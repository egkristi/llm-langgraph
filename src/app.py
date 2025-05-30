import streamlit as st
import ollama
from pathlib import Path
import json
import time
import os
import subprocess
from typing import Dict, List, Optional, Any

from agents.agent_factory import create_agent
from models.model_manager import ModelManager
from graph.group_chat import create_group_chat
from memory.conversation_memory import ConversationMemory
from tools.docker_code_runner import docker_available
from utils.config import (
    load_config, save_config, 
    load_agents, save_agents,
    load_groupchats, save_groupchats
)
from utils.conversation_manager import (
    save_conversation, load_conversation,
    list_conversations, get_conversation_filename
)
from utils.workspace_manager import (
    get_workspace_path, list_files, read_file, get_workspace_info
)

# Helper function for auto-saving configuration
def _save_current_configuration():
    """Automatically save the current application state to configuration files."""
    try:
        # Save main configuration (without agents and group chats)
        config = {
            "default_model": st.session_state.model_manager.default_model if "model_manager" in st.session_state else "",
            "ollama_host": "http://localhost:11434",  # Default value
            "debug_mode": st.session_state.get("debug_mode", False),
            "active_group_chat": st.session_state.get("active_group_chat", None)
        }
        save_config(config)
        
        # Save current agents to agents.json
        if "agents" in st.session_state:
            agents_data = {name: agent.to_dict() for name, agent in st.session_state.agents.items()}
            save_agents(agents_data)
        
        # Save current group chats to groupchats.json
        if "saved_group_chats" in st.session_state:
            # Also save to the combined file for backward compatibility
            save_groupchats(st.session_state.saved_group_chats)
            
            # Keep the active group chat in the main config for quick reference
            active_chat = st.session_state.get("active_group_chat")
            if active_chat and active_chat in st.session_state.saved_group_chats:
                st.session_state.saved_group_chats[active_chat]["active"] = True
        
        return True
    except Exception as e:
        print(f"Error auto-saving configuration: {str(e)}")
        return False

# Initialize session state variables
if "agents" not in st.session_state:
    st.session_state.agents = {}
if "group_chat" not in st.session_state:
    st.session_state.group_chat = None
if "active_group_chat" not in st.session_state:
    st.session_state.active_group_chat = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False
if "model_manager" not in st.session_state:
    st.session_state.model_manager = ModelManager()
if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()
if "config" not in st.session_state:
    st.session_state.config = load_config()
if "ollama_connected" not in st.session_state:
    st.session_state.ollama_connected = False
if "available_models" not in st.session_state:
    st.session_state.available_models = []
if "saved_group_chats" not in st.session_state:
    st.session_state.saved_group_chats = {}
if "all_saved_agents" not in st.session_state:
    st.session_state.all_saved_agents = {}
if "all_saved_group_chats" not in st.session_state:
    st.session_state.all_saved_group_chats = {}

# Function to directly create and activate a group chat
def activate_specific_group_chat(chat_name, chat_config):
    """Directly create and activate a specific group chat."""
    try:
        # Check if all required agents exist
        missing_agents = [name for name in chat_config["agent_names"] if name not in st.session_state.agents]
        
        # Print debug information
        print(f"Activating group chat: {chat_name}")
        print(f"Chat config: {chat_config}")
        print(f"Missing agents: {missing_agents}")
        print(f"Available agents: {list(st.session_state.agents.keys())}")
        
        # Only activate if all agents are available
        if not missing_agents:
            # Create the group chat
            selected_agents = {name: st.session_state.agents[name] for name in chat_config["agent_names"]}
            st.session_state.group_chat = create_group_chat(
                selected_agents,
                require_consensus=chat_config["require_consensus"],
                max_rounds=chat_config["max_rounds"],
                group_chat_name=chat_name
            )
            st.session_state.active_group_chat = chat_name
            print(f"Successfully activated group chat: {chat_name}")
            return True
        else:
            print(f"Cannot activate group chat: missing agents {missing_agents}")
            return False
    except Exception as e:
        print(f"Error activating group chat {chat_name}: {str(e)}")
        return False

