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
    load_groupchats, save_groupchats,
    load_agent_types, save_agent_types
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
if "agent_types" not in st.session_state:
    st.session_state.agent_types = load_agent_types()

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
    
    # Agent Types Management section
    with st.expander("Agent Types Management", expanded=False):
        # Load agent types if not already loaded
        if "agent_types" not in st.session_state:
            st.session_state.agent_types = load_agent_types()
        
        # Create tabs for different operations
        agent_types_tab1, agent_types_tab2 = st.tabs(["View/Edit Agent Types", "Add New Agent Type"])
        
        with agent_types_tab1:
            # Display existing agent types for editing
            st.subheader("Edit Existing Agent Types")
            
            # Extract agent types from the configuration
            agent_types_dict = st.session_state.agent_types.get("agent_types", {})
            agent_type_names = list(agent_types_dict.keys())
            
            if agent_type_names:
                # Select an agent type to edit
                selected_agent_type = st.selectbox("Select Agent Type to Edit", agent_type_names)
                
                # Get the selected agent type configuration
                agent_type_config = agent_types_dict.get(selected_agent_type, {})
                
                # Display and allow editing of the agent type fields
                display_name = st.text_input("Display Name", value=agent_type_config.get("display_name", ""))
                description = st.text_area("Description", value=agent_type_config.get("description", ""))
                system_prompt = st.text_area("System Prompt", value=agent_type_config.get("system_prompt", ""), height=300)
                
                # Save changes button
                if st.button("Save Changes"):
                    # Update the agent type configuration
                    agent_types_dict[selected_agent_type] = {
                        "display_name": display_name,
                        "description": description,
                        "system_prompt": system_prompt
                    }
                    
                    # Save the updated agent types configuration
                    st.session_state.agent_types["agent_types"] = agent_types_dict
                    save_agent_types(st.session_state.agent_types)
                    
                    st.success(f"Agent type '{selected_agent_type}' has been updated successfully!")
                    time.sleep(1)  # Give the user time to see the success message
                    st.rerun()  # Refresh the UI
                
                # Delete button with confirmation
                if st.button("Delete Agent Type", type="secondary"):
                    # Ask for confirmation
                    st.warning(f"Are you sure you want to delete the agent type '{selected_agent_type}'? This action cannot be undone.")
                    confirm_delete = st.button(f"Yes, Delete '{selected_agent_type}'", key="confirm_delete")
                    if confirm_delete:
                        # Delete the agent type
                        del agent_types_dict[selected_agent_type]
                        
                        # Save the updated agent types configuration
                        st.session_state.agent_types["agent_types"] = agent_types_dict
                        save_agent_types(st.session_state.agent_types)
                        
                        st.success(f"Agent type '{selected_agent_type}' has been deleted successfully!")
                        time.sleep(1)  # Give the user time to see the success message
                        st.rerun()  # Refresh the UI
            else:
                st.info("No agent types found. Add a new agent type in the 'Add New Agent Type' tab.")
        
        with agent_types_tab2:
            # Form for adding a new agent type
            st.subheader("Add New Agent Type")
            
            # Input fields for the new agent type
            new_agent_type_id = st.text_input("Agent Type ID", placeholder="e.g., DataAnalyst, Translator, Tutor")
            new_display_name = st.text_input("Display Name", placeholder="e.g., Data Analyst, Translator, Tutor")
            new_description = st.text_area("Description", placeholder="Describe the agent type's role and capabilities")
            new_system_prompt = st.text_area("System Prompt", placeholder="The system prompt for this agent type", height=300)
            
            # Add button
            if st.button("Add Agent Type"):
                # Validate inputs
                if not new_agent_type_id:
                    st.error("Agent Type ID is required.")
                elif not new_display_name:
                    st.error("Display Name is required.")
                elif not new_system_prompt:
                    st.error("System Prompt is required.")
                elif new_agent_type_id in agent_types_dict:
                    st.error(f"Agent Type '{new_agent_type_id}' already exists. Please use a different ID.")
                else:
                    # Add the new agent type
                    agent_types_dict[new_agent_type_id] = {
                        "display_name": new_display_name,
                        "description": new_description,
                        "system_prompt": new_system_prompt
                    }
                    
                    # Save the updated agent types configuration
                    st.session_state.agent_types["agent_types"] = agent_types_dict
                    save_agent_types(st.session_state.agent_types)
                    
                    st.success(f"New agent type '{new_agent_type_id}' has been added successfully!")
                    time.sleep(1)  # Give the user time to see the success message
                    st.rerun()  # Refresh the UI


