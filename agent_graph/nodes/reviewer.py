import datetime
from pydantic import BaseModel, Field
from typing import List, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from agent_graph.state import ProjectState
from agent_graph.config import settings
from agent_graph.mock_llm import MOCK_REVIEW_NOTES

class ReviewNote(BaseModel):
    severity: Literal["blocker", "suggestion"] = Field(
        description="Severity of the issue. Blocker will trigger routing back to coder."
    )
    file: str = Field(
        description="The relative file path the comment refers to."
    )
    note: str = Field(
        description="Review comment text detailing suggestions or blockers."
    )

class ReviewerOutput(BaseModel):
    notes: List[ReviewNote] = Field(
        description="List of review comments on the codebase."
    )
    approved: bool = Field(
        description="Set to true if there are no 'blocker' severity issues and codebase is ready."
    )

def reviewer_node(state: ProjectState) -> dict:
    """
    Reviewer Agent: checks the generated code against the specifications and the planner's blueprint.
    Creates severity-tagged notes (blocker/suggestion) and approves the project if it meets requirements.
    Supports both real Gemini API execution and offline Mock LLM execution.
    """
    notes = []
    approved = True
    action_summary = ""
    
    if settings.MOCK_LLM:
        # Mock mode execution
        iteration_count = state.get("iteration_count", {})
        calc_revision = iteration_count.get("calculator.py", 0)
        
        if "blocker" in state.get("spec", "").lower() and calc_revision == 2:
            notes = [
                {
                    "severity": "blocker",
                    "file": "calculator.py",
                    "note": "[MOCK] Code must include detailed docstrings for all mathematical operations (blocker)."
                }
            ]
            approved = False
            action_summary = "[MOCK] Reviewer rejected codebase with 1 blocker."
        else:
            notes = MOCK_REVIEW_NOTES
            approved = True
            action_summary = "[MOCK] Reviewer reviewed files. Code approved with suggestions."
    else:
        # Real Gemini API execution
        llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_REVIEWER, # Reviewer uses Pro tier model
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0
        )
        
        structured_llm = llm.with_structured_output(ReviewerOutput)
        
        # Build context
        source_code_context = "\n".join([
            f"--- File: {path} ---\n{content}\n"
            for path, content in state.get("files", {}).items()
        ])
        
        system_prompt = (
            "You are the Reviewer Agent.\n"
            "Your task is to review the generated code files against the original spec and architecture plan.\n"
            "Assess correctness, imports, code quality, and style.\n"
            "If there are fatal issues that will break functionality or violate critical requirements, mark them as 'blocker' severity.\n"
            "Otherwise, for cleanups or small improvements, mark them as 'suggestion'.\n"
            "If there are any blocker notes, set approved = False. Otherwise, set approved = True.\n"
            "Return your output using the specified JSON schema."
        )
        
        user_prompt = (
            f"Original Spec: {state.get('spec')}\n\n"
            f"Architecture blueprint: {state.get('architecture')}\n\n"
            f"Coded source files in project:\n"
            f"{source_code_context if source_code_context else 'None'}\n"
        )
        
        try:
            from agent_graph.llm_helper import safe_llm_invoke
            response = safe_llm_invoke(structured_llm, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            notes = [note.model_dump() for note in response.notes]
            approved = response.approved
            
            blockers_count = sum(1 for n in notes if n["severity"] == "blocker")
            if approved and blockers_count == 0:
                action_summary = "Codebase approved by Reviewer."
            else:
                action_summary = f"Codebase rejected by Reviewer with {blockers_count} blockers."
        except Exception as e:
            action_summary = "Failed to run codebase review due to Gemini API error."
            notes = [{"severity": "blocker", "file": "system", "note": f"Review failed: {str(e)}"}]
            approved = False
            
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "agent": "reviewer",
        "action": action_summary,
        "details": f"Notes: {notes}"
    }
    
    return {
        "review_notes": notes,
        "run_log": [log_entry]
    }
