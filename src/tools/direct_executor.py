"""
Direct code execution module that bypasses the agent system for testing.
This ensures code is executed in Docker containers directly.
"""

import os
import subprocess
import time
import uuid
from pathlib import Path

def direct_execute_code(file_name: str, group_chat_name: str, language: str = "python"):
    """
    Directly execute a code file in a Docker container.
    
    Args:
        file_name: Name of the file to execute
        group_chat_name: Name of the group chat
        language: Programming language (default: python)
    
    Returns:
        Execution results
    """
    # Create a container tracking file for debugging
    with open("/tmp/docker_containers.log", "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Executing {file_name} for {group_chat_name} in {language}\n")
    print(f"DIRECT EXECUTOR: Executing {file_name} for {group_chat_name} in {language}")
    
    # Language configurations
    language_configs = {
        "python": {
            "image": "python:3.11-slim",
            "cmd": "python"
        },
        "javascript": {
            "image": "node:18-slim",
            "cmd": "node"
        },
        "go": {
            "image": "golang:1.20-alpine",
            "cmd": "go run"
        }
    }
    
    # Get language configuration
    if language.lower() not in language_configs:
        return f"Error: Unsupported language '{language}'"
    
    lang_config = language_configs[language.lower()]
    
    # Import workspace manager
    from utils.workspace_manager import get_workspace_path
    
    # Get workspace paths using the utility function
    workspace_path = get_workspace_path(group_chat_name, create_if_missing=True)
    code_dir = workspace_path / "code"
    output_dir = workspace_path / "output"
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    # Generate unique output file name
    execution_id = str(uuid.uuid4())[:8]
    output_file = f"result_{execution_id}.txt"
    output_path = output_dir / output_file
    container_name = f"direct_execution_{execution_id}"
    
    # Print some debug info
    print(f"DIRECT EXECUTOR: Code directory: {code_dir} (exists: {code_dir.exists()})")
    print(f"DIRECT EXECUTOR: Output directory: {output_dir} (exists: {output_dir.exists()})")
    
    # Ensure directories exist
    code_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a test file in the output directory to verify permissions
    test_file = output_dir / "docker_test.txt"
    with open(test_file, "w") as f:
        f.write(f"Docker test file created at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Define the Docker command with absolute paths and explicit mount points
    docker_cmd = [
        "docker", "run",
        "--rm",  # Remove container after execution
        "--name", container_name,
        "--network=none",  # No network access
        "--memory=256m",  # Memory limit
        "--cpus=0.5",  # CPU limit
        "-v", f"{code_dir.absolute()}:/code:ro",  # Mount code as read-only (with absolute path)
        "-v", f"{output_dir.absolute()}:/output:rw",  # Mount output with write permissions (with absolute path)
        "-w", "/code",  # Set working directory
        lang_config["image"],
        "bash", "-c", f"set -x && \
                        echo '=== Docker Execution Log ==='; \
                        echo 'File: {file_name}'; \
                        echo 'Language: {language}'; \
                        echo 'Container: {container_name}'; \
                        echo 'Time: '$(date); \
                        echo '=== Environment ==='; \
                        pwd; \
                        echo '=== Directory Listing ==='; \
                        ls -la /; \
                        ls -la /code || echo '/code directory not accessible'; \
                        echo '=== Beginning Execution ==='; \
                        if [ -f /code/{file_name} ]; then \
                            cd /code && {lang_config['cmd']} {file_name}; \
                            EXIT_CODE=$?; \
                        else \
                            echo 'ERROR: File not found: /code/{file_name}'; \
                            ls -la /code; \
                            EXIT_CODE=1; \
                        fi; \
                        echo '=== Execution Complete ==='; \
                        echo 'Exit code:' $EXIT_CODE; \
                        echo 'Test file write to output directory:'; \
                        echo 'Test output from container' > /output/container_test.txt; \
                        exit $EXIT_CODE"
    ]
    
    # Create command to run and capture output
    cmd_str = ' '.join(docker_cmd) + f" > {output_path} 2>&1"
    
    print(f"DIRECT EXECUTOR: Running command: {cmd_str}")
    
    try:
        # Run the docker command with shell=True to handle output redirection
        start_time = time.time()
        try:
            # Execute the command directly with shell=True
            process = subprocess.run(
                cmd_str, 
                shell=True, 
                text=True,
                timeout=30  # Add timeout to prevent hanging
            )
            execution_time = time.time() - start_time
            
            # Check if Docker command was successful
            if process.returncode == 0:
                # Read the output file
                if output_path.exists():
                    with open(output_path, 'r') as f:
                        output = f.read()
                else:
                    output = "Execution produced no output file"
                
                print(f"DIRECT EXECUTOR: Execution successful in {execution_time:.2f}s")
                success = True
            else:
                # Read the error output file
                if output_path.exists():
                    with open(output_path, 'r') as f:
                        output = f.read()
                else:
                    output = "Execution failed but produced no output file"
                    
                print(f"DIRECT EXECUTOR: Execution failed with code {process.returncode} in {execution_time:.2f}s")
                print(f"DIRECT EXECUTOR: Error: {output[:500]}...")
                success = False
                
                # Log the full error details to a file for debugging
                error_log_path = Path("/tmp/docker_execution_errors.log")
                with open(error_log_path, "a") as f:
                    f.write(f"\n--- ERROR LOG {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                    f.write(f"Command: {cmd_str}\n")
                    f.write(f"Return code: {process.returncode}\n")
                    f.write(f"Output:\n{output}\n")
                    f.write("--------------------------------------\n")
        except subprocess.TimeoutExpired:
            output = "Execution timed out after 30 seconds"
            execution_time = time.time() - start_time
            print(f"DIRECT EXECUTOR: Execution timed out after {execution_time:.2f}s")
            success = False
        except Exception as e:
            output = f"Exception during execution: {str(e)}"
            execution_time = time.time() - start_time
            print(f"DIRECT EXECUTOR: Execution failed with exception in {execution_time:.2f}s")
            print(f"DIRECT EXECUTOR: Error: {str(e)}")
            success = False
            
        # Process results
        if success:
            # Format success message
            success_message = f"## Code Execution Successful\n\n"
            success_message += f"**File:** `{file_name}`\n\n"
            success_message += f"**Language:** {language}\n\n"
            success_message += f"**Execution Time:** {execution_time:.2f} seconds\n\n"
            success_message += f"### Output:\n\n```\n{output}\n```\n\n"
            
            return success_message
        else:
            # Format error message
            error_message = f"## Code Execution Failed\n\n"
            error_message += f"**File:** `{file_name}`\n\n"
            error_message += f"**Language:** {language}\n\n"
            error_message += f"**Execution Time:** {execution_time:.2f} seconds\n\n"
            error_message += f"**Error:**\n\n```\n{output}\n```\n\n"
            
            return error_message
    
    except subprocess.TimeoutExpired:
        print(f"DIRECT EXECUTOR: Execution timed out after 30 seconds")
        return f"Error: Code execution timed out after 30 seconds"
    
    except Exception as e:
        print(f"DIRECT EXECUTOR: Error executing code: {str(e)}")
        return f"Error executing code: {str(e)}"
