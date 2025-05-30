import os
import shutil
from pathlib import Path
import json
import time
from typing import List, Dict, Any, Optional

# Determine the project root directory dynamically
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Base path for all workspaces (relative to project root)
WORKSPACES_DIR = PROJECT_ROOT / "workspaces"

def ensure_workspace_dir():
    """Ensure the base workspaces directory exists."""
    WORKSPACES_DIR.mkdir(exist_ok=True, parents=True)

def get_workspace_path(group_chat_name: str, create_if_missing: bool = True) -> Path:
    """Get the workspace path for a group chat, optionally creating it if it doesn't exist."""
    # Normalize group chat name: convert spaces to underscores and lowercase
    # Also remove any characters that aren't alphanumeric, underscores, or hyphens
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in group_chat_name)
    safe_name = safe_name.replace(" ", "_").lower()
    
    # Create workspace path
    workspace_path = WORKSPACES_DIR / safe_name
    
    if create_if_missing:
        workspace_path.mkdir(exist_ok=True, parents=True)
        
        # Create subdirectories
        (workspace_path / "code").mkdir(exist_ok=True)
        (workspace_path / "data").mkdir(exist_ok=True)
        (workspace_path / "output").mkdir(exist_ok=True)
    
    return workspace_path

def save_file(group_chat_name: str, file_content: str, file_name: str, 
              subfolder: str = "code") -> str:
    """
    Save a file to the group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        file_content: Content to write to the file
        file_name: Name of the file
        subfolder: Subfolder within the workspace (default: code)
        
    Returns:
        Full path to the saved file
    """
    workspace_path = get_workspace_path(group_chat_name)
    subfolder_path = workspace_path / subfolder
    subfolder_path.mkdir(exist_ok=True)
    
    file_path = subfolder_path / file_name
    
    with open(file_path, "w") as f:
        f.write(file_content)
    
    return str(file_path)

def read_file(group_chat_name: str, file_name: str, 
              subfolder: str = "code") -> Optional[str]:
    """
    Read a file from the group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        file_name: Name of the file
        subfolder: Subfolder within the workspace (default: code)
        
    Returns:
        File content as string, or None if the file doesn't exist
    """
    workspace_path = get_workspace_path(group_chat_name)
    file_path = workspace_path / subfolder / file_name
    
    if not file_path.exists():
        return None
    
    with open(file_path, "r") as f:
        return f.read()

def list_files(group_chat_name: str, subfolder: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all files in a group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        subfolder: Optional subfolder to list files from
        
    Returns:
        List of dictionaries containing file information
    """
    workspace_path = get_workspace_path(group_chat_name)
    
    if subfolder:
        path_to_list = workspace_path / subfolder
    else:
        path_to_list = workspace_path
    
    result = []
    
    for item in path_to_list.glob("**/*"):
        if item.is_file():
            result.append({
                "name": item.name,
                "path": str(item.relative_to(workspace_path)),
                "full_path": str(item),
                "size": item.stat().st_size,
                "modified": time.ctime(item.stat().st_mtime)
            })
    
    return result

def delete_file(group_chat_name: str, file_name: str, 
                subfolder: str = "code") -> bool:
    """
    Delete a file from the group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        file_name: Name of the file
        subfolder: Subfolder within the workspace (default: code)
        
    Returns:
        True if the file was deleted, False otherwise
    """
    workspace_path = get_workspace_path(group_chat_name)
    file_path = workspace_path / subfolder / file_name
    
    if not file_path.exists():
        return False
    
    os.remove(file_path)
    return True

def get_workspace_info(group_chat_name: str) -> Dict[str, Any]:
    """
    Get information about a group chat's workspace.
    
    Args:
        group_chat_name: Name of the group chat
        
    Returns:
        Dictionary containing workspace information
    """
    workspace_path = get_workspace_path(group_chat_name)
    
    # Count files by type
    code_files = list(workspace_path.glob("code/*"))
    data_files = list(workspace_path.glob("data/*"))
    output_files = list(workspace_path.glob("output/*"))
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in workspace_path.glob("**/*") if f.is_file())
    
    return {
        "path": str(workspace_path),
        "code_files": len(code_files),
        "data_files": len(data_files),
        "output_files": len(output_files),
        "total_files": len(code_files) + len(data_files) + len(output_files),
        "total_size": total_size
    }

# Initialize workspaces directory
ensure_workspace_dir()
