from typing import Optional, Dict, List, Any
import os
import uuid
import tempfile
import subprocess
import json
import time
import logging
from pathlib import Path
from langchain_core.tools import BaseTool, tool
from utils.workspace_manager import save_file, get_workspace_path, list_files

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='/tmp/code_runner.log',
                   filemode='a')

# Dictionary to store information about running containers
_running_containers: Dict[str, Dict[str, Any]] = {}

@tool
def run_code(code: str, language: str, file_name: str = "", group_chat_name: str = "Default Group Chat", timeout: int = 10) -> str:
    """
    Run code in a Docker container and save it to the group chat's workspace.
    
    Args:
        code: The code to run
        language: The language the code is written in (python, javascript, go, etc.)
        file_name: Optional name for the code file (if not provided, a name will be generated)
        group_chat_name: Name of the group chat workspace to use
        timeout: Maximum execution time in seconds (default: 10)
        
    Returns:
        The output of the code execution or error message
    """
    logging.info(f"run_code called with language={language}, file_name={file_name}, group_chat={group_chat_name}")
    logging.info(f"Code snippet: {code[:100]}...")
    print(f"CODE RUNNER: Executing {language} code for {group_chat_name}")
    # Only support certain languages for security
    supported_languages = {
        "python": {
            "image": "python:3.11-slim",
            "file_ext": "py",
            "cmd": "python",
            "install_cmd": "pip install",
            "packages": []
        },
        "javascript": {
            "image": "node:18-slim",
            "file_ext": "js",
            "cmd": "node",
            "install_cmd": "npm install",
            "packages": []
        },
        "go": {
            "image": "golang:1.20-alpine",
            "file_ext": "go",
            "cmd": "go run",
            "install_cmd": "go get",
            "packages": []
        }
    }
    
    if language.lower() not in supported_languages:
        return f"Error: Unsupported language '{language}'. Supported languages: {', '.join(supported_languages.keys())}"
    
    # Get language configuration
    lang_config = supported_languages[language.lower()]
    
    # Create a unique ID for this execution
    execution_id = str(uuid.uuid4())[:8]
    container_name = f"code_runner_{language.lower()}_{execution_id}"
    
    # Generate file name if not provided
    if not file_name:
        file_name = f"script_{execution_id}.{lang_config['file_ext']}"
    elif not file_name.endswith(f".{lang_config['file_ext']}"):
        file_name = f"{file_name}.{lang_config['file_ext']}"
    
    try:
        # Save code to workspace
        workspace_path = get_workspace_path(group_chat_name)
        logging.info(f"Workspace path: {workspace_path}")
        code_path = save_file(group_chat_name, code, file_name, "code")
        logging.info(f"Code saved to: {code_path}")
        
        # Create mount path for Docker
        code_dir = workspace_path / "code"
        output_dir = workspace_path / "output"
        logging.info(f"Code directory: {code_dir}, Output directory: {output_dir}")
        
        # Ensure output directory exists
        output_dir.mkdir(exist_ok=True)
        print(f"CODE RUNNER: Code saved to {code_path}")
        
        # Create a file to store execution results
        output_file = f"result_{execution_id}.txt"
        output_path = output_dir / output_file
        
        # Check if the Docker image is available locally before pulling
        check_image_cmd = ["docker", "images", "-q", lang_config["image"]]
        try:
            image_exists = subprocess.run(check_image_cmd, capture_output=True, text=True).stdout.strip() != ""
        except Exception:
            image_exists = False
            
        # If image doesn't exist locally, pull it automatically
        if not image_exists:
            logging.info(f"Docker image '{lang_config['image']}' not found locally. Pulling it...")
            print(f"CODE RUNNER: Docker image '{lang_config['image']}' not found locally. Pulling it...")
            
            try:
                # Attempt to pull the Docker image
                pull_cmd = ["docker", "pull", lang_config["image"]]
                pull_result = subprocess.run(
                    pull_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60  # Give it up to 60 seconds to pull the image
                )
                
                if pull_result.returncode == 0:
                    # Successfully pulled the image
                    logging.info(f"Successfully pulled Docker image '{lang_config['image']}'")
                    print(f"CODE RUNNER: Successfully pulled Docker image '{lang_config['image']}'")
                else:
                    # Failed to pull the image
                    error_msg = f"Failed to pull Docker image '{lang_config['image']}'. Error: {pull_result.stderr}"
                    logging.error(error_msg)
                    print(f"CODE RUNNER: {error_msg}")
                    
                    # Write error to output file
                    with open(output_path, 'w') as f:
                        f.write(f"Error: {error_msg}\n\n")
                        f.write(f"Docker is required to execute code. No fallback execution methods are available.")
                    
                    return f"Code saved to: {file_name}\n\nError: {error_msg}\n\nDocker is required to execute code. No fallback execution methods are available."
            
            except Exception as e:
                # Handle any error in the pull process
                error_msg = f"Error pulling Docker image: {str(e)}"
                logging.error(error_msg)
                print(f"CODE RUNNER: {error_msg}")
                
                # Write error to output file
                with open(output_path, 'w') as f:
                    f.write(f"Error: {error_msg}\n\n")
                    f.write(f"Docker is required to execute code. No fallback execution methods are available.")
                
                return f"Code saved to: {file_name}\n\nError: {error_msg}\n\nDocker is required to execute code. No fallback execution methods are available."
        
        # Convert paths to absolute paths with proper formatting for Docker
        abs_code_dir = os.path.abspath(code_dir)
        abs_output_dir = os.path.abspath(output_dir)
        
        # Debug print the mount paths
        print(f"CODE RUNNER: Mounting code directory: {abs_code_dir}")
        print(f"CODE RUNNER: Mounting output directory: {abs_output_dir}")
        print(f"CODE RUNNER: Will execute: {lang_config['cmd']} {file_name}")
        
        # Set up Docker run command with proper security constraints
        cmd = [
            "docker", "run",
            "--name", container_name,
            "--rm",  # Remove container after execution
            "--network=none",  # No network access
            "--memory=256m",  # Memory limit
            "--cpus=0.5",  # CPU limit
            "--pids-limit=50",  # Process limit
            "--read-only",  # Read-only filesystem except for specific mounts
            "-v", f"{abs_code_dir}:/code:ro",  # Mount code as read-only
            "-v", f"{abs_output_dir}:/output:rw",  # Mount output with write permissions
            "-w", "/code",  # Set working directory
            "--security-opt=no-new-privileges",  # No privilege escalation
            lang_config["image"],
            "sh", "-c", f"ls -la /code && {lang_config['cmd']} {file_name} | tee /output/{output_file}"
        ]
        
        # Log the command
        docker_cmd_str = " ".join(cmd)
        logging.info(f"Running Docker command: {docker_cmd_str}")
        print(f"CODE RUNNER: Executing Docker command: {docker_cmd_str[:100]}...")
        
        # Track container start time
        start_time = time.time()
        _running_containers[container_name] = {
            "start_time": start_time,
            "language": language,
            "file_name": file_name,
            "group_chat": group_chat_name,
            "code": code[:500] + "..." if len(code) > 500 else code  # Truncate long code
        }
        
        try:
            # Run the Docker container with timeout
            logging.info(f"About to execute subprocess with timeout={timeout}")
            print(f"CODE RUNNER: Starting Docker execution with timeout={timeout}s")
            
            # Execute the Docker command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Log the execution results
            logging.info(f"Subprocess completed with return code: {result.returncode}")
            print(f"CODE RUNNER: Docker execution completed with return code: {result.returncode}")
            
            # Clean up container info
            if container_name in _running_containers:
                del _running_containers[container_name]
                logging.info(f"Removed container {container_name} from tracking")
            
            # Read the output file
            output_content = ""
            try:
                output_file_path = output_dir / output_file
                logging.info(f"Attempting to read output from {output_file_path}")
                print(f"CODE RUNNER: Reading execution output from {output_file_path}")
                
                with open(output_file_path, 'r') as f:
                    output_content = f.read()
                    logging.info(f"Read {len(output_content)} bytes from output file")
                    print(f"CODE RUNNER: Found {len(output_content)} bytes of output")
            except Exception as e:
                # If output file doesn't exist, use stderr
                logging.error(f"Error reading output file: {str(e)}")
                print(f"CODE RUNNER: Error reading output file: {str(e)}")
                output_content = result.stderr
                logging.info(f"Using stderr as output: {output_content[:100]}...")
                print(f"CODE RUNNER: Using stderr as output")
                
            # Also log stdout and stderr
            logging.info(f"STDOUT: {result.stdout[:200]}...")
            logging.info(f"STDERR: {result.stderr[:200]}...")
            
            # Process and return results
            execution_time = time.time() - start_time
            logging.info(f"Total execution time: {execution_time:.2f} seconds")
            print(f"CODE RUNNER: Execution completed in {execution_time:.2f} seconds")
            
            if result.returncode == 0:
                # Execution succeeded
                output = output_content.strip() if output_content else result.stdout.strip()
                logging.info(f"Execution successful with output length: {len(output)}")
                print(f"CODE RUNNER: Execution successful with output length: {len(output)}")
                
                # Save the file listing
                workspace_files = list_files(group_chat_name)
                file_listing = "\n".join([f"- {f['path']}" for f in workspace_files[:10]])
                logging.info(f"Workspace files: {file_listing}")
                
                # Format a detailed success message
                success_message = f"## Code Execution Successful\n\n"
                success_message += f"**File:** `{file_name}`\n\n"
                success_message += f"**Language:** {language}\n\n"
                success_message += f"**Execution Time:** {execution_time:.2f} seconds\n\n"
                success_message += f"### Output:\n\n```\n{output}\n```\n\n"
                success_message += f"### Workspace Files:\n{file_listing}\n"
                
                return success_message
            else:
                # Execution failed
                error_msg = result.stderr.strip()
                logging.error(f"Execution failed with error: {error_msg[:200]}...")
                print(f"CODE RUNNER: Execution failed with error")
                
                # Save error to output file
                error_file = output_dir / f"error_{execution_id}.txt"
                with open(error_file, 'w') as f:
                    f.write(f"Error executing {language} code:\n{error_msg}")
                logging.info(f"Error saved to {error_file}")
                
                # Format a detailed error message
                error_message = f"## Code Execution Failed\n\n"
                error_message += f"**File:** `{file_name}`\n\n"
                error_message += f"**Language:** {language}\n\n"
                error_message += f"**Error:**\n\n```\n{error_msg}\n```\n\n"
                error_message += f"The error has been saved to `{error_file.name}` in the workspace output folder.\n"
                
                return error_message
        
        except subprocess.TimeoutExpired:
            # Kill the container if it's still running
            subprocess.run(["docker", "kill", container_name], capture_output=True)
            
            # Save timeout message to output file
            with open(output_path, 'w') as f:
                f.write(f"Error: Code execution timed out after {timeout} seconds")
            
            return f"Code saved to: {file_name}\n\nError: Code execution timed out after {timeout} seconds"
    
    except Exception as e:
        # Handle any other exceptions
        return f"Error: {str(e)}"
    
    finally:
        # Clean up any lingering container
        try:
            if container_name in _running_containers:
                del _running_containers[container_name]
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        except:
            pass

