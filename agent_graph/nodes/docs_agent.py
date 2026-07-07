import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from agent_graph.state import ProjectState
from agent_graph.config import settings
from agent_graph.mock_llm import MOCK_README

class DocsAgentOutput(BaseModel):
    filepath: str = Field(
        description="Relative filepath of the documentation file to write (e.g. README.md)."
    )
    content: str = Field(
        description="The complete markdown documentation content (do not use markdown blocks inside the string)."
    )

def docs_agent_node(state: ProjectState) -> dict:
    """
    Docs Agent: runs after the codebase successfully passes all testing, linting, and reviews.
    Generates a user-facing README.md for the generated project.
    Supports both real Gemini API execution and offline Mock LLM execution.
    """
    filepath = "README.md"
    content = ""
    action_summary = ""
    
    if settings.MOCK_LLM:
        # Mock mode execution
        content = MOCK_README
        action_summary = "[MOCK] Generated project README.md."
    else:
        # Real Gemini API execution
        llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_DOCS,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2
        )
        
        structured_llm = llm.with_structured_output(DocsAgentOutput)
        
        # Build context
        source_code_context = "\n".join([
            f"--- File: {path} ---\n{code}\n"
            for path, code in state.get("files", {}).items()
        ])
        
        system_prompt = (
            "You are the Documentation Agent.\n"
            "Your task is to write a clean, helpful, and thorough README.md for the generated project.\n"
            "Include installation, project structure, usage instructions, and testing details.\n"
            "Return your output using the specified JSON schema."
        )
        
        user_prompt = (
            f"Original Spec: {state.get('spec')}\n\n"
            f"Coded source files in project:\n"
            f"{source_code_context if source_code_context else 'None'}\n"
        )
        
        try:
            response = structured_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            filepath = response.filepath
            content = response.content
            action_summary = f"Generated project documentation file: {filepath}."
        except Exception as e:
            action_summary = "Failed to run documentation generator due to Gemini API error."
            content = f"# Documentation Generation Failed\nError: {str(e)}"
            
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "agent": "docs_agent",
        "action": action_summary,
        "details": f"File: {filepath} ({len(content)} bytes)"
    }
    
    return {
        "files": {filepath: content},
        "run_log": [log_entry]
    }
