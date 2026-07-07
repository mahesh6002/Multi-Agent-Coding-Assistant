import sys
import os
import argparse
import json
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Now import agent_graph modules
from agent_graph.graph import app
from agent_graph.config import settings

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Coding Assistant CLI")
    parser.add_argument("task", type=str, nargs="?", help="Plain English description of the task to build")
    parser.add_argument("--output-dir", type=str, default="generated_project", help="Directory to save generated files")
    parser.add_argument("--thread-id", type=str, default="default-thread", help="Thread ID for LangGraph checkpointer")
    args = parser.parse_args()

    # Get task from CLI or prompt user
    task = args.task
    if not task:
        task = input("Enter the coding task description: ").strip()
        if not task:
            print("Error: No task specified.")
            sys.exit(1)

    print(f"\nStarting generator graph for task: '{task}'")
    print(f"Output directory: {args.output_dir}")
    print(f"Using model: {settings.MODEL_SUPERVISOR} (Supervisor)\n")

    # Initial state
    initial_state = {
        "spec": task,
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

    config = {"configurable": {"thread_id": args.thread_id}}

    # Execute the LangGraph workflow and print events
    print("--------------------------------------------------------------------------------")
    print("Agent Logs:")
    print("--------------------------------------------------------------------------------")
    
    current_status = None
    
    for event in app.stream(initial_state, config, stream_mode="values"):
        # Access the latest state values from the event
        status = event.get("status")
        if status != current_status:
            current_status = status
            print(f"\n>>> State Status Transition: {status.upper()} <<<")
        
        # Print the last log entry if available
        run_log = event.get("run_log", [])
        if run_log:
            last_entry = run_log[-1]
            agent = last_entry.get("agent")
            action = last_entry.get("action")
            reasoning = last_entry.get("reasoning", "")
            details = last_entry.get("details", "")
            
            print(f"[{agent.upper()}] {action}")
            if reasoning:
                print(f"  Reasoning: {reasoning}")
            if details:
                # Truncate details for cleaner display
                detail_str = str(details)
                if len(detail_str) > 150:
                    detail_str = detail_str[:150] + "..."
                print(f"  Details: {detail_str}")

    # Retrieve the final state
    final_state = app.get_state(config).values
    
    print("\n--------------------------------------------------------------------------------")
    print(f"Graph execution finished. Final Status: {final_state.get('status')}")
    print("--------------------------------------------------------------------------------")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Write source files
    files = final_state.get("files", {})
    if files:
        print("\nWriting generated source files:")
        for filepath, content in files.items():
            out_path = os.path.join(args.output_dir, filepath)
            # Create subdirectories if necessary
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f" - Saved: {out_path} ({len(content)} bytes)")
            
    # Write test files if any
    test_files = final_state.get("test_files", {})
    if test_files:
        print("\nWriting generated test files:")
        for filepath, content in test_files.items():
            out_path = os.path.join(args.output_dir, filepath)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f" - Saved: {out_path} ({len(content)} bytes)")

    # Save run log
    log_path = os.path.join(args.output_dir, "run_trace.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(final_state.get("run_log", []), f, indent=2)
    print(f"\nTrace log saved to: {log_path}")

if __name__ == "__main__":
    main()
