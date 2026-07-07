from typing import TypedDict, Literal, Annotated, List, Dict, Any
from operator import add

# Reducer to merge dictionaries (e.g. file changes, test results)
def merge_dict(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    new_dict = left.copy()
    new_dict.update(right)
    return new_dict

class ProjectState(TypedDict):
    spec: str                          # Original task description
    architecture: Dict[str, Any]       # Planner's output: file tree + responsibilities
    files: Annotated[Dict[str, str], merge_dict]        # filename -> current content
    test_files: Annotated[Dict[str, str], merge_dict]   # filename -> test content
    test_results: Dict[str, str] # filename -> raw pytest output
    lint_results: Dict[str, List[str]] # filename -> list of issues
    review_notes: List[Dict[str, Any]]  # [{severity, file, note}]
    iteration_count: Annotated[Dict[str, int], merge_dict] # per-file or general retry counts
    status: Literal["planning", "coding", "testing", "linting", "reviewing", "debugging", "documenting", "done", "failed"]
    next_agent: str
    run_log: Annotated[List[Dict[str, Any]], add]       # append-only trace of every agent action
