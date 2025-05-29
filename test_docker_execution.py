#!/usr/bin/env python3
"""
Direct test script for Docker code execution.
This script will test Docker code execution directly, bypassing the agent system.
"""

import os
import sys
import subprocess
from pathlib import Path

# Define test parameters
test_group_chat = "test_chat"
test_file = "test_script.py"
language = "python"

# Get workspace path
workspace_root = Path("/Users/erling/code/llm-langgraph/workspaces")
workspace_path = workspace_root / test_group_chat
code_dir = workspace_path / "code"
output_dir = workspace_path / "output"

# Ensure output directory exists
output_dir.mkdir(exist_ok=True)

print(f"Testing Docker code execution with:")
print(f"- Group Chat: {test_group_chat}")
print(f"- File: {test_file}")
print(f"- Code directory: {code_dir}")
print(f"- Output directory: {output_dir}")

# Check if test file exists
test_file_path = code_dir / test_file
if not test_file_path.exists():
    print(f"Error: Test file {test_file_path} does not exist")
    sys.exit(1)

# Define Docker command
docker_cmd = [
    "docker", "run",
    "--rm",  # Remove container after execution
    "--name", "test_code_execution",
    "--network=none",  # No network access
    "-v", f"{code_dir}:/code:ro",  # Mount code as read-only
    "-v", f"{output_dir}:/output:rw",  # Mount output with write permissions
    "-w", "/code",  # Set working directory
    "python:3.11-slim",
    "sh", "-c", f"ls -la /code && python {test_file} | tee /output/test_result.txt"
]

# Print the command
print(f"\nExecuting Docker command:\n{' '.join(docker_cmd)}")

# Run Docker command
try:
    result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30)
    print(f"\nExit code: {result.returncode}")
    print(f"\nSTDOUT:\n{result.stdout}")
    print(f"\nSTDERR:\n{result.stderr}")
    
    # Check if output file was created
    output_file = output_dir / "test_result.txt"
    if output_file.exists():
        print(f"\nOutput file created: {output_file}")
        with open(output_file, 'r') as f:
            print(f"\nOutput file contents:\n{f.read()}")
    else:
        print(f"\nOutput file was not created")
        
except Exception as e:
    print(f"Error executing Docker command: {str(e)}")
