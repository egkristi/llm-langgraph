#!/usr/bin/env python
"""
Demo script for the multi-agent LLM chat system.
This demonstrates how to use the system programmatically without the Streamlit UI.
"""

import os
import time
import json
from typing import Dict, Any
from pathlib import Path

from agents.agent_factory import create_agent
from graph.group_chat import create_group_chat
from models.model_manager import ModelManager
from memory.conversation_memory import ConversationMemory
from utils.config import load_agent_types, save_agent_types, AGENT_TYPES_FILE

def main():
    """Run a demonstration of the multi-agent chat system."""
    print("Starting Multi-Agent LLM Chat Demo")
    print("==================================\n")
    
    # Initialize model manager
    model_manager = ModelManager(default_model="llama3")
    
    # Check Ollama connection
    try:
        models = model_manager.list_available_models()
        print(f"Connected to Ollama. Available models: {', '.join(models)}")
    except Exception as e:
        print(f"Error connecting to Ollama: {str(e)}")
        print("Please make sure Ollama is running with 'ollama serve'")
        return
    
    # Load agent types from configuration
    print("\nLoading agent types from configuration...")
    agent_types_config = load_agent_types()
    agent_types = agent_types_config.get("agent_types", {})
    
    # Display available agent types
    print(f"Available agent types: {', '.join(agent_types.keys())}")
    
    # Optionally create a new agent type programmatically
    print("\nCreating a custom agent type programmatically...")
    demo_agent_type = {
        "display_name": "Demo Agent",
        "description": "An agent type created programmatically for demonstration",
        "system_prompt": "You are a demonstration agent created to show how to programmatically create agent types. Your goal is to provide clear and informative responses while highlighting how agent types can be managed outside of the UI."
    }
    
    # Add the new agent type to the configuration
    if "Demo Agent" not in agent_types:
        agent_types["Demo Agent"] = demo_agent_type
        agent_types_config["agent_types"] = agent_types
        
        # Save the updated configuration
        save_agent_types(agent_types_config)
        print("✓ Created and saved 'Demo Agent' type")
    else:
        print("✓ 'Demo Agent' type already exists")
    
    # Reload agent types to confirm our changes were saved
    updated_agent_types = load_agent_types().get("agent_types", {})
    
    # Create agents
    agents = {}
    
    print("\nCreating agents...")
    agents["Assistant"] = create_agent(
        name="Assistant",
        agent_type="Assistant",
        model="llama3",
    )
    print("✓ Created Assistant agent")
    
    agents["Researcher"] = create_agent(
        name="Researcher",
        agent_type="Researcher",
        model="llama3",
    )
    print("✓ Created Researcher agent")
    
    # Use our new Demo agent type
    agents["Demo"] = create_agent(
        name="Demo",
        agent_type="Demo Agent",  # Using our programmatically created agent type
        model="llama3",
    )
    print("✓ Created Demo agent with custom agent type")
    
    # Create group chat
    print("\nSetting up group chat...")
    group_chat = create_group_chat(agents)
    print(f"✓ Group chat created with {len(agents)} agents")
    
    # Function to display agent types in detail (optional)
    def display_agent_types_info(agent_types):
        print("\nDetailed Agent Types Information:")
        print("==================================")
        for agent_type, details in agent_types.items():
            print(f"\nAgent Type: {agent_type}")
            print(f"Display Name: {details.get('display_name', 'N/A')}")
            print(f"Description: {details.get('description', 'N/A')}")
            prompt = details.get('system_prompt', '')
            print(f"System Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print("\n")
    
    # Display detailed information about agent types (uncomment to use)
    # display_agent_types_info(updated_agent_types)
    
    # Process messages
    messages = [
        "Explain the concept of agent types and why they are useful in a multi-agent system.",
        "How can custom agent types improve the performance of a group chat?",
        "What would be a good system prompt for an agent specialized in data analysis?"
    ]
    
    print("\nStarting conversation:")
    print("======================")
    
    for message in messages:
        print(f"\nUser: {message}")
        start_time = time.time()
        
        try:
            responses = group_chat.run(message)
            
            for agent_name, response in responses.items():
                print(f"\n{agent_name}: {response}")
                
            elapsed_time = time.time() - start_time
            print(f"\n(Response generated in {elapsed_time:.2f} seconds)")
        
        except Exception as e:
            print(f"Error: {str(e)}")
    
    print("\nDemo complete!")

if __name__ == "__main__":
    main()
