import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from agent_graph.state import ProjectState
from agent_graph.config import settings
from agent_graph.mock_llm import MOCK_CORRECT_CALCULATOR

class DebuggerOutput(BaseModel):
    filepath: str = Field(
        description="The filepath of the file being corrected."
    )
    code: str = Field(
        description="The complete, corrected Python source code (do not use markdown wrappers)."
    )
    explanation: str = Field(
        description="Detailed explanation of the root cause and the fix applied."
    )

def debugger_node(state: ProjectState) -> dict:
    """
    Debugger Agent: receives failing test outputs and tracebacks, locates the bug,
    and returns a targeted corrected version of the code.
    Supports both real Gemini API execution and offline Mock LLM execution.
    """
    files = state.get("files", {})
    test_results = state.get("test_results", {})
    
    # We identify which file to debug
    # Default to calculator.py for the mock scenario, or the first file that failed tests.
    target_filepath = "calculator.py"
    for path in files.keys():
        # In real scenario, we might look for references to this path in the test failure output
        pass
        
    code_content = ""
    explanation = ""
    
    if settings.MOCK_LLM:
        # Mock mode execution
        if "unfixable" in state.get("spec", "").lower():
            offset = 88 - (state.get("iteration_count", {}).get("calculator.py", 0) * 10)
            code_content = f"""
def add(a, b):
    # Intentional wrong implementation to simulate unfixable bug
    return a + b + {offset}

def subtract(a, b):
    return a - b
"""
            explanation = f"[MOCK] Debugger attempted to resolve the issue but the calculation remains incorrect (offset +{offset})."
        else:
            code_content = MOCK_CORRECT_CALCULATOR
            explanation = "[MOCK] Debugger identified that addition sum was offset by +99 in calculator.py. Replaced with correct standard sum."
    else:
        # Real Gemini API execution
        llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_DEBUGGER,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        
        structured_llm = llm.with_structured_output(DebuggerOutput)
        
        # Build context
        source_code = files.get(target_filepath, "")
        traceback_info = "\n".join(test_results.values())
        
        system_prompt = (
            "You are the Debugger Agent.\n"
            "Your task is to fix failing tests or static analysis issues in a single Python file.\n"
            "Review the failing traceback, identify the exact bug, and write the corrected FULL file.\n"
            "Do not omit any functions or imports. Return your output using the specified JSON schema."
        )
        
        user_prompt = (
            f"Failing File Path: {target_filepath}\n\n"
            f"Failing File Code:\n{source_code}\n\n"
            f"Test Execution Errors / Traceback:\n{traceback_info}\n\n"
            f"Please output the corrected code."
        )
        
        try:
            from agent_graph.llm_helper import safe_llm_invoke
            response = safe_llm_invoke(structured_llm, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            target_filepath = response.filepath
            code_content = response.code
            explanation = response.explanation
        except Exception as e:
            action_summary = f"Failed to generate debug fix due to Gemini API error."
            return {
                "run_log": [{
                    "timestamp": datetime.datetime.now().isoformat(),
                    "agent": "debugger",
                    "action": action_summary,
                    "details": str(e)
                }]
            }
            
    iteration_count = state.get("iteration_count", {})
    new_iter = iteration_count.get(target_filepath, 0) + 1
    action_summary = f"Debugger fixed {target_filepath} (Revision {new_iter})."
    
    return {
        "files": {target_filepath: code_content},
        "iteration_count": {target_filepath: new_iter},
        "test_results": {},
        "lint_results": {},
        "review_notes": [],
        "run_log": [{
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": "debugger",
            "action": action_summary,
            "details": explanation
        }]
    }
