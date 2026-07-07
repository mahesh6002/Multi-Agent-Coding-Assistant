import datetime
from typing import Literal
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from agent_graph.state import ProjectState
from agent_graph.config import settings
from agent_graph.mock_llm import get_mock_supervisor_decision

class SupervisorDecision(BaseModel):
    next_agent: Literal[
        "planner", "coder", "test_writer", "executor", 
        "static_analyzer", "reviewer", "debugger", "docs_agent", "done", "failed"
    ] = Field(
        description="The next agent node to run, or 'done'/'failed' to terminate."
    )
    reasoning: str = Field(
        description="Explanation of why this agent was chosen based on the current state."
    )

def supervisor_node(state: ProjectState) -> dict:
    """
    Supervisor Agent: reads state, decides the next agent to transition to,
    and logs its reasoning to the run log.
    Enforces correct sequencing (all planned files must be coded before test/lint/review/docs).
    """
    next_agent = "failed"
    reasoning = ""
    
    if settings.MOCK_LLM:
        # Mock mode execution
        decision = get_mock_supervisor_decision(state)
        next_agent = decision["next_agent"]
        reasoning = decision["reasoning"]
    else:
        # Real Gemini API execution
        llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_SUPERVISOR,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0
        )
        
        # Bind structured output
        structured_llm = llm.with_structured_output(SupervisorDecision)
        
        current_files = list(state.get("files", {}).keys())
        current_tests = list(state.get("test_files", {}).keys())
        run_log_length = len(state.get("run_log", []))
        
        system_prompt = (
            "You are the Supervisor of a Multi-Agent Coding Assistant.\n"
            "Your task is to review the current project state and decide which specialist agent should act next.\n\n"
            "CRITICAL SEQUENCING RULE:\n"
            "You MUST NOT transition to 'test_writer', 'executor', 'static_analyzer', 'reviewer', or 'docs_agent' "
            "unless ALL files listed in the architecture plan (architecture['files']) have been coded (exist in 'Files'). "
            "If any planned file is missing, you must route to 'coder' to write it first.\n\n"
            "Routing guidelines:\n"
            "1. If no architecture/plan has been generated, route to 'planner'.\n"
            "2. If the plan exists but ANY planned file is not yet coded, route to 'coder'.\n"
            "3. If all planned files are coded but tests aren't written, route to 'test_writer'.\n"
            "4. If tests are written but test_results is empty or out-of-date after a code change, route to 'executor'.\n"
            "5. If tests have passed (all pass) and static analysis is empty, route to 'static_analyzer' (linting).\n"
            "6. If tests fail, route to 'debugger' to produce a patch, then back to executor.\n"
            "7. If linting has issues, route to 'debugger' or 'coder' to fix them.\n"
            "8. If linting is clean but code has not been reviewed, route to 'reviewer'.\n"
            "9. If the reviewer suggests changes with severity 'blocker', route to 'coder' / 'debugger'.\n"
            "10. If everything is passing, lint-free, and approved (no blockers), route to 'docs_agent' to write documentation.\n"
            "11. If docs are complete, route to 'done'.\n"
            "12. If the iteration count exceeds the maximum limit or no progress is being made, route to 'failed'.\n\n"
            "Be decisive and logical. Never route back to the same agent if no progress has been made."
        )
        
        state_description = (
            f"Spec: {state.get('spec')}\n"
            f"Architecture: {state.get('architecture')}\n"
            f"Files: {current_files}\n"
            f"Test Files: {current_tests}\n"
            f"Test Results: {state.get('test_results')}\n"
            f"Lint Results: {state.get('lint_results')}\n"
            f"Review Notes: {state.get('review_notes')}\n"
            f"Iteration Count: {state.get('iteration_count')}\n"
            f"Total Logged Actions: {run_log_length}\n"
            f"Last Node: {state.get('next_agent')}\n"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Current State:\n{state_description}\nPlease decide the next step."}
        ]
        
        try:
            decision = structured_llm.invoke(messages)
            next_agent = decision.next_agent
            reasoning = decision.reasoning
        except Exception as e:
            next_agent = "failed"
            reasoning = f"Failed to call Gemini API for supervisor decision: {str(e)}"

    # Programmatic safety override to prevent sequencing bugs
    planned_files = state.get("architecture", {}).get("files", [])
    files = state.get("files", {})
    if planned_files and next_agent not in ["planner", "coder", "failed"]:
        missing_files = [f["filepath"] for f in planned_files if f["filepath"] not in files]
        if missing_files:
            next_agent = "coder"
            reasoning = f"Override: routing to coder because planned files are missing from workspace: {missing_files}"

    # Blocker review notes override
    run_log = state.get("run_log", [])
    last_agent = run_log[-1].get("agent") if run_log else None
    
    blockers = [n for n in state.get("review_notes", []) if n.get("severity") == "blocker"]
    if blockers and last_agent == "reviewer" and next_agent not in ["coder", "debugger", "failed"]:
        next_agent = "coder"
        reasoning = f"Override: routing to coder due to outstanding blocker-severity review notes: {blockers}"

    # Create log entry
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "agent": "supervisor",
        "action": f"Routed to {next_agent}",
        "reasoning": reasoning
    }
    
    status_map = {
        "planner": "planning",
        "coder": "coding",
        "test_writer": "testing",
        "executor": "testing",
        "static_analyzer": "linting",
        "reviewer": "reviewing",
        "debugger": "debugging",
        "docs_agent": "documenting",
        "done": "done",
        "failed": "failed"
    }
    
    return {
        "next_agent": next_agent,
        "status": status_map.get(next_agent, state.get("status", "planning")),
        "run_log": [log_entry]
    }
