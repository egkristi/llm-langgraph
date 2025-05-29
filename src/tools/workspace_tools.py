from typing import List, Dict, Any, Optional
import os
from pathlib import Path
from langchain_core.tools import BaseTool, tool
from utils.workspace_manager import list_files as ws_list_files
from utils.workspace_manager import read_file as ws_read_file
from utils.workspace_manager import save_file as ws_save_file
from utils.workspace_manager import get_workspace_info as ws_get_workspace_info
from utils.workspace_manager import get_workspace_path, ensure_workspace_dir

@tool
def list_workspace_files(group_chat_name: str = "Default Group Chat", subfolder: str = "") -> str:
    """
    List all files in a group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        subfolder: Optional subfolder to list files from (code, data, output)
        
    Returns:
        Information about workspace files
    """
    try:
        files = ws_list_files(group_chat_name, subfolder)
        
        if not files:
            if subfolder:
                return f"No files found in workspace '{group_chat_name}' subfolder '{subfolder}'."
            else:
                return f"No files found in workspace '{group_chat_name}'."
        
        # Format file information
        result = f"Files in workspace '{group_chat_name}'"
        if subfolder:
            result += f" subfolder '{subfolder}'"
        result += ":\n\n"
        
        for file in files:
            result += f"- {file['path']}\n"
            result += f"  Size: {file['size']} bytes, Modified: {file['modified']}\n"
        
        return result
    
    except Exception as e:
        return f"Error listing workspace files: {str(e)}"

@tool
def read_workspace_file(group_chat_name: str, file_name: str, subfolder: str = "code") -> str:
    """
    Read a file from a group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        file_name: Name of the file to read
        subfolder: Subfolder within the workspace (default: code)
        
    Returns:
        Content of the file or error message
    """
    try:
        content = ws_read_file(group_chat_name, file_name, subfolder)
        
        if content is None:
            return f"File '{file_name}' not found in workspace '{group_chat_name}' subfolder '{subfolder}'."
        
        return f"Content of {file_name}:\n\n{content}"
    
    except Exception as e:
        return f"Error reading workspace file: {str(e)}"

@tool
def save_workspace_file(group_chat_name: str, file_content: str, file_name: str, 
                       subfolder: str = "data") -> str:
    """
    Save a file to a group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        file_content: Content to write to the file
        file_name: Name of the file
        subfolder: Subfolder within the workspace (default: data)
        
    Returns:
        Confirmation message or error
    """
    try:
        file_path = ws_save_file(group_chat_name, file_content, file_name, subfolder)
        
        # List all files in the workspace to show the updated state
        files = ws_list_files(group_chat_name)
        file_listing = "\n".join([f"- {f['path']}" for f in files[:10]])
        if len(files) > 10:
            file_listing += f"\n... and {len(files) - 10} more files"
        
        return f"File saved to: {file_path}\n\nWorkspace files:\n{file_listing}"
    
    except Exception as e:
        return f"Error saving workspace file: {str(e)}"

@tool
def get_workspace_details(group_chat_name: str = "Default Group Chat") -> str:
    """
    Get details about a group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        
    Returns:
        Information about the workspace
    """
    try:
        info = ws_get_workspace_info(group_chat_name)
        
        result = f"Workspace Details for '{group_chat_name}':\n\n"
        result += f"- Location: {info['path']}\n"
        result += f"- Code Files: {info['code_files']}\n"
        result += f"- Data Files: {info['data_files']}\n"
        result += f"- Output Files: {info['output_files']}\n"
        result += f"- Total Files: {info['total_files']}\n"
        result += f"- Total Size: {info['total_size']} bytes\n"
        
        return result
    
    except Exception as e:
        return f"Error getting workspace details: {str(e)}"