@tool
def list_running_code(group_chat_name: str = "") -> str:
    """
    List all currently running code executions.
    
    Args:
        group_chat_name: Optional group chat name to filter by
        
    Returns:
        Information about running code executions
    """
    if not _running_containers:
        return "No code is currently running."
    
    # Filter by group chat if specified
    filtered_containers = _running_containers
    if group_chat_name:
        filtered_containers = {k: v for k, v in _running_containers.items() 
                              if v.get("group_chat", "") == group_chat_name}
        
        if not filtered_containers:
            return f"No code is currently running for group chat '{group_chat_name}'."
    
    result = "Currently running code:\n"
    current_time = time.time()
    
    for container_name, info in filtered_containers.items():
        elapsed = current_time - info["start_time"]
        result += f"- ID: {container_name}\n"
        result += f"  Language: {info['language']}\n"
        if "file_name" in info:
            result += f"  File: {info['file_name']}\n"
        if "group_chat" in info:
            result += f"  Group Chat: {info['group_chat']}\n"
        result += f"  Running for: {elapsed:.2f} seconds\n"
        result += f"  Code snippet: {info['code'][:100]}...\n\n"
    
    return result

@tool
def kill_running_code(container_id: str) -> str:
    """
    Kill a running code execution.
    
    Args:
        container_id: ID of the container to kill
        
    Returns:
        Status message
    """
    # Check if container exists in our tracking
    if not container_id.startswith("code_runner_"):
        return f"Error: '{container_id}' is not a valid code runner container ID"
    
    if container_id not in _running_containers:
        return f"Error: No running container with ID '{container_id}' found"
    
    try:
        # Kill the container
        result = subprocess.run(
            ["docker", "kill", container_id],
            capture_output=True,
            text=True
        )
        
        # Clean up container info
        if container_id in _running_containers:
            del _running_containers[container_id]
        
        if result.returncode == 0:
            return f"Successfully killed code execution '{container_id}'"
        else:
            return f"Error killing container: {result.stderr.strip()}"
    
    except Exception as e:
        return f"Error: {str(e)}"

# Helper function to check if Docker is available
def docker_available() -> bool:
    """Check if Docker is available on the system."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False