# Make Agent Configuration collapsible and collapsed by default
with st.expander("Agent Configuration", expanded=False):
    # Create new agent
    col1, col2 = st.columns(2)
    with col1:
        new_agent_name = st.text_input("Agent Name")
    with col2:
        # Get agent types dynamically from configuration
        if "agent_types" not in st.session_state:
            st.session_state.agent_types = load_agent_types()
        agent_types_dict = st.session_state.agent_types.get("agent_types", {})
        agent_type_options = list(agent_types_dict.keys())
        
        # Make sure 'Custom' is always an option
        if "Custom" not in agent_type_options:
            agent_type_options.append("Custom")
            
        new_agent_type = st.selectbox("Agent Type", agent_type_options)
    
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
        
        # Initialize agent_to_edit in session state if it doesn't exist
        if "agent_to_edit" not in st.session_state:
            st.session_state.agent_to_edit = None
            
        # Use columns for better layout
        agent_cols = st.columns(3)
        for i, (agent_name, agent) in enumerate(st.session_state.agents.items()):
            with agent_cols[i % 3]:
                st.write(f"**{agent_name}**")
                st.write(f"Type: {agent.agent_type}")
                st.write(f"Model: {agent.model}")
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    # Edit button for each agent
                    if st.button(f"Edit", key=f"edit_{agent_name}"):
                        st.session_state.agent_to_edit = agent_name
                        
                with col2:
                    # Delete button for each agent
                    if st.button(f"Delete", key=f"delete_{agent_name}"):
                        del st.session_state.agents[agent_name]
                        # If this is the agent being edited, clear the edit state
                        if st.session_state.agent_to_edit == agent_name:
                            st.session_state.agent_to_edit = None
                        st.rerun()
        
        # Edit form appears when an agent is selected for editing
        if st.session_state.agent_to_edit:
            agent_name = st.session_state.agent_to_edit
            agent = st.session_state.agents[agent_name]
            
            st.divider()
            st.subheader(f"Edit Agent: {agent_name}")
            
            # Display and edit agent fields
            # Get agent types dynamically from configuration
            if "agent_types" not in st.session_state:
                st.session_state.agent_types = load_agent_types()
            agent_types_dict = st.session_state.agent_types.get("agent_types", {})
            agent_type_options = list(agent_types_dict.keys())
            
            # Make sure 'Custom' is always an option
            if "Custom" not in agent_type_options:
                agent_type_options.append("Custom")
                
            # Find the index of the current agent type
            try:
                type_index = agent_type_options.index(agent.agent_type)
            except ValueError:
                type_index = 0  # Default to first option if not found
                
            new_agent_type = st.selectbox("Agent Type", agent_type_options, index=type_index, key="edit_agent_type")
            
            # Model selection
            if "available_models" in st.session_state:
                new_model = st.selectbox("Agent Model", st.session_state.available_models, index=st.session_state.available_models.index(agent.model) if agent.model in st.session_state.available_models else 0, key="edit_agent_model")
            else:
                new_model = st.text_input("Agent Model (Ollama not connected)", value=agent.model, key="edit_agent_model_text")
            
            # Custom prompt for custom agent type
            new_custom_prompt = None
            if new_agent_type == "Custom":
                # Show the current custom prompt if it exists
                current_prompt = agent.custom_prompt if agent.custom_prompt else ""
                new_custom_prompt = st.text_area("Custom Agent Prompt", value=current_prompt, height=150, key="edit_custom_prompt")
                
            # Save and Cancel buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Changes", type="primary"):
                    try:
                        # Create a new agent with the updated values
                        updated_agent = create_agent(
                            name=agent_name,
                            agent_type=new_agent_type,
                            model=new_model,
                            custom_prompt=new_custom_prompt
                        )
                        
                        # Replace the old agent with the updated one
                        st.session_state.agents[agent_name] = updated_agent
                        
                        # Save the updated configuration
                        _save_current_configuration()
                        
                        # Clear the edit state
                        st.session_state.agent_to_edit = None
                        
                        st.success(f"Agent {agent_name} updated successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating agent: {str(e)}")
                        if st.session_state.debug_mode:
                            st.exception(e)
            
            with col2:
                if st.button("Cancel"):
                    st.session_state.agent_to_edit = None
                    st.rerun()

# Initialize expander state if it doesn't exist
if "group_chat_expander_open" not in st.session_state:
    st.session_state.group_chat_expander_open = False

# Initialize active tab tracking if it doesn't exist
if "active_gc_tab" not in st.session_state:
    st.session_state.active_gc_tab = None  # Default to no active tab
    
