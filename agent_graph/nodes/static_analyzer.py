import datetime
from agent_graph.state import ProjectState
from agent_graph.config import settings
from sandbox.docker_sandbox import run_analysis_in_sandbox

def static_analyzer_node(state: ProjectState) -> dict:
    """
    Static Analyzer Agent: Runs Ruff, MyPy, and Bandit checks in the sandbox container.
    Saves findings into lint_results.
    """
    files = state.get("files", {})
    
    if not files:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": "static_analyzer",
            "action": "Skipped analysis: no source files found.",
            "details": ""
        }
        return {"run_log": [log_entry]}
        
    print("\n[STATIC_ANALYZER] Running Ruff, MyPy, and Bandit inside sandbox container...")
    
    # Run analysis
    if settings.MOCK_LLM:
        # Mock mode: return clean results to proceed to next stages smoothly
        results = {"calculator.py": [], "utils.py": []}
        action_text = "Static analysis completed (Mock Mode: clean)."
        details = "Ruff, MyPy, and Bandit simulated runs returned zero warnings."
    else:
        # Real mode: run inside container
        results = run_analysis_in_sandbox(
            files=files,
            image_name=settings.DOCKER_IMAGE,
            timeout=settings.SANDBOX_TIMEOUT,
            mem_limit=settings.SANDBOX_MEMORY_LIMIT
        )
        
        issue_count = sum(len(issues) for issues in results.values())
        if issue_count == 0:
            action_text = "Static analysis completed: zero issues found."
            details = "All lint, type, and security checks passed."
        else:
            action_text = f"Static analysis completed: found {issue_count} issues across {len(results)} files."
            details = str(results)
            
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "agent": "static_analyzer",
        "action": action_text,
        "details": details
    }
    
    return {
        "lint_results": results,
        "run_log": [log_entry]
    }