# Auto-load saved configurations from all JSON files
try:
    # Load main config
    config = st.session_state.config
    
    # Debug: Print the content of the config file
    print("\n\nDEBUG: Config file contents:")
    print(json.dumps(config, indent=2))
    print("\n")
    
    # Set debug mode and default model
    st.session_state.debug_mode = config.get("debug_mode", False)
    default_model = config.get("default_model", "")
    if default_model:
        st.session_state.model_manager.set_default_model(default_model)
    
    # Load saved agents from both sources
    
    # 1. First, load agents from the separate agents.json file
    all_agents = load_agents()
    st.session_state.all_saved_agents = all_agents.copy()
    
    # 2. Also load agents from the main config.json for backward compatibility
    if "agents" in config:
        # Merge with agents from config.json for backward compatibility
        for name, agent_data in config.get("agents", {}).items():
            if name not in st.session_state.all_saved_agents:
                st.session_state.all_saved_agents[name] = agent_data
    
    # Create agent instances that don't already exist
    for name, agent_data in st.session_state.all_saved_agents.items():
        if name not in st.session_state.agents:
            try:
                if st.session_state.debug_mode:
                    print(f"Creating agent {name} with data: {agent_data}")
                
                # Ensure we have the required fields
                if "agent_type" not in agent_data or "model" not in agent_data:
                    print(f"Warning: Missing required fields for agent {name}. Agent data: {agent_data}")
                    continue
                    
                agent = create_agent(
                    name=name,
                    agent_type=agent_data["agent_type"],
                    model=agent_data["model"],
                    custom_prompt=agent_data.get("custom_prompt")
                )
                st.session_state.agents[name] = agent
                if st.session_state.debug_mode:
                    print(f"Successfully created agent {name}")
            except Exception as agent_err:
                print(f"Error creating agent {name}: {str(agent_err)}")
    
    # Load saved group chats from both sources
    
    # 1. First load from the separate groupchats.json file
    all_group_chats = load_groupchats()
    st.session_state.all_saved_group_chats = all_group_chats.copy()
    
    # 2. Also load from the main config.json for backward compatibility
    if "saved_group_chats" in config:
        # Look for active group chat
        for name, chat_data in config.get("saved_group_chats", {}).items():
            # Add to collections
            if name not in st.session_state.all_saved_group_chats:
                st.session_state.all_saved_group_chats[name] = chat_data.copy()
                st.session_state.saved_group_chats[name] = chat_data.copy()
                
                # Debug
                print(f"Loaded group chat from config.json: {name}")
                
            # Check for active flag
            if chat_data.get("active", False):
                # Set this as the active group chat name
                config["active_group_chat"] = name
                print(f"Found active group chat in config.json: {name}")
    
    # DIRECT FIX: Handle 'My Group Chat' specifically if it exists
    if "saved_group_chats" in config and "My Group Chat" in config["saved_group_chats"]:
        chat_name = "My Group Chat"
        config["active_group_chat"] = chat_name
        
        # Make sure it's in both collections
        if chat_name not in st.session_state.saved_group_chats and chat_name in config["saved_group_chats"]:
            st.session_state.saved_group_chats[chat_name] = config["saved_group_chats"][chat_name].copy()
            
        if chat_name not in st.session_state.all_saved_group_chats and chat_name in config["saved_group_chats"]:
            st.session_state.all_saved_group_chats[chat_name] = config["saved_group_chats"][chat_name].copy()
            
        print(f"Direct fix: Set 'My Group Chat' as the active group chat")
    
    
    # Update current group chats (these are the ones shown in the UI)
    st.session_state.saved_group_chats = st.session_state.all_saved_group_chats.copy()
    
    # First check if there's already an active chat in the session state
    if st.session_state.group_chat is None:
        # Check for active group chat in the saved configurations
        active_chat_name = None
        
        # Print debug info
        if st.session_state.debug_mode:
            print(f"Available agents: {list(st.session_state.agents.keys())}")
            print(f"Available group chats: {list(st.session_state.saved_group_chats.keys())}")
        
        # First priority: check main config for active group chat - direct reference
        active_chat_name = config.get("active_group_chat")
        
        # Second priority: group chat marked as active in saved configs
        if not active_chat_name:
            for chat_name, chat_config in st.session_state.saved_group_chats.items():
                if chat_config.get("active", False):
                    active_chat_name = chat_name
                    break
        
        # Third priority: use the most recently created group chat
        if not active_chat_name and st.session_state.saved_group_chats:
            # Find the most recently created group chat
            most_recent = None
            most_recent_time = None
            
            for chat_name, chat_config in st.session_state.saved_group_chats.items():
                if "created_at" in chat_config:
                    if most_recent_time is None or chat_config["created_at"] > most_recent_time:
                        most_recent = chat_name
                        most_recent_time = chat_config["created_at"]
            
            if most_recent:
                active_chat_name = most_recent
                # Mark this chat as active
                st.session_state.saved_group_chats[active_chat_name]["active"] = True
                
        # If an active chat is found, try to initialize it
        if active_chat_name:
            # Try to get the chat config from any available source
            chat_config = None
            
            if active_chat_name in st.session_state.saved_group_chats:
                chat_config = st.session_state.saved_group_chats[active_chat_name]
            elif "saved_group_chats" in config and active_chat_name in config["saved_group_chats"]:
                chat_config = config["saved_group_chats"][active_chat_name]
                # Also add to current session's group chats for consistency
                st.session_state.saved_group_chats[active_chat_name] = chat_config.copy()
                
            if st.session_state.debug_mode:
                print(f"Attempting to activate chat: {active_chat_name}")
                print(f"Chat config: {chat_config}")
                
            if not chat_config:
                print(f"Warning: Could not find configuration for group chat '{active_chat_name}'")
                # Skip the rest of this block
                continue_activation = False
            else:
                continue_activation = True
            
            # Only proceed if we have a valid chat config
            if continue_activation:
                # Check if all required agents exist
                missing_agents = [name for name in chat_config["agent_names"] if name not in st.session_state.agents]
                
                if st.session_state.debug_mode:
                    print(f"Missing agents for chat '{active_chat_name}': {missing_agents}")
                    print(f"Available agents: {list(st.session_state.agents.keys())}")
                
                # Only activate if all agents are available
                if not missing_agents:
                    try:
                        # Create the group chat
                        selected_agents = {name: st.session_state.agents[name] for name in chat_config["agent_names"]}
                        st.session_state.group_chat = create_group_chat(
                            selected_agents,
                            require_consensus=chat_config.get("require_consensus", False),
                            max_rounds=chat_config.get("max_rounds", 3),
                            group_chat_name=active_chat_name
                        )
                        st.session_state.active_group_chat = active_chat_name
                        print(f"Auto-activated group chat: {active_chat_name}")
                    except Exception as gc_err:
                        print(f"Error auto-activating group chat {active_chat_name}: {str(gc_err)}")
    else:
        print(f"Using existing group chat from session state: {st.session_state.active_group_chat}")

    # Directly try to activate the group chat from config.json
    if st.session_state.group_chat is None and "saved_group_chats" in config:
        # List all available group chats
        print(f"Available group chats in config.json: {list(config.get('saved_group_chats', {}).keys())}")
        
        # Find the active group chat or the first one
        chat_name = None
        
        # First check for a chat explicitly marked as active
        for name, chat_data in config.get("saved_group_chats", {}).items():
            if chat_data.get("active", False):
                chat_name = name
                break
        
        # If no active chat found, try "My Group Chat" specifically
        if not chat_name and "My Group Chat" in config.get("saved_group_chats", {}):
            chat_name = "My Group Chat"
        
        # If still no chat found, use the first one
        if not chat_name and config.get("saved_group_chats", {}):
            chat_name = list(config.get("saved_group_chats", {}).keys())[0]
        
        if not chat_name:
            print("No group chats found in config.json")
            # Skip the rest of the activation attempt
            continue_with_activation = False
        else:
            continue_with_activation = True
            
        if continue_with_activation:
            print(f"Selected group chat to activate: {chat_name}")
            chat_config = config["saved_group_chats"][chat_name]
            print(f"\n\nDIRECT ACTIVATION ATTEMPT for '{chat_name}'")
            
            # Ensure agents in the group chat exist
            if "agents" in config:
                # Extract agent names from group chat
                chat_agents = chat_config.get("agent_names", [])
                print(f"Chat agent names: {chat_agents}")
                
                # Check each agent and create if missing
                for agent_name in chat_agents:
                    if agent_name not in st.session_state.agents and agent_name in config["agents"]:
                        print(f"Creating missing agent {agent_name} from config.json")
                        agent_data = config["agents"][agent_name]
                        try:
                            agent = create_agent(
                                name=agent_name,
                                agent_type=agent_data["agent_type"],
                                model=agent_data["model"],
                                custom_prompt=agent_data.get("custom_prompt")
                            )
                            st.session_state.agents[agent_name] = agent
                            print(f"Successfully created agent {agent_name} for the group chat")
                        except Exception as e:
                            print(f"Failed to create agent {agent_name}: {str(e)}")
        
            # Try to activate the group chat directly
            success = activate_specific_group_chat(chat_name, chat_config)
            if success:
                # Mark this chat as active in the configuration
                if chat_name in st.session_state.saved_group_chats:
                    st.session_state.saved_group_chats[chat_name]["active"] = True
                    
                # Also mark it as active in the main config
                config["active_group_chat"] = chat_name
                
                # Save the updated configuration
                _save_current_configuration()
                print("Successfully activated and saved the group chat configuration.")
                
                # Force a rerun to ensure the UI updates
                st.rerun()

    # If no group chat is activated, try to create a default one with available agents
    if st.session_state.group_chat is None and st.session_state.agents:
        print("\n\nCreating a default group chat with available agents...")
        available_agents = list(st.session_state.agents.keys())
        if len(available_agents) > 0:
            # Create a new group chat configuration
            default_chat_name = "Default Group Chat"
            default_chat_config = {
                "agent_names": available_agents,
                "require_consensus": True,
                "max_rounds": 5,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "active": True
            }
            
            # Add to collections
            st.session_state.saved_group_chats[default_chat_name] = default_chat_config
            st.session_state.all_saved_group_chats[default_chat_name] = default_chat_config
            
            # Activate the group chat
            success = activate_specific_group_chat(default_chat_name, default_chat_config)
            if success:
                print(f"Successfully created and activated default group chat with agents: {available_agents}")
                _save_current_configuration()