# Make Group Chat Management collapsible and track its state
with st.expander("Group Chat Management", expanded=st.session_state.group_chat_expander_open):
    # Define tab names
    tab_names = ["Create New Group Chat", "Use Saved Group Chat", "Manage Configurations", "Conversations"]
    
    # Create a container for the tab navigation
    tab_cols = st.columns(len(tab_names))
    
    # Create custom tab navigation that will maintain state
    for i, (name, col) in enumerate(zip(tab_names, tab_cols)):
        # Determine if this tab is active
        is_active = (i == st.session_state.active_gc_tab)
        
        # Tab styling and interaction
        if is_active:
            # Active tab styling with deselect option
            if col.button(f"✓ {name}", key=f"tab_btn_{i}"):
                # Clicking an active tab deselects it
                st.session_state.active_gc_tab = None
                st.rerun()
        else:
            # Inactive tab with clickable button
            if col.button(name, key=f"tab_btn_{i}"):
                st.session_state.active_gc_tab = i
                st.rerun()
    
    # Add a divider for visual separation
    st.divider()
    
    # Create placeholder tabs to maintain the same code structure
    # We'll only show content for the active tab
    tab1 = tab2 = tab3 = tab4 = st.empty()

# Display content only if a tab is selected
if st.session_state.active_gc_tab is None:
    # No tab selected - show welcome message
    st.markdown("### Group Chat Management")
    st.info("Select an option above to create, use, or manage your group chats.")
elif st.session_state.active_gc_tab == 0:  # Tab 1: Create New Group Chat
    if st.session_state.agents:
        # Custom name for the group chat configuration
        group_chat_name = st.text_input("Group Chat Name", value="My Group Chat", 
                                      help="Give your group chat configuration a descriptive name")
        
        # Select agents for the group chat
        group_chat_agents = st.multiselect(
            "Select Agents for Group Chat",
            options=list(st.session_state.agents.keys())
        )
        
        # Only show the advanced configuration if agents are selected
        if group_chat_agents and len(group_chat_agents) >= 2:
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
        else:
            # When no agents are selected, show a message
            require_consensus = True
            max_rounds = 5
            if group_chat_agents:
                st.info("Please select at least 2 agents to configure the group chat settings.")
            else:
                st.info("Select agents from the list to get started.")
        
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

elif st.session_state.active_gc_tab == 1:  # Tab 2: Use Saved Group Chat
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
            format_func=format_chat_name,
            key="saved_chat_selector" # Use a consistent key for the radio button
        )
        
        # Keep the expander open when making a selection
        st.session_state.group_chat_expander_open = True
        
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
                    # Keep the expander open during activation
                    st.session_state.group_chat_expander_open = True
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

