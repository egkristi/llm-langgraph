"""
Message processing utilities for group chats.
Handles code extraction and storage from agent messages.
"""

from typing import Dict, Any, List, Optional
from utils.code_extractor import (
    extract_code_blocks, 
    save_code_blocks_to_workspace,
    generate_execution_suggestion
)

def process_agent_message(
    message: str, 
    agent_name: str, 
    group_chat_name: str,
    round_num: int = 1
) -> Dict[str, Any]:
    """
    Process an agent message to extract and store code blocks.
    
    Args:
        message: The agent's message text
        agent_name: Name of the agent
        group_chat_name: Name of the group chat
        round_num: The current round number
        
    Returns:
        Dictionary with processed message and metadata
    """
    # Extract code blocks from the message
    code_blocks = extract_code_blocks(message)
    
    # Save code blocks to the workspace if any were found
    saved_files = []
    execution_suggestion = ""
    
    if code_blocks:
        # Save the code blocks to the workspace
        saved_files = save_code_blocks_to_workspace(
            code_blocks, 
            group_chat_name,
            agent_name
        )
        
        # Generate execution suggestions for the Code Runner
        execution_suggestion = generate_execution_suggestion(saved_files)
        
        # Append code storage information to the message if files were saved
        if saved_files:
            file_info = "\n\n---\n**Code blocks saved to workspace:**\n"
            for file in saved_files:
                file_info += f"- `{file['filename']}` ({file['language']})\n"
            
            # Create a direct command for the Code Runner to execute the code
            execution_commands = ""
            
            # Only create commands if this message isn't from the Code Runner itself
            if agent_name != "codeExecutor":
                # Get the first file to execute as an example
                example_file = saved_files[0] if saved_files else None
                
                if example_file:
                    # Create a very explicit command for the Code Runner to execute
                    file_to_run = example_file['filename']
                    language = example_file['language']
                    
                    # Format a direct run_code command that can be copy-pasted
                    execution_commands = f"\n\n@codeExecutor EXECUTE THIS CODE NOW:\n"
                    execution_commands += f"```\nrun_code(file_name=\"{file_to_run}\", language=\"{language}\")\n```\n"
                    execution_commands += f"This is a direct command to execute the code file `{file_to_run}` that was just saved to the workspace.\n"
            
            # Add detailed execution instructions and file information
            execution_details = f"\n{execution_suggestion}"
            
            # Append all the information to the original message
            message += file_info + execution_details + execution_commands
    
    # Return the processed message and metadata
    return {
        "content": message,
        "code_blocks": code_blocks,
        "saved_files": saved_files,
        "execution_suggestion": execution_suggestion,
        "has_code": len(code_blocks) > 0
    }