except Exception as e:
    print(f"Error auto-loading configuration: {str(e)}")
    if st.session_state.debug_mode:
        import traceback
        traceback.print_exc()

# Page title
st.title("Multi-Agent LLM Chat")

# Function to connect to Ollama and list models
def connect_to_ollama(host="http://localhost:11434"):
    try:
        # Set the Ollama host globally
        ollama.BASE_URL = host
        st.session_state.model_manager.set_ollama_host(host)
        models = ollama.list()
        # Inspect the response for debugging if needed
        if st.session_state.debug_mode:
            print(f"Ollama response: {models}")
            
        # Extract model names from Ollama response
        extracted_models = []
        if hasattr(models, 'models') and isinstance(models.models, list):
            for model in models.models:
                if hasattr(model, 'model'):
                    # Extract model name (removing ':latest' if present)
                    model_name = model.model.split(':')[0] if ':' in model.model else model.model
                    extracted_models.append(model_name)
                else:
                    # Fallback if structure is unexpected
                    extracted_models.append(str(model))
        
        if extracted_models:
            st.session_state.available_models = extracted_models
            st.session_state.ollama_connected = True
            return True, f"Connected to Ollama. Found {len(extracted_models)} models."
        else:
            # Alternative parsing method for different response formats
            try:
                # Try direct access to models attribute
                if hasattr(models, 'models'):
                    models_list = getattr(models, 'models')
                    if isinstance(models_list, list):
                        extracted_models = []
                        for model in models_list:
                            # Try different attribute names that might contain the model name
                            for attr in ['model', 'name', 'id']:
                                if hasattr(model, attr):
                                    model_name = getattr(model, attr)
                                    # Remove version tag if present
                                    if isinstance(model_name, str) and ':' in model_name:
                                        model_name = model_name.split(':')[0]
                                    extracted_models.append(model_name)
                                    break
                            else:
                                # If no known attributes found, use the string representation
                                extracted_models.append(str(model))
                        
                        if extracted_models:
                            st.session_state.available_models = extracted_models
                            st.session_state.ollama_connected = True
                            return True, f"Connected to Ollama. Found {len(extracted_models)} models."
                
                # Try dictionary format as a fallback
                if isinstance(models, dict):
                    if 'models' in models and isinstance(models['models'], list):
                        model_list = models['models']
                        extracted_models = []
                        for model in model_list:
                            if isinstance(model, dict):
                                # Look for common name fields
                                for field in ['model', 'name', 'id']:
                                    if field in model:
                                        model_name = model[field]
                                        if isinstance(model_name, str) and ':' in model_name:
                                            model_name = model_name.split(':')[0]
                                        extracted_models.append(model_name)
                                        break
                        
                        if extracted_models:
                            st.session_state.available_models = extracted_models
                            st.session_state.ollama_connected = True
                            return True, f"Connected to Ollama. Found {len(extracted_models)} models."
            except Exception as e:
                if st.session_state.debug_mode:
                    print(f"Error in alternative parsing: {str(e)}")
                # Continue to the next fallback method
            
            return False, "Could not find any models in the Ollama response."
    except Exception as e:
        return False, f"Failed to connect to Ollama: {str(e)}"

