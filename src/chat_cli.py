#!/usr/bin/env python
"""
Multi-Agent LLM Chat CLI

A command-line interface for interacting with multi-agent LLM conversations.
This allows you to run the multi-agent system without the Streamlit UI.

Usage:
    python chat_cli.py [--model MODEL] [--agents AGENTS] [--max-rounds N] [--consensus] [--interactive] [QUESTION]
    
Examples:
    python chat_cli.py --model llama3 --interactive
    python chat_cli.py "What is the square root of 144?"
    python chat_cli.py --agents "Math Expert,Coder" "Write a Python function to calculate prime numbers"
    python chat_cli.py --agents "Assistant,Manager" --max-rounds 5 --consensus "Explain quantum computing"
"""

import os
import time
import json
import argparse
from typing import Dict, Any, List
from pathlib import Path

from agents.agent_factory import create_agent
from graph.group_chat import create_group_chat
from models.model_manager import ModelManager
from memory.conversation_memory import ConversationMemory
from utils.config import load_agent_types, save_agent_types, AGENT_TYPES_FILE


def display_agent_types_info(agent_types):
    """Display detailed information about available agent types."""
    print("\nAvailable Agent Types:")
    print("=====================")
    for agent_type, details in agent_types.items():
        print(f"\nAgent Type: {agent_type}")
        print(f"Display Name: {details.get('display_name', 'N/A')}")
        print(f"Description: {details.get('description', 'N/A')}")
    print("\n")


def setup_agents(model_name="llama3", agent_types_to_use=None, available_agent_types=None):
    """Set up the agents for the chat using the specified model.
    
    Args:
        model_name: Name of the model to use for agents
        agent_types_to_use: List of agent types to include (default: None, use standard set)
        available_agent_types: Dictionary of available agent types from configuration
    
    Returns:
        Dictionary of created agents
    """
    agents = {}
    
    # If no specific agent types are requested, use a default set
    if not agent_types_to_use:
        agent_types_to_use = ["Assistant", "Researcher", "Manager"]
    
    # If available_agent_types wasn't provided, load them
    if available_agent_types is None:
        available_agent_types = load_agent_types().get("agent_types", {})
    
    print("\nCreating agents...")
    for agent_type in agent_types_to_use:
        # Skip invalid agent types
        if agent_type not in available_agent_types and agent_type != "Custom":
            print(f"✗ Skipping invalid agent type: {agent_type}")
            continue
            
        try:
            agent_name = agent_type
            agents[agent_name] = create_agent(
                name=agent_name,
                agent_type=agent_type,
                model=model_name,
            )
            print(f"✓ Created {agent_name} agent")
        except Exception as e:
            print(f"✗ Failed to create {agent_type} agent: {str(e)}")
    
    return agents


def interactive_mode(group_chat):
    """Run the multi-agent chat in interactive mode where the user can type questions."""
    print("\nInteractive Multi-Agent Chat (type 'exit' to quit)")
    print("================================================")
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting chat...")
                break
                
            if not user_input.strip():
                continue
                
            start_time = time.time()
            responses = group_chat.run(user_input)
            
            for agent_name, response in responses.items():
                print(f"\n{agent_name}: {response}")
                
            elapsed_time = time.time() - start_time
            print(f"\n(Response generated in {elapsed_time:.2f} seconds)")
            
        except KeyboardInterrupt:
            print("\nChat interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")


def main():
    """Run the multi-agent chat system via CLI."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Multi-Agent LLM Chat CLI")
    parser.add_argument("--model", type=str, default="llama3", 
                      help="Model to use for the agents (default: llama3)")
    parser.add_argument("--question", type=str,
                      help="Question to ask the agents (specified with --question or as the last argument)")
    parser.add_argument("--interactive", action="store_true",
                      help="Run in interactive mode, allowing multiple questions")
    parser.add_argument("--agents", type=str, 
                      help="Comma-separated list of agent types to use (default: Assistant,Researcher,Manager)")
    parser.add_argument("--list-agent-types", action="store_true",
                      help="List all available agent types and exit")
    parser.add_argument("--max-rounds", type=int, default=3,
                      help="Maximum number of discussion rounds before concluding (default: 3)")
    parser.add_argument("--consensus", action="store_true",
                      help="Require agents to reach consensus before concluding")
    # Add positional argument for the question as an alternative to --question
    parser.add_argument("question_pos", nargs="?", type=str,
                      help="Question to ask (can be provided directly without --question)")
    
    args = parser.parse_args()
    
    print("Multi-Agent LLM Chat CLI")
    print("=======================\n")
    
    # Initialize model manager
    model_manager = ModelManager(default_model=args.model)
    
    # Check Ollama connection
    try:
        models = model_manager.list_available_models()
        print(f"Connected to Ollama. Available models: {', '.join(models)}")
    except Exception as e:
        print(f"Error connecting to Ollama: {str(e)}")
        print("Please make sure Ollama is running with 'ollama serve'")
        return
    
    # Load agent types from configuration
    agent_types_config = load_agent_types()
    agent_types = agent_types_config.get("agent_types", {})
    
    # If user just wants to list agent types
    if args.list_agent_types:
        display_agent_types_info(agent_types)
        return
        
    # Parse agent types to use from command line if provided
    agent_types_to_use = None
    if args.agents:
        agent_types_to_use = [agent_type.strip() for agent_type in args.agents.split(",")]
        # Validate agent types
        invalid_types = [t for t in agent_types_to_use if t not in agent_types]
        if invalid_types:
            print(f"Warning: Unknown agent types: {', '.join(invalid_types)}")
            print(f"Available types: {', '.join(agent_types.keys())}")
    
    # Create agents
    agents = setup_agents(args.model, agent_types_to_use, agent_types)
    
    if not agents:
        print("No agents were created successfully. Exiting.")
        return
        
    # Create group chat
    print("\nSetting up group chat...")
    group_chat = create_group_chat(
        agents, 
        require_consensus=args.consensus, 
        max_rounds=args.max_rounds,
        group_chat_name="CLI Chat"
    )
    print(f"✓ Group chat created with {len(agents)} agents")
    if args.consensus:
        print(f"✓ Consensus mode enabled")
    print(f"✓ Maximum {args.max_rounds} discussion rounds")
    
    
    # Interactive mode
    if args.interactive:
        interactive_mode(group_chat)
        return
        
    # Single question mode - check for question from either --question or positional argument
    question = args.question or args.question_pos
    if question:
        messages = [question]
    else:
        # Demo questions if no specific question was provided
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
    
    print("\nChat session complete!")


if __name__ == "__main__":
    main()
