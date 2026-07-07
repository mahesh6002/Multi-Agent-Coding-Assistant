import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from agent_graph.state import ProjectState
from agent_graph.config import settings
from agent_graph.mock_llm import MOCK_BUGGY_CALCULATOR, MOCK_UTILS

class CoderOutput(BaseModel):
    filepath: str = Field(
        description="The relative filepath of the file to write or modify (must match a file in the plan)."
    )
    code: str = Field(
        description="The complete, drop-in replacement Python source code for the file (do not use markdown blocks inside the string)."
    )
    explanation: str = Field(
        description="Brief explanation of what was implemented or modified."
    )

def coder_node(state: ProjectState) -> dict:
    """
    Coder Agent: writes or modifies a single file based on the architecture plan.
    Has visibility of other files' contents to maintain import consistency.
    Supports both real Gemini API execution and offline Mock LLM execution.
    """
    # Gather planned files and existing files
    planned_files = state.get("architecture", {}).get("files", [])
    current_files = state.get("files", {})
    
    # Determine which file to write or update.
    # We prioritize files that don't exist yet.
    target_file = None
    for pf in planned_files:
        path = pf["filepath"]
        if path not in current_files:
            target_file = pf
            break
            
    # If all planned files are already written, we check if we are in a debugging/review state
    # and need to update a file that has issues.
    if not target_file:
        bad_files = []
        if state.get("review_notes"):
            bad_files.extend([note.get("file") for note in state["review_notes"] if note.get("file")])
        if state.get("lint_results"):
            bad_files.extend([f for f, issues in state["lint_results"].items() if issues])
        
        bad_files = [f for f in bad_files if f]
        if bad_files:
            for pf in planned_files:
                if pf["filepath"] == bad_files[0]:
                    target_file = pf
                    break
        
        # Default fallback
        if not target_file and planned_files:
            target_file = planned_files[0]
            
    if not target_file:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": "coder",
            "action": "Skipped coding: no planned files found.",
            "details": ""
        }
        return {"run_log": [log_entry]}

    filepath = target_file["filepath"]
    description = target_file["description"]
    
    code_content = ""
    explanation = ""
    filepath_written = filepath
    
    if settings.MOCK_LLM:
        # Mock mode execution
        if filepath == "calculator.py":
            iteration_count = state.get("iteration_count", {})
            curr_iter = iteration_count.get("calculator.py", 0)
            if curr_iter >= 2:
                code_content = """
def add(a, b):
    \"\"\"Adds two numbers.\"\"\"
    return a + b

def subtract(a, b):
    \"\"\"Subtracts b from a.\"\"\"
    return a - b
"""
                explanation = "[MOCK] Updating calculator.py to add detailed docstrings for all mathematical operations (fixing reviewer blocker)."
            else:
                code_content = MOCK_BUGGY_CALCULATOR
                explanation = "[MOCK] Implementing initial draft of calculator.py with core arithmetic functions."
        elif filepath == "utils.py":
            code_content = MOCK_UTILS
            explanation = "[MOCK] Implementing helper formatting utilities in utils.py."
        else:
            code_content = f"# Mock code for {filepath}\n"
            explanation = f"[MOCK] Implementing {filepath}."
    else:
        # Real Gemini API execution
        llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_CODER,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        
        # Bind structured output
        structured_llm = llm.with_structured_output(CoderOutput)
        
        other_files_context = "\n".join([
            f"--- File: {path} ---\n{content}\n"
            for path, content in current_files.items() if path != filepath
        ])
        
        system_prompt = (
            "You are the Coder Agent.\n"
            "Your task is to write clean, production-ready, PEP 8-compliant Python code for a single file.\n"
            "Ensure all imports from other project modules are correct.\n"
            "Write the FULL content of the file. Do not use placeholders or omit any logic.\n"
            "Return the output using the specified JSON schema."
        )
        
        user_prompt = (
            f"Goal: Implement this file:\n"
            f"File Path: {filepath}\n"
            f"Responsibilities: {description}\n\n"
            f"Project Specification: {state.get('spec')}\n\n"
            f"Architecture Overview: {state.get('architecture', {}).get('explanation')}\n\n"
            f"Current contents of other files in the project:\n"
            f"{other_files_context if other_files_context else 'None'}\n\n"
        )
        
        issues_context = ""
        if state.get("test_results"):
            issues_context += f"Test execution errors/results:\n{state.get('test_results')}\n\n"
        
        file_lints = state.get("lint_results", {}).get(filepath)
        if file_lints:
            issues_context += f"Lint errors for this file:\n" + "\n".join(file_lints) + "\n\n"
            
        file_reviews = [n for n in state.get("review_notes", []) if n.get("file") == filepath]
        if file_reviews:
            issues_context += f"Review comments for this file:\n" + "\n".join([r["note"] for r in file_reviews]) + "\n\n"
            
        if issues_context:
            user_prompt += (
                f"CRITICAL: There are execution errors, lint issues, or reviewer comments for this file. "
                f"You MUST resolve them in your implementation:\n{issues_context}"
            )
            
        try:
            response = structured_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            filepath_written = response.filepath
            code_content = response.code
            explanation = response.explanation
        except Exception as e:
            action_summary = f"Failed to generate code for {filepath} due to Gemini API error."
            return {
                "run_log": [{
                    "timestamp": datetime.datetime.now().isoformat(),
                    "agent": "coder",
                    "action": action_summary,
                    "details": str(e)
                }]
            }
            
    # Track iteration counts for this file
    iteration_count = state.get("iteration_count", {})
    new_iter = iteration_count.get(filepath_written, 0) + 1
    action_summary = f"Implemented {filepath_written} (Revision {new_iter})."
    
    return {
        "files": {filepath_written: code_content},
        "iteration_count": {filepath_written: new_iter},
        "test_results": {},
        "lint_results": {},
        "review_notes": [],
        "run_log": [{
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": "coder",
            "action": action_summary,
            "details": explanation
        }]
    }
