#!/usr/bin/env python3
"""
Standalone Docker Code Executor Tool

This script provides a command-line interface to execute code in Docker containers
directly from the workspace. It can be used to test and debug code execution without
going through the group chat interface.

Usage:
  python docker_executor.py <group_chat_name> <file_name> <language>

Example:
  python docker_executor.py coding_group_chat verify_docker.py python
"""

import sys
import os
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import the direct executor
from tools.direct_executor import direct_execute_code

def main():
    if len(sys.argv) < 4:
        print("Usage: python docker_executor.py <group_chat_name> <file_name> <language>")
        sys.exit(1)
    
    group_chat_name = sys.argv[1]
    file_name = sys.argv[2]
    language = sys.argv[3]
    
    print(f"=== Docker Code Executor ===")
    print(f"Group Chat: {group_chat_name}")
    print(f"File: {file_name}")
    print(f"Language: {language}")
    
    # Import the workspace manager utility
    from utils.workspace_manager import get_workspace_path
    
    # Get the workspace path using the utility function
    workspace_path = get_workspace_path(group_chat_name, create_if_missing=False)
    code_dir = workspace_path / "code"
    file_path = code_dir / file_name
    
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist")
        sys.exit(1)
    
    print(f"File exists: {file_path}")
    
    # Execute the code
    start_time = time.time()
    print("\nExecuting in Docker container...")
    try:
        result = direct_execute_code(file_name, group_chat_name, language)
        execution_time = time.time() - start_time
        
        print(f"\nExecution completed in {execution_time:.2f} seconds")
        print("\nResult:")
        print(result)
        
        # Check if the result contains an error message
        if "Error executing" in result:
            print("\n⚠️ Execution failed with errors. See details above.")
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"\n❌ Execution failed in {execution_time:.2f} seconds")
        print(f"Error: {str(e)}")
        print("\nDetailed exception:")
        import traceback
        traceback.print_exc()
    
    # Get the output file using the workspace manager
    output_dir = workspace_path / "output"
    output_files = [f for f in output_dir.glob("result_*.txt")]
    output_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    if output_files:
        latest_output = output_files[0]
        print(f"\nLatest output file: {latest_output}")
        with open(latest_output, 'r') as f:
            print(f"\nOutput file contents:")
            print(f.read())
    
    print("\nVerify execution with:")
    print(f"  docker ps -a | grep code_runner")
    
if __name__ == "__main__":
    main()