# Auto-connect to Ollama on app start if not already connected
if not st.session_state.ollama_connected:
    with st.spinner("Connecting to Ollama..."):
        success, message = connect_to_ollama()
        if success:
            st.success(message)
        else:
            st.warning(f"{message} Click 'Connect to Ollama' to retry.")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # Ollama configuration
    st.subheader("Ollama Settings")
    # Connection status
    if st.session_state.ollama_connected:
        st.success("✓ Connected to Ollama")
    else:
        st.error("✗ Not connected to Ollama")
    ollama_host = st.text_input("Ollama Host", value="http://localhost:11434")
    
    # Connect to Ollama button
    if st.button("Connect to Ollama"):
        with st.spinner("Connecting to Ollama..."):
            try:
                # Initialize model manager
                model_manager = ModelManager()
                st.session_state.model_manager = model_manager
                
                # Try to get available models
                models = model_manager.list_available_models()
                st.session_state.models = models
                
                # Get all models from models.json
                all_models = model_manager.get_all_models()
                st.session_state.all_models = all_models
                
                st.success(f"Connected to Ollama. Found {len(models)} models.")
            except Exception as e:
                st.error(f"Error connecting to Ollama: {str(e)}")
                if st.session_state.debug_mode:
                    st.exception(e)
                    st.write("Try running 'ollama serve' in a terminal to start Ollama")

    # Custom Model Installation section was moved to the Model Management expander

    # Debug mode toggle
    st.subheader("Advanced Settings")
    debug_mode = st.checkbox("Enable Debug Mode", value=st.session_state.debug_mode, 
                           help="Display verbose debugging information in the UI")
    
    # Update session state when checkbox changes
    if debug_mode != st.session_state.debug_mode:
        st.session_state.debug_mode = debug_mode
        # Save the debug mode setting to config
        config = st.session_state.config
        config["debug_mode"] = debug_mode
        save_config(config)
        st.toast(f"Debug mode {'enabled' if debug_mode else 'disabled'}")
        # Force a rerun to update the UI
        st.rerun()

    # Workspace file browser (collapsed by default)
    with st.expander("Workspace Files", expanded=False):
        # Get current group chat name
        current_group_chat = st.session_state.get("active_group_chat", "Default Group Chat")
        
        # Dropdown to select group chat workspace
        available_group_chats = list(st.session_state.get("all_saved_group_chats", {}).keys())
        selected_workspace = st.selectbox(
            "Select Workspace", 
            options=available_group_chats,
            index=available_group_chats.index(current_group_chat) if current_group_chat in available_group_chats else 0
        )
        
        # Dropdown to select folder
        folder_options = ["code", "data", "output"]
        selected_folder = st.selectbox("Select Folder", options=folder_options)
        
        # Get workspace files
        try:
            workspace_path = get_workspace_path(selected_workspace)
            files = list_files(selected_workspace, selected_folder)
            
            if files:
                st.write(f"**Files in {selected_folder}/**")
                
                # Create a container for the file list
                file_container = st.container()
                
                with file_container:
                    for file in files:
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"{file['name']} ({file['size']} bytes)")
                        
                        with col2:
                            # Create a download button for each file
                            file_content = read_file(selected_workspace, file['name'], selected_folder)
                            if file_content is not None:
                                st.download_button(
                                    label="📥",
                                    data=file_content,
                                    file_name=file['name'],
                                    mime="text/plain",
                                    key=f"download_{file['name']}"
                                )
            else:
                st.info(f"No files in {selected_folder}/ folder")
                
            # Show workspace information
            workspace_info = get_workspace_info(selected_workspace)
            st.write("**Workspace Summary:**")
            st.write(f"Total files: {workspace_info['total_files']}")
            st.write(f"Size: {workspace_info['total_size']} bytes")
            
        except Exception as e:
            st.error(f"Error loading workspace files: {str(e)}")
            if st.session_state.debug_mode:
                st.exception(e)


    
    # Model management section (collapsed by default)
    with st.expander("Model Management", expanded=False):
        if "model_manager" in st.session_state:
            # Get all models
            if "all_models" not in st.session_state:
                all_models = st.session_state.model_manager.get_all_models()
                st.session_state.all_models = all_models
            else:
                all_models = st.session_state.all_models
            
            installed_models = all_models["installed"]
            recommended_models = all_models["recommended"]
            
            st.write("**Installed Models:**")
            if installed_models:
                for model in installed_models:
                    st.write(f"- {model}")
            else:
                st.info("No models installed. Please connect to Ollama first.")
            
            # Add Pull Custom Model section
            st.divider()
            st.write("**Pull Custom Model:**")
            custom_model = st.text_input("Model Name", placeholder="e.g., llama3:latest, phi3:instruct")
            description = st.text_area("Description (optional)", placeholder="Describe the model's capabilities", height=100)
            
            # Pull model button
            if st.button("Pull Model"):
                if not custom_model:
                    st.error("Please enter a model name")
                else:
                    with st.spinner(f"Pulling model {custom_model}..."):
                        try:
                            # Add the custom model with simplified metadata
                            success = st.session_state.model_manager.add_custom_model(
                                model_name=custom_model,
                                display_name=None,  # Use model name as display name
                                description=description if description else None,
                                tags=["custom"]  # Always use custom tag
                            )
                            
                            if success:
                                # Refresh models
                                all_models = st.session_state.model_manager.get_all_models()
                                st.session_state.all_models = all_models
                                st.success(f"Successfully pulled model {custom_model}")
                                st.rerun()  # Refresh the UI to show the new model
                            else:
                                st.error(f"Failed to pull model {custom_model}")
                        except Exception as e:
                            st.error(f"Error pulling model: {str(e)}")
                            if st.session_state.debug_mode:
                                st.exception(e)
            
            st.divider()
            st.write("**Recommended Models:**")
            
            # Create a container for the model list
            model_container = st.container()
            
            with model_container:
                for model_entry in recommended_models:
                    # Extract model details
                    if isinstance(model_entry, dict):
                        model_name = model_entry.get("name", "")
                        display_name = model_entry.get("display_name", model_name)
                        description = model_entry.get("description", "")
                    else:
                        model_name = model_entry
                        display_name = model_name
                        description = ""
                    
                    # Check if model is installed
                    is_installed = model_name in installed_models
                    
                    # Create a row for each model
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        if is_installed:
                            st.write(f"**{display_name}** ✓")
                        else:
                            st.write(f"**{display_name}**")
                        
                        if description:
                            st.write(f"*{description}*")
                    
                    with col2:
                        # Add pull button for models not yet installed
                        if not is_installed:
                            if st.button(f"Pull", key=f"pull_{model_name}"):
                                with st.spinner(f"Pulling {model_name}..."):
                                    success = st.session_state.model_manager.pull_model(model_name)
                                    if success:
                                        st.success(f"Successfully pulled {model_name}")
                                        # Update installed models
                                        all_models = st.session_state.model_manager.get_all_models()
                                        st.session_state.all_models = all_models
                                        st.session_state.models = all_models["installed"]
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to pull {model_name}")
        else:
            st.info("Please connect to Ollama first to manage models.")
            if st.button("Connect"):
                st.rerun()



