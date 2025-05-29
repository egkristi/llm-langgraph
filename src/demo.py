#!/usr/bin/env python
"""
Demo script for the multi-agent LLM chat system.
This demonstrates how to use the system programmatically without the Streamlit UI.
"""

import os
import time
from typing import Dict, Any

from agents.agent_factory import create_agent
from graph.group_chat import create_group_chat
from models.model_manager import ModelManager
from memory.conversation_memory import ConversationMemory

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
    
    agents["Critic"] = create_agent(
        name="Critic",
        agent_type="Critic",
        model="llama3",
    )
    print("✓ Created Critic agent")
    
    # Create group chat
    print("\nSetting up group chat...")
    group_chat = create_group_chat(agents)
    print("✓ Group chat created with 3 agents")
    
    # Process messages
    messages = [
        "What are the main challenges in artificial intelligence today?",
        "How do those challenges affect machine learning deployments?",
        "Thank you for the information!"
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