elif st.session_state.active_gc_tab == 2:  # Tab 3: Manage Configurations
    # Initialize group_chat_to_edit in session state if it doesn't exist
    if "group_chat_to_edit" not in st.session_state:
        st.session_state.group_chat_to_edit = None
        
    if st.session_state.all_saved_group_chats:
        st.subheader("Manage Group Chat Configurations")
        
        # Display all saved configurations with management options
        for config_name in list(st.session_state.all_saved_group_chats.keys()):
            config = st.session_state.all_saved_group_chats[config_name]
            
            # Skip if this is the one being edited (it will be shown in the edit form below)
            if st.session_state.group_chat_to_edit == config_name:
                continue
                
            # Create a container for each configuration
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**{config_name}**")
                    st.write(f"Agents: {', '.join(config['agent_names'][:3])}{'...' if len(config['agent_names']) > 3 else ''}")
                    st.write(f"Consensus: {'Yes' if config['require_consensus'] else 'No'} | Max Rounds: {config['max_rounds']}")
                
                with col2:
                    # Action buttons
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    # Edit button
                    with btn_col1:
                        if st.button("✏️", key=f"edit_{config_name}", help=f"Edit '{config_name}'"):
                            st.session_state.group_chat_to_edit = config_name
                            # Keep the expander open during editing
                            st.session_state.group_chat_expander_open = True
                            # Set active tab to Manage Configurations (tab3, index 2)
                            st.session_state.active_gc_tab = 2
                            st.rerun()
                    
                    # Clone button
                    with btn_col2:
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
                    
                    # Delete button
                    with btn_col3:
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
        
        # Edit form for the selected group chat
        if st.session_state.group_chat_to_edit and st.session_state.group_chat_to_edit in st.session_state.all_saved_group_chats:
            config_name = st.session_state.group_chat_to_edit
            config = st.session_state.all_saved_group_chats[config_name]
            
            # Initialize form fields in session state if needed
            if "edit_form_initialized" not in st.session_state or st.session_state.edit_form_initialized != config_name:
                st.session_state.edit_group_chat_name = config_name
                st.session_state.edit_group_chat_agents = config["agent_names"]
                st.session_state.edit_require_consensus = config["require_consensus"]
                st.session_state.edit_max_rounds = config["max_rounds"]
                st.session_state.edit_form_initialized = config_name
            
            st.divider()
            st.subheader(f"Edit Group Chat: {config_name}")
            
            # Edit form with explicitly pre-filled values from session state
            # New name for the group chat
            new_name = st.text_input("Group Chat Name", 
                                   value=st.session_state.edit_group_chat_name, 
                                   key="edit_group_chat_name")
            
            # Select agents for the group chat - make sure we have existing agents selected
            available_agents = list(st.session_state.agents.keys())
            
            # Filter to keep only agents that exist in the available_agents list
            default_agents = [a for a in st.session_state.edit_group_chat_agents if a in available_agents]
            
            selected_agents = st.multiselect(
                "Select Agents for Group Chat",
                options=available_agents,
                default=default_agents,
                key="edit_group_chat_agents"
            )
            
            # Initialize values in case they weren't set properly
            if "edit_require_consensus" not in st.session_state:
                st.session_state.edit_require_consensus = config["require_consensus"]
            if "edit_max_rounds" not in st.session_state:
                st.session_state.edit_max_rounds = config["max_rounds"]
                
            # Only show advanced configuration if agents are selected
            if selected_agents and len(selected_agents) >= 2:
                # Show a divider and heading for the advanced section
                st.divider()
                st.subheader("Advanced Configuration")
                
                # Consensus and rounds options
                col1, col2 = st.columns(2)
                with col1:
                    require_consensus = st.checkbox("Require Consensus", 
                                                  value=st.session_state.edit_require_consensus, 
                                                  key="edit_require_consensus",
                                                  help="When enabled, agents will discuss until consensus is reached or max rounds is hit")
                with col2:
                    max_rounds = st.number_input("Maximum Discussion Rounds", 
                                               min_value=1, max_value=99, 
                                               value=st.session_state.edit_max_rounds,
                                               key="edit_max_rounds",
                                               help="Maximum number of discussion rounds before presenting results")
                
                # Explain how consensus works
                if require_consensus:
                    st.info("🤝 **Consensus Mode:** Agents will have multiple rounds of discussion. A Manager agent will "
                           "evaluate when consensus is reached. If no Manager agent exists, a Critic or another agent "
                           "will serve as the discussion manager.")
            else:
                # Default values when no agents are selected - assign directly, don't try to access session state
                require_consensus = config["require_consensus"]
                max_rounds = config["max_rounds"]
                
                # Show a message
                if selected_agents:
                    st.info("Please select at least 2 agents to configure advanced settings.")
                else:
                    st.info("Select agents from the list to configure this group chat.")
            
            # Save and Cancel buttons
            save_col, cancel_col = st.columns(2)
            with save_col:
                if st.button("Save Changes", key="save_group_chat_changes", type="primary"):
                    # Check if we have enough agents selected
                    if len(selected_agents) < 2:
                        st.error("Please select at least 2 agents for the group chat.")
                    else:
                        try:
                            # Create the updated config
                            updated_config = {
                                "agent_names": selected_agents,
                                "require_consensus": require_consensus,
                                "max_rounds": int(max_rounds),
                                "created_at": config.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S")),
                                "active": config.get("active", False)
                            }
                            
                            # Handle name change if needed
                            if new_name != config_name and new_name:
                                # Check if the new name already exists
                                if new_name in st.session_state.all_saved_group_chats:
                                    st.error(f"A group chat with the name '{new_name}' already exists. Please choose a different name.")
                                else:
                                    # Remove the old config
                                    del st.session_state.all_saved_group_chats[config_name]
                                    if config_name in st.session_state.saved_group_chats:
                                        del st.session_state.saved_group_chats[config_name]
                                    
                                    # Add with the new name
                                    st.session_state.all_saved_group_chats[new_name] = updated_config
                                    st.session_state.saved_group_chats[new_name] = updated_config
                                    
                                    # Update active group chat reference if needed
                                    if st.session_state.active_group_chat == config_name:
                                        st.session_state.active_group_chat = new_name
                                    
                                    # Save the configuration
                                    _save_current_configuration()
                                    st.success(f"Group chat renamed from '{config_name}' to '{new_name}' and updated.")
                                    st.session_state.group_chat_to_edit = None
                                    st.rerun()
                            else:
                                # Just update the existing config
                                st.session_state.all_saved_group_chats[config_name] = updated_config
                                if config_name in st.session_state.saved_group_chats:
                                    st.session_state.saved_group_chats[config_name] = updated_config
                                
                                # Save the configuration
                                _save_current_configuration()
                                st.success(f"Group chat '{config_name}' updated successfully.")
                                st.session_state.group_chat_to_edit = None
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error updating group chat: {str(e)}")
                            if st.session_state.debug_mode:
                                st.exception(e)
            
            with cancel_col:
                if st.button("Cancel", key="cancel_group_chat_edit"):
                    st.session_state.group_chat_to_edit = None
                    st.rerun()
    else:
        st.info("No saved group chat configurations found. Create one in the 'Create New Group Chat' tab.")

elif st.session_state.active_gc_tab == 3:  # Tab 4: Conversations
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

