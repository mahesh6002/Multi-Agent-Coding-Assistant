import datetime
from pydantic import BaseModel, Field
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from agent_graph.state import ProjectState
from agent_graph.config import settings
from agent_graph.mock_llm import MOCK_ARCHITECTURE

class FilePlan(BaseModel):
    filepath: str = Field(description="Relative path of the file to create (e.g. calculator.py)")
    description: str = Field(description="Purpose of this file and its duties/classes/functions.")

class ArchitecturePlan(BaseModel):
    files: List[FilePlan] = Field(description="List of files that need to be created in the project.")
    explanation: str = Field(description="High-level architectural overview of the solution.")

def planner_node(state: ProjectState) -> dict:
    """
    Planner Agent: takes the plain-English task spec and creates a structured plan
    of files and their respective responsibilities.
    Supports both real Gemini API execution and offline Mock LLM execution.
    """
    architecture = {}
    action_summary = ""
    details = ""
    
    if settings.MOCK_LLM:
        # Mock mode execution
        spec = state.get("spec", "").lower()
        if "sequencing" in spec:
            architecture = {
                "files": [
                    {
                        "filepath": "calculator.py",
                        "description": "Core calculator logic with add and subtract functions."
                    },
                    {
                        "filepath": "utils.py",
                        "description": "Utility formatting and helper functions for outputs."
                    },
                    {
                        "filepath": "main.py",
                        "description": "Main entry point file to orchestrate calculation."
                    }
                ],
                "explanation": "A clean, modular calculator implementation with operations, helpers, and an orchestrator."
            }
        else:
            architecture = MOCK_ARCHITECTURE
        action_summary = f"[MOCK] Generated architecture plan with {len(architecture['files'])} files."
        details = architecture["explanation"]
    else:
        # Real Gemini API execution
        llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_PLANNER,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        
        # Bind structured output
        structured_llm = llm.with_structured_output(ArchitecturePlan)
        
        system_prompt = (
            "You are the Lead Software Architect.\n"
            "Your task is to review the user's software spec and propose a clean, modular multi-file Python architecture.\n"
            "Break the task down into logical files: separating logic, utilities, and main entry points.\n"
            "Provide a clear plan with filenames and concrete responsibilities for each file.\n"
            "Only specify standard relative paths. No absolute paths."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Specification:\n{state.get('spec')}"}
        ]
        
        try:
            plan = structured_llm.invoke(messages)
            architecture = plan.model_dump()
            action_summary = f"Generated architecture plan with {len(plan.files)} files."
            details = architecture.get("explanation", "")
        except Exception as e:
            architecture = {"files": [], "explanation": f"Failed to generate plan: {str(e)}"}
            action_summary = "Failed to generate architecture plan due to Gemini API error."
            details = str(e)
            
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "agent": "planner",
        "action": action_summary,
        "details": details
    }
    
    return {
        "architecture": architecture,
        "run_log": [log_entry]
    }