# Make Agent Configuration collapsible and collapsed by default
with st.expander("Agent Configuration", expanded=False):
    # Create new agent
    col1, col2 = st.columns(2)
    with col1:
        new_agent_name = st.text_input("Agent Name")
    with col2:
        agent_types = ["Assistant", "Researcher", "Coder", "Math Expert", "Critic", "Manager", "Code Runner", "Custom"]
        new_agent_type = st.selectbox("Agent Type", agent_types)
    
    # Model selection for agent
    if "available_models" in st.session_state:
        agent_model = st.selectbox("Agent Model", st.session_state.available_models, key="new_agent_model")
    else:
        agent_model = st.text_input("Agent Model (Ollama not connected)")
    
    # Custom prompt for custom agent type
    if new_agent_type == "Custom":
        custom_prompt = st.text_area("Custom Agent Prompt", height=150)
    else:
        custom_prompt = None
    
    # Create agent button
    if st.button("Create Agent"):
        if new_agent_name and new_agent_name not in st.session_state.agents:
            # Check for Docker availability if creating a Code Runner agent
            if new_agent_type == "Code Runner" and not docker_available():
                st.error("Docker is not available. Please ensure Docker is installed and running before creating a Code Runner agent.")
                st.info("The Code Runner agent requires Docker to execute code safely in isolated containers.")
            else:
                with st.spinner(f"Creating agent {new_agent_name}..."):
                    try:
                        agent = create_agent(
                            name=new_agent_name,
                            agent_type=new_agent_type,
                            model=agent_model,
                            custom_prompt=custom_prompt
                        )
                        st.session_state.agents[new_agent_name] = agent
                        
                        # Auto-save configuration when an agent is created
                        _save_current_configuration()
                        
                        st.success(f"Agent {new_agent_name} created successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating agent: {str(e)}")
                        if st.session_state.debug_mode:
                            st.exception(e)
    
    # Display created agents
    if st.session_state.agents:
        st.subheader("Created Agents")
        
        # Use columns for better layout
        agent_cols = st.columns(3)
        for i, (agent_name, agent) in enumerate(st.session_state.agents.items()):
            with agent_cols[i % 3]:
                st.write(f"**{agent_name}**")
                st.write(f"Type: {agent.agent_type}")
                st.write(f"Model: {agent.model}")
                
                # Delete button for each agent
                if st.button(f"Delete {agent_name}"):
                    del st.session_state.agents[agent_name]
                    st.rerun()

# Make Group Chat Management collapsible and collapsed by default
with st.expander("Group Chat Management", expanded=False):
    # Create New Group Chat tab and Saved Group Chat tab
    tab1, tab2, tab3, tab4 = st.tabs(["Create New Group Chat", "Use Saved Group Chat", "Manage Configurations", "Conversations"])

