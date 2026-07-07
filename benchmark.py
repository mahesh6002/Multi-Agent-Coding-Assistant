import os
import json
import time
import datetime
import traceback
import sqlite3
import argparse

# Enforce real Gemini API calls
os.environ["MOCK_LLM"] = "False"

from agent_graph.graph import app as graph_app
from agent_graph.config import settings

# Verify settings mock mode is indeed disabled
settings.MOCK_LLM = False

# Define the 5 benchmark tasks
BENCHMARK_TASKS = [
    {
        "id": "task_1_lru_cache",
        "name": "LRU Cache",
        "spec": "Implement an LRU Cache with get and set operations. It should support a fixed capacity and discard the least recently used item when full. Include unit tests."
    },
    {
        "id": "task_2_rate_limiter",
        "name": "Token Bucket Rate Limiter",
        "spec": "Implement a rate limiter using the Token Bucket algorithm. It should allow configuring bucket capacity and replenishment rate. Include unit tests."
    },
    {
        "id": "task_3_csv_validator",
        "name": "Multi-File CSV Validator",
        "spec": (
            "Implement a CSV validator split across three files:\n"
            "1. schema.py: Defines a class representing the expected column schema (types and constraints).\n"
            "2. validator.py: Implements the validation logic checking row types, missing columns, and header matches.\n"
            "3. exceptions.py: Defines shared validation exception classes.\n"
            "Include unit tests covering valid rows, missing columns, and type mismatches."
        )
    },
    {
        "id": "task_4_run_length_encoder",
        "name": "Run-Length Encoder",
        "spec": "Implement run-length compression and decompression functions for string inputs (e.g., 'AAAABBBCC' -> '4A3B2C'). Include unit tests."
    },
    {
        "id": "task_5_markdown_to_html",
        "name": "Markdown to HTML Converter",
        "spec": "Implement a markdown to HTML converter that processes basic markdown header lines (e.g. '# Header 1') and bold text markers (e.g. '**bold text**') into HTML elements. Include unit tests."
    }
]

def run_benchmark(target_task_id=None):
    results = []
    start_time_all = time.perf_counter()
    
    # Filter tasks if a single target task is specified
    tasks_to_run = BENCHMARK_TASKS
    if target_task_id:
        tasks_to_run = [t for t in BENCHMARK_TASKS if t["id"] == target_task_id]
        if not tasks_to_run:
            print(f"Error: Task ID '{target_task_id}' not found in benchmark tasks.")
            return
            
    print(f"Starting Multi-Agent Assistant Benchmark at {datetime.datetime.now().isoformat()}")
    print(f"Mock Mode: {settings.MOCK_LLM} | Target Tasks: {[t['name'] for t in tasks_to_run]}")
    print("--------------------------------------------------------------------------------")
    
    for task in tasks_to_run:
        task_id = task["id"]
        task_name = task["name"]
        task_spec = task["spec"]
        thread_id = f"bench-{task_id}"
        
        print(f"\n[RUNNING] {task_name} (Thread ID: {thread_id})...")
        
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "spec": task_spec,
            "architecture": {"files": [], "explanation": ""},
            "files": {},
            "test_files": {},
            "test_results": {},
            "lint_results": {},
            "review_notes": [],
            "iteration_count": {},
            "status": "planning",
            "next_agent": "planner",
            "run_log": []
        }
        
        task_start = time.perf_counter()
        status = "failed"
        iterations = 0
        generated_files = []
        error_info = None
        final_state = None
        
        try:
            # Execute the graph run synchronously
            final_state = graph_app.invoke(initial_state, config)
            status = final_state.get("status", "failed")
            
            # Count supervisor routing iterations
            run_log = final_state.get("run_log", [])
            iterations = sum(1 for log in run_log if log.get("agent") == "supervisor")
            
            # Gather created files list
            src_files = list(final_state.get("files", {}).keys())
            tst_files = list(final_state.get("test_files", {}).keys())
            generated_files = src_files + tst_files
            
            # If the graph reported failure, extract the actual reason from final state logs
            if status != "done":
                if run_log:
                    # Look backward for the first failing step description
                    for log in reversed(run_log):
                        action = log.get("action", "")
                        reasoning = log.get("reasoning", "")
                        details = log.get("details", "")
                        if "failed" in action.lower() or "error" in reasoning.lower() or "failed" in reasoning.lower():
                            error_info = f"[{log.get('agent').upper()} NODE FAILURE] Action: {action} | Reasoning: {reasoning}"
                            if details:
                                error_info += f" | Details: {details}"
                            break
                    if not error_info:
                        last = run_log[-1]
                        error_info = f"[{last.get('agent').upper()} NODE FAILURE] Action: {last.get('action')} | Reasoning: {last.get('reasoning')}"
                else:
                    arch_expl = final_state.get("architecture", {}).get("explanation", "")
                    if "failed" in arch_expl.lower() or "error" in arch_expl.lower():
                        error_info = f"[PLANNER NODE FAILURE] Explanation: {arch_expl}"
                    else:
                        error_info = "Unknown failure occurred before run logs could be recorded."
            
            # Output results to disk if successful or partially coded
            if generated_files:
                output_dir = f"benchmark_output/{task_id}"
                os.makedirs(output_dir, exist_ok=True)
                for filepath, content in final_state.get("files", {}).items():
                    out_path = os.path.join(output_dir, filepath)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(content)
                for filepath, content in final_state.get("test_files", {}).items():
                    out_path = os.path.join(output_dir, filepath)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(content)
            
            # Save run trace
            if run_log:
                output_dir = f"benchmark_output/{task_id}"
                os.makedirs(output_dir, exist_ok=True)
                with open(os.path.join(output_dir, "run_trace.json"), "w", encoding="utf-8") as f:
                    json.dump(run_log, f, indent=2)
                    
        except Exception as e:
            status = "failed_error"
            error_info = f"[GRAPH PROCESS EXCEPTION] {str(e)}"
            print(f"[ERROR] Task {task_name} encountered exception: {error_info}")
            traceback.print_exc()
            
        task_end = time.perf_counter()
        elapsed = task_end - task_start
        
        print(f"[COMPLETED] {task_name} | Status: {status} | Iterations: {iterations} | Time: {elapsed:.2f}s")
        if error_info:
            print(f"  -> Error: {error_info}")
        
        results.append({
            "task_id": task_id,
            "task_name": task_name,
            "status": status,
            "iterations": iterations,
            "elapsed_seconds": elapsed,
            "files_count": len(generated_files),
            "files": generated_files,
            "error": error_info
        })
        
    elapsed_all = time.perf_counter() - start_time_all
    
    # Save structured results to file (only if running all tasks or appending)
    if not target_task_id:
        with open("benchmark_results.json", "w", encoding="utf-8") as f:
            json.dump({
                "total_elapsed_seconds": elapsed_all,
                "timestamp": datetime.datetime.now().isoformat(),
                "results": results
            }, f, indent=2)
            
        generate_markdown_report(results, elapsed_all)
        print("\n================================================================================")
        print(f"Benchmark finished successfully in {elapsed_all/60:.2f} minutes.")
        print("Results saved to benchmark_results.json and eval_report.md.")
    else:
        print("\n================================================================================")
        print(f"Single task execution completed in {elapsed_all:.2f} seconds.")
        print(json.dumps(results, indent=2))

