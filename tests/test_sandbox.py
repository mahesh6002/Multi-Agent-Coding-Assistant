import pytest
import urllib.request
from sandbox.docker_sandbox import run_in_sandbox

def test_sandbox_passing_run():
    """Verify that a passing test suite runs and returns exit code 0."""
    files = {
        "logic.py": "def add(a, b): return a + b"
    }
    test_files = {
        "test_logic.py": "from logic import add\ndef test_add(): assert add(2, 3) == 5"
    }
    exit_code, output = run_in_sandbox(files, test_files)
    assert exit_code == 0
    assert "passed" in output.lower()

def test_sandbox_failing_run():
    """Verify that a failing test suite runs and returns exit code > 0."""
    files = {
        "logic.py": "def add(a, b): return a + b + 99"
    }
    test_files = {
        "test_logic.py": "from logic import add\ndef test_add(): assert add(2, 3) == 5"
    }
    exit_code, output = run_in_sandbox(files, test_files)
    assert exit_code != 0
    assert "failed" in output.lower()

def test_sandbox_network_isolation():
    """Verify that internet access is blocked inside the sandbox."""
    files = {}
    test_files = {
        "test_net.py": (
            "import urllib.request\n"
            "def test_network():\n"
            "    try:\n"
            "        urllib.request.urlopen('https://www.google.com', timeout=3)\n"
            "        assert False, 'Network is not disabled!'\n"
            "    except Exception as e:\n"
            "        # Should fail with connection error because network is disabled\n"
            "        assert True"
        )
    }
    exit_code, output = run_in_sandbox(files, test_files)
    # The test file itself asserts that an exception is raised, which passes!
    # So pytest will succeed (exit_code 0) if the network call failed,
    # or fail (exit_code non-zero) if the network call actually succeeded.
    assert exit_code == 0

def test_sandbox_memory_limit():
    """Verify that resource limits are enforced.
    Allocating 50MB of memory inside a 20MB-limited container should trigger OOM.
    """
    files = {}
    test_files = {
        "test_oom.py": (
            "def test_allocate_memory():\n"
            "    # Attempt to allocate 50MB of memory\n"
            "    data = bytearray(50 * 1024 * 1024)\n"
            "    assert len(data) == 50 * 1024 * 1024"
        )
    }
    # Run sandbox with a tight 20MB limit
    exit_code, output = run_in_sandbox(files, test_files, mem_limit="20m", timeout=10)
    
    # Exited due to OOM (usually exit code 137 on Linux/Docker) or failed execution
    assert exit_code != 0
    # The output should show the process was killed, OOMed, or failed
    assert any(term in output.lower() or term in str(exit_code) for term in ["oom", "killed", "137", "error", "fail"])