# Tab 1: Create New Group Chat
with tab1:
    if st.session_state.agents:
        # Custom name for the group chat configuration
        group_chat_name = st.text_input("Group Chat Name", value="My Group Chat", 
                                      help="Give your group chat configuration a descriptive name")
        
        # Select agents for the group chat
        group_chat_agents = st.multiselect(
            "Select Agents for Group Chat",
            options=list(st.session_state.agents.keys())
        )
        
        # Advanced configuration section with a divider and subheader
        st.divider()
        st.subheader("Advanced Configuration")
        
        # Consensus and rounds options
        col1, col2 = st.columns(2)
        with col1:
            require_consensus = st.checkbox("Require Consensus", value=True, 
                                          help="When enabled, agents will discuss until consensus is reached or max rounds is hit")
        with col2:
            max_rounds = st.slider("Maximum Discussion Rounds", min_value=1, max_value=99, value=5,
                                  help="Maximum number of back-and-forth rounds before concluding")
        
        # Explain how consensus works
        if require_consensus:
            st.info("🤝 **Consensus Mode:** Agents will have multiple rounds of discussion. A Manager agent will "
                   "evaluate when consensus is reached. If no Manager agent exists, a Critic or another agent "
                   "will serve as the discussion manager.")
        
        # Setup group chat
        col1, col2 = st.columns(2)
        # Single button with checkbox for activation
        activate_after_setup = st.checkbox("Activate immediately after setup", value=True, 
                                 help="When checked, the group chat will be activated after setup")
        setup_button = st.button("Setup Group Chat", type="primary")
        
        if setup_button and group_chat_agents:
            if not group_chat_name or group_chat_name.strip() == "":
                st.error("Please provide a name for your group chat configuration")
            else:
                with st.spinner("Setting up group chat..."):
                    # Store the group chat configuration
                    if "saved_group_chats" not in st.session_state:
                        st.session_state.saved_group_chats = {}
                    
                    # Save the configuration
                    st.session_state.saved_group_chats[group_chat_name] = {
                        "agent_names": group_chat_agents,
                        "require_consensus": require_consensus,
                        "max_rounds": max_rounds,
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Auto-save configuration
                    _save_current_configuration()
                    
                    # Create the group chat if requested
                    if activate_after_setup:
                        try:
                            # Enable debug mode temporarily to track the issue
                            previous_debug = st.session_state.debug_mode
                            st.session_state.debug_mode = True
                            
                            # Create a dictionary of agent objects
                            selected_agents = {name: st.session_state.agents[name] for name in group_chat_agents}
                            
                            # Log for debugging
                            print(f"Creating group chat with {len(selected_agents)} agents: {', '.join(selected_agents.keys())}")
                            
                            # Create the group chat
                            group_chat = create_group_chat(
                                selected_agents,
                                require_consensus=require_consensus,
                                max_rounds=max_rounds,
                                group_chat_name=new_chat_name
                            )
                            
                            # Set it in session state
                            st.session_state.group_chat = group_chat
                            
                            # Log for debugging
                            print(f"Group chat created: {type(group_chat).__name__}, ID: {id(group_chat)}")
                            
                            # Verify group chat was created successfully
                            if st.session_state.group_chat is not None:
                                # Show confirmation with details about setup
                                if require_consensus:
                                    manager_type = "Manager" if "Manager" in selected_agents else \
                                                  "Critic" if "Critic" in selected_agents else \
                                                  list(selected_agents.keys())[0]
                                    st.success(f"Group chat '{group_chat_name}' created and activated with consensus required. "
                                              f"Using {manager_type} as discussion manager. Max rounds: {max_rounds}")
                                else:
                                    st.success(f"Group chat '{group_chat_name}' created and activated")
                                
                                # Add group chat info to the saved configuration
                                st.session_state.saved_group_chats[group_chat_name]["active"] = True
                                st.session_state.active_group_chat = group_chat_name
                                _save_current_configuration()
                                
                                # Always show debug info for troubleshooting
                                st.info(f"Debug: Group chat '{group_chat_name}' created and activated successfully. Type: {type(st.session_state.group_chat).__name__}")
                                
                                # Restore original debug setting
                                st.session_state.debug_mode = previous_debug
                                
                                # Force a rerun to refresh the UI state
                                st.rerun()
                            else:
                                st.error("Failed to create group chat object, but no exception was raised.")
                                st.session_state.debug_mode = previous_debug
                        except Exception as e:
                            st.error(f"Error creating group chat: {str(e)}")
                            st.exception(e)
                    else:
                        st.success(f"Group chat configuration '{group_chat_name}' saved successfully")
    else:
        st.info("Create some agents first to set up a group chat")

# Tab 2: Use Saved Group Chat
with tab2:
    if st.session_state.all_saved_group_chats:
        # Display saved chats with nice formatting
        st.subheader("Select a Saved Configuration")
        
        # Use radio buttons with better formatting for selection
        saved_chat_options = list(st.session_state.all_saved_group_chats.keys())
        
        # Add information about source
        def format_chat_name(chat_name):
            if st.session_state.active_group_chat and chat_name == st.session_state.active_group_chat:
                return f"📍 {chat_name} (current)"
            else:
                return f"{chat_name}"
        
        saved_chat = st.radio(
            "Available Group Chat Configurations",
            options=saved_chat_options,
            format_func=format_chat_name
        )
        
        # Show configuration details
        if saved_chat:
            config = st.session_state.all_saved_group_chats[saved_chat]
            st.write("**Configuration Details:**")
            st.write(f"- **Agents:** {', '.join(config['agent_names'])}")
            st.write(f"- **Consensus Required:** {'Yes' if config['require_consensus'] else 'No'}")
            st.write(f"- **Max Discussion Rounds:** {config['max_rounds']}")
            if "created_at" in config:
                st.write(f"- **Created:** {config['created_at']}")
            
            # Check if all required agents exist before enabling activation
            missing_agents = [name for name in config["agent_names"] if name not in st.session_state.agents]
            
            if missing_agents:
                st.warning(f"Missing agents: {', '.join(missing_agents)}")
                # Provide option to auto-create missing agents
                if st.session_state.available_models and st.session_state.ollama_connected:
                    default_model = st.session_state.model_manager.default_model or st.session_state.available_models[0]
                    
                    # Use a container instead of an expander to avoid nesting expanders
                    st.markdown("### 🔧 Auto-create missing agents")
                    st.info("The following agents need to be created to activate this group chat.")
                    
                    # Show the missing agents with their details from the config
                    if "agents" in st.session_state.config:
                        all_agent_configs = st.session_state.config.get("agents", {})
                        for agent_name in missing_agents:
                            if agent_name in all_agent_configs:
                                agent_config = all_agent_configs[agent_name]
                                st.write(f"**{agent_name}** - Type: {agent_config.get('agent_type', 'Unknown')}, Model: {agent_config.get('model', default_model)}")
                            else:
                                st.write(f"**{agent_name}** - No saved configuration found")
                    else:
                        for agent_name in missing_agents:
                            st.write(f"**{agent_name}** - No saved configuration found")
                    
                    if st.button("Create Missing Agents", type="primary"):
                        with st.spinner("Creating missing agents..."):
                            created_agents = []
                            failed_agents = []
                            
                            # Try to create each missing agent
                            for agent_name in missing_agents:
                                try:
                                    # Get agent config if available
                                    agent_config = {}
                                    if "agents" in st.session_state.config:
                                        agent_config = st.session_state.config.get("agents", {}).get(agent_name, {})
                                    
                                    # Use saved config or defaults
                                    agent_type = agent_config.get("agent_type", "Assistant")
                                    model = agent_config.get("model", default_model)
                                    custom_prompt = agent_config.get("custom_prompt")
                                    
                                    # Create the agent
                                    agent = create_agent(
                                        name=agent_name,
                                        agent_type=agent_type,
                                        model=model,
                                        custom_prompt=custom_prompt
                                    )
                                    st.session_state.agents[agent_name] = agent
                                    created_agents.append(agent_name)
                                except Exception as e:
                                    failed_agents.append(agent_name)
                                    print(f"Error creating agent {agent_name}: {str(e)}")
                            
                            # Report results
                            if created_agents:
                                st.success(f"Successfully created {len(created_agents)} agents: {', '.join(created_agents)}")
                            if failed_agents:
                                st.error(f"Failed to create {len(failed_agents)} agents: {', '.join(failed_agents)}")
                                
                            # Save the updated configuration
                            _save_current_configuration()
                            
                            # Refresh to show new state
                            if not failed_agents:
                                st.rerun()
                else:
                    st.error("Cannot create missing agents: Ollama is not connected or no models are available")
            else:
                if st.button("Activate This Group Chat", type="primary"):
                    with st.spinner("Loading group chat..."):
                        # First, update the saved group chats collection if needed
                        if saved_chat not in st.session_state.saved_group_chats:
                            st.session_state.saved_group_chats[saved_chat] = config.copy()
                        
                        # Clear active status for all chats
                        for chat_name in st.session_state.saved_group_chats:
                            if "active" in st.session_state.saved_group_chats[chat_name]:
                                st.session_state.saved_group_chats[chat_name]["active"] = False
                        
                        # Set this chat as active
                        st.session_state.saved_group_chats[saved_chat]["active"] = True
                        st.session_state.active_group_chat = saved_chat
                        
                        # Create group chat instance
                        selected_agents = {name: st.session_state.agents[name] for name in config["agent_names"]}
                        st.session_state.group_chat = create_group_chat(
                            selected_agents,
                            require_consensus=config["require_consensus"],
                            max_rounds=config["max_rounds"],
                            group_chat_name=saved_chat
                        )
                        
                        # Save changes to all files
                        _save_current_configuration()
                        
                        st.success(f"Activated group chat: {saved_chat}")
                        st.rerun()
    else:
        st.info("No saved group chat configurations found. Create one in the 'Create New Group Chat' tab.")

# Tab 3: Manage Configurations
with tab3:
    if st.session_state.all_saved_group_chats:
        st.subheader("Manage Group Chat Configurations")
        
        # Display all saved configurations with management options
        for config_name in list(st.session_state.all_saved_group_chats.keys()):
            config = st.session_state.all_saved_group_chats[config_name]
            
            # Create a container for each configuration
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**{config_name}**")
                    st.write(f"Agents: {', '.join(config['agent_names'][:3])}{'...' if len(config['agent_names']) > 3 else ''}")
                    st.write(f"Consensus: {'Yes' if config['require_consensus'] else 'No'} | Max Rounds: {config['max_rounds']}")
                
                with col2:
                    # Clone and delete buttons
                    btn_col1, btn_col2 = st.columns(2)
                    
                    with btn_col1:
                        if st.button("🔄", key=f"clone_{config_name}", help=f"Clone '{config_name}'"):
                            # Create a copy with a new name
                            new_name = f"{config_name} (Copy)"
                            counter = 1
                            while new_name in st.session_state.all_saved_group_chats:
                                counter += 1
                                new_name = f"{config_name} (Copy {counter})"
                            
                            # Clone the configuration to both collections
                            cloned_config = config.copy()
                            cloned_config["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Add to both collections
                            st.session_state.all_saved_group_chats[new_name] = cloned_config
                            st.session_state.saved_group_chats[new_name] = cloned_config
                            
                            # Save and refresh
                            _save_current_configuration()
                            st.success(f"Cloned '{config_name}' to '{new_name}'")
                            st.rerun()
                    
                    with btn_col2:
                        if st.button("❌", key=f"delete_{config_name}", help=f"Delete '{config_name}'"):
                            # Remove the configuration from both collections
                            if config_name in st.session_state.saved_group_chats:
                                del st.session_state.saved_group_chats[config_name]
                            
                            if config_name in st.session_state.all_saved_group_chats:
                                del st.session_state.all_saved_group_chats[config_name]
                            
                            # Check if this was the active chat
                            if st.session_state.active_group_chat == config_name:
                                st.session_state.active_group_chat = None
                                st.session_state.group_chat = None
                            
                            # Save and refresh
                            _save_current_configuration()
                            st.success(f"Deleted group chat configuration: {config_name}")
                            st.rerun()
                
                # Add a divider between configurations
                st.divider()
    else:
        st.info("No saved group chat configurations found. Create one in the 'Create New Group Chat' tab.")

# Tab 4: Conversations
with tab4:
    st.subheader("Saved Conversations")
    
    # Get list of all saved conversations
    conversations = list_conversations()
    
    if not conversations:
        st.info("No saved conversations found. Start chatting to create some!")
    else:
        # Group conversations by group chat name
        grouped_convos = {}
        for convo in conversations:
            group_name = convo["group_chat_name"]
            if group_name not in grouped_convos:
                grouped_convos[group_name] = []
            grouped_convos[group_name].append(convo)
        
        # Create a selectbox for group chat filtering
        group_chat_names = ["All Group Chats"] + list(grouped_convos.keys())
        selected_group = st.selectbox("Filter by Group Chat", group_chat_names)
        
        # Filter conversations based on selection
        if selected_group == "All Group Chats":
            filtered_convos = conversations
        else:
            filtered_convos = grouped_convos.get(selected_group, [])
        
        # Display the filtered conversations
        if not filtered_convos:
            st.info(f"No conversations found for {selected_group}")
        else:
            st.write(f"Found {len(filtered_convos)} conversation(s)")
            
            # Create a container for the conversations
            for idx, convo in enumerate(filtered_convos):
                # Use a container with a divider instead of an expander
                st.markdown(f"### {convo['group_chat_name']} - {convo['timestamp']}")
                st.write(f"*{convo['message_count']} messages*")
                
                # Use a container for the conversation content
                with st.container():
                    # Load the full conversation
                    full_convo = load_conversation(convo["file_path"])
                    
                    # Display metadata
                    if "metadata" in full_convo:
                        st.write("**Conversation Details:**")
                        for key, value in full_convo["metadata"].items():
                            if key != "group_chat_name":  # Already shown in the header
                                st.write(f"- **{key.replace('_', ' ').title()}:** {value}")
                    
                    # Create a button to load this conversation
                    if st.button(f"Load Conversation", key=f"load_convo_{idx}"):
                        # Clear the current chat history
                        st.session_state.chat_history = full_convo.get("messages", [])
                        st.success(f"Loaded conversation from {convo['timestamp']}")
                        st.rerun()
                    
                    # Show preview of the conversation
                    st.write("**Preview:**")
                    messages = full_convo.get("messages", [])
                    preview_count = min(3, len(messages))
                    
                    for i in range(preview_count):
                        msg = messages[i]
                        if msg["role"] == "user":
                            st.write(f"> **User:** {msg['content'][:100]}..." if len(msg['content']) > 100 else f"> **User:** {msg['content']}")
                        else:
                            agent_name = msg.get("agent", "Assistant")
                            st.write(f"> **{agent_name}:** {msg['content'][:100]}..." if len(msg['content']) > 100 else f"> **{agent_name}:** {msg['content']}")
                    
                    if len(messages) > preview_count:
                        st.write(f"*... and {len(messages) - preview_count} more messages*")

# Chat Interface section follows the Group Chat Management section

# Main chat interface (only shown if group chat is active)
if st.session_state.group_chat and st.session_state.active_group_chat:
    chat_name = st.session_state.active_group_chat
    chat_config = st.session_state.saved_group_chats[chat_name]
    agent_list = chat_config["agent_names"]
    
    st.title(f"Group Chat: {chat_name}")
    
    # Debug information display (only shown in debug mode)
    if st.session_state.debug_mode:
        with st.expander("Debug Information", expanded=True):
            # Group chat configuration
            st.subheader("Group Chat Configuration")
            st.json(chat_config)
            
            # Agent information
            st.subheader("Participating Agents")
            for agent_name in agent_list:
                if agent_name in st.session_state.agents:
                    agent = st.session_state.agents[agent_name]
                    st.markdown(f"**{agent_name}**")
                    st.write(f"Type: {agent.agent_type}, Model: {agent.model}")
                    
                    # Show tools for each agent
                    if hasattr(agent, 'tools') and agent.tools:
                        st.markdown("**Available Tools:**")
                        for tool in agent.tools:
                            st.markdown(f"- {tool.name}: {tool.description}")
            
            # Workspace information
            st.subheader("Workspace Information")
            workspace_info = get_workspace_info(chat_name)
            st.write(f"Workspace Path: {workspace_info['path']}")
            st.write(f"Code Files: {len(workspace_info['code_files'])}")
            st.write(f"Data Files: {len(workspace_info['data_files'])}")
            st.write(f"Output Files: {len(workspace_info['output_files'])}")
            
            # Docker status
            st.subheader("Docker Status")
            docker_status = docker_available()
            st.write(f"Docker Available: {docker_status}")
    
    # Show concise version with max 3 agents and ellipsis if more
    agent_display = ", ".join(agent_list[:3])
    if len(agent_list) > 3:
        agent_display += ", ..."
            
        # Use a clean success message with icon
        st.success(f"🔄 **Active Chat:** {chat_name} with {agent_display}")

# Display chat history
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        # Display assistant messages with agent name in the message
        with st.chat_message("assistant"):
            if "agent" in message:
                st.markdown(f"**{message['agent']}:**")
            st.write(message["content"])

# Chat input
user_input = st.chat_input("Type your message here...")

if user_input and st.session_state.group_chat:
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    # Display user message
    st.chat_message("user").write(user_input)
    
    # Process with group chat
    with st.spinner("Thinking..."):
        start_time = time.time()
        
        # Get response from group chat
        # Create containers to hold conversation by rounds
        round_containers = {}
        max_rounds = st.session_state.group_chat.max_rounds
        for i in range(1, max_rounds + 1):
            round_containers[i] = st.container()
        
        # Create a container for system messages
        system_container = st.container()
        
        # Initialize conversation state if not exists
        if "conversation_state" not in st.session_state:
            st.session_state.conversation_state = {
                "messages": [],
                "current_round": 0,
                "is_thinking": False,
                "displayed_messages": set()  # Track which messages have been displayed
            }
        
        # Setup placeholder for thinking indicator
        thinking_placeholder = st.empty()
        
        try:
            # Show thinking indicator
            with thinking_placeholder:
                if not st.session_state.conversation_state["is_thinking"]:
                    st.session_state.conversation_state["is_thinking"] = True
                    st.info("⏳ Agents are thinking, discussing or executing...")
            
            # Define the callback function to collect messages
            def message_callback(agent_name, message, round_num, is_evaluation=False, is_system=False):
                # Create a unique message ID to track displayed messages
                message_id = f"{agent_name}_{round_num}_{hash(message[:50])}"
                
                # Add message to conversation state
                msg_obj = {
                    "role": "assistant",
                    "agent": agent_name,
                    "content": message,
                    "round": round_num,
                    "is_evaluation": is_evaluation,
                    "is_system": is_system,
                    "id": message_id
                }
                st.session_state.conversation_state["messages"].append(msg_obj)
                
                # Update current round if higher
                if round_num > st.session_state.conversation_state["current_round"]:
                    st.session_state.conversation_state["current_round"] = round_num
                
                # Add to chat history
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "agent": agent_name, 
                    "content": message,
                    "round": round_num
                })
                
                # Display the message immediately if it hasn't been displayed yet
                if message_id not in st.session_state.conversation_state["displayed_messages"]:
                    # Mark as displayed
                    st.session_state.conversation_state["displayed_messages"].add(message_id)
                    
                    # Display system messages in the system container
                    if is_system:
                        with system_container:
                            st.info(message)
                    else:
                        # Display in the appropriate round container
                        with round_containers[round_num]:
                            # Show round header if this is the first message in this round
                            if len([m for m in st.session_state.conversation_state["messages"] 
                                   if m.get("round") == round_num and not m.get("is_system", False)]) == 1:
                                st.markdown(f"### Round {round_num}")
                            
                            # Display the agent message
                            with st.chat_message("assistant"):
                                header = f"**{agent_name}:**"
                                if is_evaluation:
                                    header += " [Evaluation]"
                                st.markdown(header)
                                st.write(message)
            
            # Run the group chat with the callback
            response = st.session_state.group_chat.run(user_input, callback=message_callback)
            
            # Clear thinking indicator
            thinking_placeholder.empty()
            st.session_state.conversation_state["is_thinking"] = False
            
            # Messages have already been displayed in real-time by the callback
            # No need to display them again, but we'll log completion for debugging
            if st.session_state.debug_mode:
                print(f"Conversation complete. {len(st.session_state.conversation_state['messages'])} messages processed.")
                print(f"Messages were displayed in real-time via the callback function.")
            
            # Reset conversation state for next interaction
            st.session_state.conversation_state = {
                "messages": [],
                "current_round": 0,
                "is_thinking": False,
                "displayed_messages": set()  # Reset displayed messages tracking
            }
            
            # Display timing in debug mode
            if st.session_state.debug_mode:
                elapsed_time = time.time() - start_time
                st.info(f"Response generated in {elapsed_time:.2f} seconds")
                
            # Save the conversation to file
            if st.session_state.chat_history:
                # Create metadata about the conversation
                metadata = {
                    "group_chat_name": st.session_state.active_group_chat,
                    "agents": list(st.session_state.agents.keys()),
                    "require_consensus": st.session_state.saved_group_chats[st.session_state.active_group_chat].get("require_consensus", False),
                    "max_rounds": st.session_state.saved_group_chats[st.session_state.active_group_chat].get("max_rounds", 3)
                }
                
                # Save the conversation
                file_path = save_conversation(
                    group_chat_name=st.session_state.active_group_chat,
                    chat_history=st.session_state.chat_history,
                    metadata=metadata
                )
                
                if st.session_state.debug_mode and file_path:
                    print(f"Saved conversation to {file_path}")
                
        except Exception as e:
            st.error(f"Error processing message: {str(e)}")
            if st.session_state.debug_mode:
                st.exception(e)
elif user_input:
    st.warning("Please set up a group chat first")

