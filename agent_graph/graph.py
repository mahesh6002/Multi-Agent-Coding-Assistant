import sqlite3
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from agent_graph.state import ProjectState
from agent_graph.config import settings

# Import real node implementations
from agent_graph.nodes.supervisor import supervisor_node
from agent_graph.nodes.planner import planner_node
from agent_graph.nodes.coder import coder_node
from agent_graph.nodes.test_writer import test_writer_node
from agent_graph.nodes.executor import executor_node
from agent_graph.nodes.static_analyzer import static_analyzer_node
from agent_graph.nodes.reviewer import reviewer_node
from agent_graph.nodes.debugger import debugger_node
from agent_graph.nodes.docs_agent import docs_agent_node

# Router function for supervisor
def supervisor_router(state: ProjectState) -> str:
    next_agent = state.get("next_agent", "failed")
    # Map next_agent string to graph node names or END
    if next_agent in ["done", "failed"]:
        return END
    return next_agent

# Initialize StateGraph
workflow = StateGraph(ProjectState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("planner", planner_node)
workflow.add_node("coder", coder_node)
workflow.add_node("test_writer", test_writer_node)
workflow.add_node("executor", executor_node)
workflow.add_node("static_analyzer", static_analyzer_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("debugger", debugger_node)
workflow.add_node("docs_agent", docs_agent_node)

# Set entry point
workflow.set_entry_point("supervisor")

# Define conditional edges from supervisor
workflow.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "planner": "planner",
        "coder": "coder",
        "test_writer": "test_writer",
        "executor": "executor",
        "static_analyzer": "static_analyzer",
        "reviewer": "reviewer",
        "debugger": "debugger",
        "docs_agent": "docs_agent",
        # Special terminal nodes
        END: END
    }
)

# Nodes transition back to supervisor for evaluation
workflow.add_edge("planner", "supervisor")
workflow.add_edge("coder", "supervisor")
workflow.add_edge("test_writer", "supervisor")
workflow.add_edge("executor", "supervisor")
workflow.add_edge("static_analyzer", "supervisor")
workflow.add_edge("reviewer", "supervisor")
workflow.add_edge("debugger", "supervisor")
workflow.add_edge("docs_agent", "supervisor")

# Compile workflow with SQLite checkpointer for local validation and persistence
conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH, check_same_thread=False)
memory = SqliteSaver(conn)
app = workflow.compile(checkpointer=memory)
