import datetime
from agent_graph.state import ProjectState
from agent_graph.config import settings
from sandbox.docker_sandbox import run_in_sandbox

def executor_node(state: ProjectState) -> dict:
    """
    Executor Agent (Sandbox Tool): runs the generated files and pytest suite
    inside the isolated Docker container. Parses and saves the results.
    """
    files = state.get("files", {})
    test_files = state.get("test_files", {})
    
    if not test_files:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": "executor",
            "action": "Skipped run: no test files found.",
            "details": ""
        }
        return {"run_log": [log_entry]}
        
    action_summary = "Running test suite inside Docker sandbox..."
    print(f"\n[EXECUTOR] {action_summary}")
    
    # Run sandbox
    exit_code, output = run_in_sandbox(
        files=files,
        test_files=test_files,
        image_name=settings.DOCKER_IMAGE,
        timeout=settings.SANDBOX_TIMEOUT,
        mem_limit=settings.SANDBOX_MEMORY_LIMIT
    )
    
    # Save results
    # We key by the test file name or a generic "all_tests"
    test_key = list(test_files.keys())[0] if test_files else "tests"
    
    if exit_code == 0:
        status_text = f"PASSED\n\n{output}"
        action_text = f"Tests passed: {test_key} completed successfully."
    else:
        status_text = f"FAILED (Exit Code {exit_code})\n\n{output}"
        action_text = f"Tests failed: {test_key} exited with code {exit_code}."
        
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "agent": "executor",
        "action": action_text,
        "details": output
    }
    
    return {
        "test_results": {test_key: status_text},
        "run_log": [log_entry]
    }
