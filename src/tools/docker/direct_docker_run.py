#!/usr/bin/env python3
"""
Direct Docker Execution Tool

This script provides a simpler, more reliable way to execute code in Docker containers.
It addresses issues with volume mounting and path resolution.
"""

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

def execute_in_docker(file_path, language="python"):
    """Execute a file in a Docker container with proper volume mounting."""
    # Validate file exists
    file_path = Path(file_path).absolute()
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist")
        return False
    
    # Get file directory and name
    file_dir = file_path.parent
    file_name = file_path.name
    
    # Create output directory next to the file
    output_dir = file_dir.parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Generate unique IDs
    execution_id = str(uuid.uuid4())[:8]
    container_name = f"docker_exec_{execution_id}"
    output_file = output_dir / f"result_{execution_id}.txt"
    
    # Determine language configuration
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
    
    if language.lower() not in language_configs:
        print(f"Error: Unsupported language '{language}'")
        return False
    
    lang_config = language_configs[language.lower()]
    
    # Create a direct Docker run command
    docker_cmd = [
        "docker", "run",
        "--rm",  # Remove container after execution
        "--name", container_name,
        "--network=none",  # No network access
        "--memory=256m",  # Memory limit
        "--cpus=0.5",  # CPU limit
        "-v", f"{file_dir}:/workdir:ro",  # Mount code directory as read-only
        "-v", f"{output_dir}:/output:rw",  # Mount output with write permissions
        "-w", "/workdir",  # Set working directory to code dir
        lang_config["image"],
        "bash", "-c", f"echo '=== Docker Execution ==='; "
                     f"echo 'Running {file_name}'; "
                     f"echo 'Working directory:'; pwd; "
                     f"echo 'Directory contents:'; ls -la; "
                     f"echo '=== Beginning Execution ==='; "
                     f"{lang_config['cmd']} {file_name} 2>&1 | tee /output/{output_file.name}; "
                     f"echo '=== Execution Complete ==='"
    ]
    
    # Print command for debugging
    print(f"Executing: {' '.join(docker_cmd)}")
    
    # Run Docker command
    start_time = time.time()
    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True)
        execution_time = time.time() - start_time
        
        # Check results and look for Python exceptions in the output
        if output_file.exists():
            with open(output_file, 'r') as f:
                output = f.read()
        else:
            output = result.stdout
            print(f"Warning: No output file was created at {output_file}")
            
        # Check for Python exceptions or errors in the output
        python_exceptions = [
            "Traceback (most recent call last):", 
            "ModuleNotFoundError:", 
            "ImportError:",
            "SyntaxError:",
            "NameError:",
            "TypeError:",
            "ValueError:",
            "IndexError:",
            "KeyError:",
            "AttributeError:",
            "ZeroDivisionError:",
            "RuntimeError:",
            "Exception:"
        ]
        
        # Check if the output contains any Python exceptions
        has_exception = any(exc in output for exc in python_exceptions)
        
        if result.returncode == 0 and not has_exception:
            print(f"\nExecution successful in {execution_time:.2f}s")
            print(f"\nOutput from {file_name}:\n")
            print(output)
            return True
        else:
            # If there's an exception or non-zero return code, it's an error
            print(f"\nExecution failed in {execution_time:.2f}s")
            print(f"Python exception detected in output" if has_exception else f"Return code: {result.returncode}")
            print(f"\nError output:\n")
            print(output)
            return False
            
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"\nExecution error in {execution_time:.2f}s: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python direct_docker_run.py <file_path> [language]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "python"
    
    success = execute_in_docker(file_path, language)
    sys.exit(0 if success else 1)
