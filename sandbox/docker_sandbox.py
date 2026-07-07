import os
import shutil
import tempfile
import time
import docker
from typing import Dict, List, Tuple

def run_in_sandbox(
    files: Dict[str, str], 
    test_files: Dict[str, str], 
    image_name: str = "assistant-sandbox:latest",
    timeout: int = 15,
    mem_limit: str = "64m"
) -> Tuple[int, str]:
    """
    Executes Python files and tests in an isolated, network-disabled Docker container.
    Returns:
        Tuple[int, str]: (exit_code, stdout/stderr combined output)
    """
    workspace_temp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace_temp"))
    os.makedirs(workspace_temp, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=workspace_temp)
    
    try:
        for filename, content in files.items():
            file_path = os.path.join(temp_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        for filename, content in test_files.items():
            file_path = os.path.join(temp_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        try:
            client = docker.from_env()
        except Exception as e:
            return 1, f"Docker client initialization failed: {str(e)}. Make sure Docker Desktop is running."
            
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            try:
                client.images.get("python:3.12-slim")
                image_name = "python:3.12-slim"
            except docker.errors.ImageNotFound:
                try:
                    client.images.pull("python", tag="3.12-slim")
                    image_name = "python:3.12-slim"
                except Exception as pull_err:
                    return 1, f"Failed to pull base python image: {str(pull_err)}"

        container = None
        try:
            container = client.containers.create(
                image=image_name,
                command="pytest --tb=short",
                network_disabled=True,
                mem_limit=mem_limit,
                volumes={
                    temp_dir: {
                        "bind": "/workspace",
                        "mode": "ro"
                    }
                },
                working_dir="/workspace",
                detach=True
            )
            
            container.start()
            start_time = time.time()
            exit_code = None
            
            while time.time() - start_time < timeout:
                container.reload()
                status = container.status
                if status == "exited":
                    result = container.wait()
                    exit_code = result.get("StatusCode", 0)
                    break
                time.sleep(0.5)
            else:
                try:
                    container.kill()
                except Exception:
                    pass
                return 124, "TIMEOUT: Execution exceeded the time limit inside sandbox container."
                
            logs = container.logs(stdout=True, stderr=True).decode("utf-8")
            return exit_code, logs
            
        except Exception as run_err:
            return 1, f"Container execution error: {str(run_err)}"
            
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
                    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def run_analysis_in_sandbox(
    files: Dict[str, str],
    image_name: str = "assistant-sandbox:latest",
    timeout: int = 15,
    mem_limit: str = "64m"
) -> Dict[str, List[str]]:
    """
    Runs static analysis (ruff, mypy, bandit) inside the Docker sandbox.
    Returns:
        Dict[str, List[str]]: Map of filepath -> list of lint issues found.
    """
    workspace_temp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace_temp"))
    os.makedirs(workspace_temp, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=workspace_temp)
    
    findings = {}
    for filepath in files.keys():
        findings[filepath] = []
        
    try:
        # Write files to check
        for filename, content in files.items():
            # Skip test files or configuration files for generic lint checks if we want to focus on src
            file_path = os.path.join(temp_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        try:
            client = docker.from_env()
        except Exception:
            # Fallback if docker client fails (e.g. Docker not running)
            return {"system": ["Docker not running. Skipping static analysis."]}
            
        # Ensure image exists
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            # If not built, static analysis tools won't be available inside generic python image
            # Return empty to allow flow to continue, or report missing tool
            return {"system": [f"Image {image_name} not found. Cannot run static analysis."]}

        # Run Ruff
        ruff_out = run_tool_in_container(client, image_name, "ruff check .", temp_dir, mem_limit, timeout)
        parse_tool_output(ruff_out, "ruff", findings)

        # Run MyPy
        mypy_out = run_tool_in_container(client, image_name, "mypy . --ignore-missing-imports", temp_dir, mem_limit, timeout)
        parse_tool_output(mypy_out, "mypy", findings)

        # Run Bandit
        bandit_out = run_tool_in_container(client, image_name, "bandit -r . -f txt", temp_dir, mem_limit, timeout)
        parse_tool_output(bandit_out, "bandit", findings)
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    # Clean up empty file lists
    return {k: v for k, v in findings.items() if v}

def run_tool_in_container(
    client: docker.DockerClient,
    image_name: str,
    command: str,
    temp_dir: str,
    mem_limit: str,
    timeout: int
) -> str:
    container = None
    try:
        container = client.containers.create(
            image=image_name,
            command=command,
            network_disabled=True,
            mem_limit=mem_limit,
            volumes={
                temp_dir: {
                    "bind": "/workspace",
                    "mode": "ro"
                }
            },
            working_dir="/workspace",
            detach=True
        )
        container.start()
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            container.reload()
            if container.status == "exited":
                break
            time.sleep(0.2)
        else:
            try:
                container.kill()
            except Exception:
                pass
            return "TIMEOUT during tool execution."
            
        return container.logs(stdout=True, stderr=True).decode("utf-8")
    except Exception as e:
        return f"Error executing tool: {str(e)}"
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass

def parse_tool_output(output: str, tool_name: str, findings: Dict[str, List[str]]):
    """
    Parses output of lint tools and assigns lines to respective files in the findings dict.
    """
    if not output or "Error executing tool" in output:
        return
        
    for line in output.splitlines():
        # Match standard file paths in output lines
        for filepath in findings.keys():
            # If the filename is in the line, associate it
            if filepath in line:
                findings[filepath].append(f"[{tool_name.upper()}] {line.strip()}")
