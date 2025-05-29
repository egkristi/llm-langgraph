from typing import Dict, List, Any, Optional
import json
from pathlib import Path
import time

class ConversationMemory:
    """Manages conversation history and persistence for agents."""
    
    def __init__(self, max_history: int = 100):
        """
        Initialize the conversation memory.
        
        Args:
            max_history: Maximum number of messages to keep in history
        """
        self.max_history = max_history
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.save_directory = Path("conversations")
        
        # Create save directory if it doesn't exist
        self.save_directory.mkdir(exist_ok=True, parents=True)
    
    def add_message(self, conversation_id: str, message: Dict[str, Any]):
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            message: Message to add, should be a dict with at least 'role' and 'content'
        """
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
            
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = time.time()
            
        self.conversations[conversation_id].append(message)
        
        # Trim if needed
        if len(self.conversations[conversation_id]) > self.max_history:
            self.conversations[conversation_id] = self.conversations[conversation_id][-self.max_history:]
    
    def get_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List of messages in the conversation
        """
        return self.conversations.get(conversation_id, [])
    
    def clear_conversation(self, conversation_id: str):
        """
        Clear a conversation's history.
        
        Args:
            conversation_id: ID of the conversation to clear
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id] = []
    
    def save_conversation(self, conversation_id: str, filename: Optional[str] = None):
        """
        Save a conversation to a file.
        
        Args:
            conversation_id: ID of the conversation to save
            filename: Optional filename, will use conversation_id if not provided
        """
        if conversation_id not in self.conversations:
            return
            
        filename = filename or f"{conversation_id}.json"
        file_path = self.save_directory / filename
        
        with open(file_path, "w") as f:
            json.dump(self.conversations[conversation_id], f, indent=2)
    
    def load_conversation(self, filename: str) -> str:
        """
        Load a conversation from a file.
        
        Args:
            filename: Name of the file to load
            
        Returns:
            The conversation ID
        """
        file_path = self.save_directory / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Conversation file {filename} not found")
            
        with open(file_path, "r") as f:
            conversation = json.load(f)
            
        # Use filename without extension as conversation ID
        conversation_id = Path(filename).stem
        self.conversations[conversation_id] = conversation
        
        return conversation_id
    
    def list_saved_conversations(self) -> List[str]:
        """
        List all saved conversations.
        
        Returns:
            List of filenames for saved conversations
        """
        return [f.name for f in self.save_directory.glob("*.json")]
