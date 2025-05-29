import json
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# Define the path for storing conversations
CONVERSATIONS_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "conversations"

# Create the directory if it doesn't exist
CONVERSATIONS_DIR.mkdir(exist_ok=True)

def get_conversation_filename(group_chat_name: str, timestamp: Optional[str] = None) -> Path:
    """
    Generate a filename for a conversation based on the group chat name and timestamp.
    
    Args:
        group_chat_name: Name of the group chat
        timestamp: Optional timestamp string, will use current time if not provided
        
    Returns:
        Path object for the conversation file
    """
    # Clean group chat name to make it suitable for a filename
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in group_chat_name)
    safe_name = safe_name.replace(" ", "_")
    
    # Use provided timestamp or generate a new one
    if not timestamp:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
    return CONVERSATIONS_DIR / f"{safe_name}_{timestamp}.json"

def save_conversation(group_chat_name: str, chat_history: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Save a conversation to a JSON file.
    
    Args:
        group_chat_name: Name of the group chat
        chat_history: List of chat messages
        metadata: Optional additional information about the conversation
        
    Returns:
        Path to the saved conversation file
    """
    # Skip saving if chat history is empty
    if not chat_history:
        return ""
        
    # Generate a timestamp for the filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_path = get_conversation_filename(group_chat_name, timestamp)
    
    # Prepare the data to save
    conversation_data = {
        "group_chat_name": group_chat_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "messages": chat_history
    }
    
    # Add metadata if provided
    if metadata:
        conversation_data["metadata"] = metadata
    
    # Save to file
    with open(file_path, "w") as f:
        json.dump(conversation_data, f, indent=2)
        
    return str(file_path)

def load_conversation(file_path: str) -> Dict[str, Any]:
    """
    Load a conversation from a JSON file.
    
    Args:
        file_path: Path to the conversation file
        
    Returns:
        Dictionary containing the conversation data
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading conversation from {file_path}: {str(e)}")
        return {"messages": [], "error": str(e)}

def list_conversations(group_chat_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all saved conversations, optionally filtered by group chat name.
    
    Args:
        group_chat_name: Optional name of the group chat to filter by
        
    Returns:
        List of dictionaries with conversation metadata
    """
    conversations = []
    
    # Get all JSON files in the conversations directory
    for file_path in CONVERSATIONS_DIR.glob("*.json"):
        try:
            # Load the conversation data
            with open(file_path, "r") as f:
                data = json.load(f)
                
            # Filter by group chat name if provided
            if group_chat_name and data.get("group_chat_name") != group_chat_name:
                continue
                
            # Add metadata about the conversation
            conversation_info = {
                "file_path": str(file_path),
                "filename": file_path.name,
                "group_chat_name": data.get("group_chat_name", "Unknown"),
                "timestamp": data.get("timestamp", "Unknown"),
                "message_count": len(data.get("messages", [])),
            }
            
            conversations.append(conversation_info)
        except Exception as e:
            print(f"Error loading conversation metadata from {file_path}: {str(e)}")
    
    # Sort by timestamp (newest first)
    return sorted(conversations, key=lambda x: x["timestamp"], reverse=True)