def generate_markdown_report(results, total_time):
    passed_tasks = sum(1 for r in results if r["status"] == "done")
    total_tasks = len(results)
    success_rate = (passed_tasks / total_tasks) * 100
    
    avg_iterations = sum(r["iterations"] for r in results) / total_tasks
    avg_time = sum(r["elapsed_seconds"] for r in results) / total_tasks
    
    report_content = f"""# Benchmark Evaluation Report

This report summarizes the performance of the **Multi-Agent Coding Assistant** on the 5 approved benchmark tasks running against the real Gemini API (`MOCK_LLM=false`).

---

## Executive Summary

| Metric | Value |
|---|---|
| **Evaluation Date** | {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} |
| **Total Benchmark Tasks** | {total_tasks} |
| **Successful Tasks** | {passed_tasks} / {total_tasks} |
| **Success Rate** | {success_rate:.1f}% |
| **Total Execution Time** | {total_time/60:.2f} minutes |
| **Average Task Time** | {avg_time:.2f} seconds |
| **Average Routing Cycles** | {avg_iterations:.1f} iterations |

---

## Detailed Task Performance

| Task ID | Task Name | Status | Iterations | Time (s) | File Count |
|---|---|---|---|---|---|
"""
    
    for r in results:
        status_pill = "✅ DONE" if r["status"] == "done" else f"❌ {r['status'].upper()}"
        report_content += f"| `{r['task_id']}` | {r['task_name']} | {status_pill} | {r['iterations']} | {r['elapsed_seconds']:.2f} | {r['files_count']} |\n"
        
    report_content += """
---

## Task Details Breakdown
"""
    
    for r in results:
        status_text = "Done" if r["status"] == "done" else f"Failed ({r['status']})"
        report_content += f"""
### {r['task_name']}
*   **Status**: {status_text}
*   **Orchestrator Iterations**: {r['iterations']}
*   **Time Elapsed**: {r['elapsed_seconds']:.2f} seconds
*   **Generated Files** ({r['files_count']}):
"""
        if r["files"]:
            for f in r["files"]:
                report_content += f"    *   `{f}`\n"
        else:
            report_content += "    *   No files created.\n"
            
        if r["error"]:
            report_content += f"\n*   **Error Encountered**:\n    > {r['error']}\n"
            
    # Write report locally
    with open("eval_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)
        
    # Write report to artifacts directory
    artifact_path = r"C:\Users\srvar\.gemini\antigravity\brain\b770ef9a-fd44-46b6-bdcd-5b3b2ce2d0c1\eval_report.md"
    try:
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(report_content)
    except Exception as e:
        print(f"Warning: Could not write artifact copy: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Evaluation Benchmark Runner")
    parser.add_index = parser.add_argument("--task", type=str, help="Run only a single task by ID (e.g. task_1_lru_cache)")
    args = parser.parse_args()
    
    run_benchmark(args.task)
