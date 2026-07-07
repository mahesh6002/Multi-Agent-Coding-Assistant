import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from agent_graph.state import ProjectState
from agent_graph.config import settings
from agent_graph.mock_llm import MOCK_TESTS

class TestWriterOutput(BaseModel):
    filepath: str = Field(
        description="The relative filepath of the test file to write (e.g. test_calculator.py)."
    )
    code: str = Field(
        description="The complete, drop-in replacement Python unit test code (pytest, do not use markdown code block wrappers)."
    )
    explanation: str = Field(
        description="Brief explanation of the test cases written."
    )

def test_writer_node(state: ProjectState) -> dict:
    """
    Test Writer Agent: writes unit tests (pytest) based on the project spec and implemented files.
    Supports both real Gemini API execution and offline Mock LLM execution.
    """
    test_filepath = "test_calculator.py"
    test_code = ""
    explanation = ""
    
    if settings.MOCK_LLM:
        # Mock mode execution
        test_code = MOCK_TESTS
        explanation = "[MOCK] Generating test suite covering arithmetic methods and formatted print output."
    else:
        # Real Gemini API execution
        llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_CODER, # Test Writer uses Flash tier model
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        
        structured_llm = llm.with_structured_output(TestWriterOutput)
        
        # Build context from generated files
        source_files_context = "\n".join([
            f"--- File: {path} ---\n{content}\n"
            for path, content in state.get("files", {}).items()
        ])
        
        system_prompt = (
            "You are the Test Writer Agent.\n"
            "Your task is to write comprehensive, PEP 8-compliant unit tests using pytest.\n"
            "Cover all classes, functions, and key edge cases in the project modules.\n"
            "Do not import external packages unless absolutely necessary. Import correct module names from the project.\n"
            "Return your output using the specified JSON schema."
        )
        
        user_prompt = (
            f"Project Spec: {state.get('spec')}\n\n"
            f"Architecture Plan: {state.get('architecture')}\n\n"
            f"Coded source files in project:\n"
            f"{source_files_context if source_files_context else 'None'}\n"
        )
        
        try:
            response = structured_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            test_filepath = response.filepath
            test_code = response.code
            explanation = response.explanation
        except Exception as e:
            action_summary = f"Failed to generate tests due to Gemini API error."
            return {
                "run_log": [{
                    "timestamp": datetime.datetime.now().isoformat(),
                    "agent": "test_writer",
                    "action": action_summary,
                    "details": str(e)
                }]
            }
            
    action_summary = f"Generated test suite {test_filepath}."
    
    return {
        "test_files": {test_filepath: test_code},
        "run_log": [{
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": "test_writer",
            "action": action_summary,
            "details": explanation
        }]
    }
