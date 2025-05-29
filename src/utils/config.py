import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import time

# Default config files location
CONFIG_FILE = Path("config.json")
AGENTS_FILE = Path("agents.json")
GROUPCHATS_FILE = Path("groupchats.json")

def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the config file, uses default if not specified
        
    Returns:
        Dictionary containing the configuration
    """
    config_path = config_path or CONFIG_FILE
    
    if not config_path.exists():
        return {}
        
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return {}

def save_config(config: Dict[str, Any], config_path: Optional[Path] = None):
    """
    Save configuration to a JSON file.
    
    Args:
        config: Configuration dictionary to save
        config_path: Path to the config file, uses default if not specified
    """
    config_path = config_path or CONFIG_FILE
    
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {str(e)}")


def load_agents(agents_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load agents from a JSON file.
    
    Args:
        agents_path: Path to the agents file, uses default if not specified
        
    Returns:
        Dictionary containing the agents
    """
    agents_path = agents_path or AGENTS_FILE
    
    if not agents_path.exists():
        return {}
        
    try:
        with open(agents_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading agents: {str(e)}")
        return {}


def save_agents(agents: Dict[str, Any], agents_path: Optional[Path] = None):
    """
    Save agents to a JSON file.
    
    Args:
        agents: Agents dictionary to save
        agents_path: Path to the agents file, uses default if not specified
    """
    agents_path = agents_path or AGENTS_FILE
    
    try:
        with open(agents_path, "w") as f:
            json.dump(agents, f, indent=2)
    except Exception as e:
        print(f"Error saving agents: {str(e)}")


def load_groupchats(groupchats_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load group chats from a JSON file.
    
    Args:
        groupchats_path: Path to the group chats file, uses default if not specified
        
    Returns:
        Dictionary containing the group chats
    """
    groupchats_path = groupchats_path or GROUPCHATS_FILE
    
    if not groupchats_path.exists():
        return {}
        
    try:
        with open(groupchats_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading group chats: {str(e)}")
        return {}


def save_groupchats(groupchats: Dict[str, Any], groupchats_path: Optional[Path] = None):
    """
    Save group chats to a JSON file.
    
    Args:
        groupchats: Group chats dictionary to save
        groupchats_path: Path to the group chats file, uses default if not specified
    """
    groupchats_path = groupchats_path or GROUPCHATS_FILE
    
    try:
        with open(groupchats_path, "w") as f:
            json.dump(groupchats, f, indent=2)
    except Exception as e:
        print(f"Error saving group chats: {str(e)}")


def update_config(updates: Dict[str, Any], config_path: Optional[Path] = None):
    """
    Update existing configuration with new values.
    
    Args:
        updates: Dictionary of configuration updates
        config_path: Path to the config file, uses default if not specified
    """
    current_config = load_config(config_path)
    
    # Update recursively
    def update_dict(target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                update_dict(target[key], value)
            else:
                target[key] = value
    
    update_dict(current_config, updates)
    save_config(current_config, config_path)
