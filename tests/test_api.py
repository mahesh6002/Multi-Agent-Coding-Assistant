import pytest
import json
from fastapi.testclient import TestClient
from api import api_app
from agent_graph.config import settings

client = TestClient(api_app)

def test_list_threads():
    """Verify that list_threads returns a list of metadata entries."""
    response = client.get("/api/threads")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_nonexistent_thread():
    """Verify that get_thread returns a 404 for a missing thread."""
    response = client.get("/api/threads/missing-thread-12345")
    assert response.status_code == 404
    assert "detail" in response.json()

def test_generate_sse_stream():
    """Verify that /api/generate successfully returns an SSE event stream.
    We run in mock mode to verify the yielded stream updates and event types.
    """
    # Ensure mock mode is enabled for fast offline test execution
    assert settings.MOCK_LLM is True
    
    # We use a StreamingResponse client block to iterate through chunks
    url = "/api/generate?spec=Build a simple calculator&thread_id=test-api-stream-thread&output_dir=temp_api_test_output"
    with client.stream("GET", url) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # Read the first few lines from the generator
        event_lines = []
        for line in response.iter_lines():
            if line:
                event_lines.append(line)
            # Stop once we have captured a few updates to keep tests fast
            if len(event_lines) >= 8:
                break
                
        # Assert that we received SSE updates
        has_update_event = any("event: update" in l for l in event_lines)
        has_update_data = any("data:" in l for l in event_lines)
        assert has_update_event
        assert has_update_data
        
        # Check if the data chunk contains expected keys
        for line in event_lines:
            if line.startswith("data:"):
                data_str = line[5:].strip()
                data_json = json.loads(data_str)
                assert "status" in data_json
                assert "run_log" in data_json
                break

def test_api_client_disconnect_persistence():
    """Verify that a client disconnecting mid-stream does not kill the run.
    The background thread should complete, writing checkpoints and files.
    """
    import time
    thread_id = "test-disconnect-persistence-thread"
    url = f"/api/generate?spec=Build a calculator&thread_id={thread_id}&output_dir=temp_disconnect_test_output"
    
    # Start the stream and read the first event, then cancel immediately
    with client.stream("GET", url) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("data:"):
                # We got the first event, now disconnect
                break
                
    # Wait for the background thread to finish running mock nodes (takes ~0.5s in mock mode)
    time.sleep(1.5)
    
    # Assert that the thread is registered in the checkpointer database
    threads_res = client.get("/api/threads")
    assert threads_res.status_code == 200
    thread_ids = [t["thread_id"] for t in threads_res.json()]
    assert thread_id in thread_ids
    
    # Assert that the full state and files were successfully saved and can be lazy-loaded
    detail_res = client.get(f"/api/threads/{thread_id}")
    assert detail_res.status_code == 200
    detail_json = detail_res.json()
    assert detail_json["thread_id"] == thread_id
    assert detail_json["status"] == "done"
    assert "calculator.py" in detail_json["files"]
    assert "README.md" in detail_json["files"]

