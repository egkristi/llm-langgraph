from typing import Dict, List, Any, Optional, Tuple, Callable
from langchain_core.messages import HumanMessage, AIMessage
import random
import re
import time

# Import code extraction utilities
from utils.message_processor import process_agent_message

# Import direct executor for code execution
from tools.direct_executor import direct_execute_code

class GroupChat:
    """Implements a group chat with consensus and chat manager functionality."""
    
    def __init__(self, agents: Dict[str, Any], require_consensus: bool = False, max_rounds: int = 3, group_chat_name: str = "Default Group Chat"):
        """
        Initialize the group chat with a dictionary of agents.
        
        Args:
            agents: Dictionary of agent name to agent object
            require_consensus: Whether agents need to reach consensus
            max_rounds: Maximum number of rounds before concluding (default: 3)
            group_chat_name: Name of the group chat (used for workspace management)
        """
        self.agents = agents
        self.require_consensus = require_consensus
        self.max_rounds = max_rounds
        self.group_chat_name = group_chat_name
        
        # Designate one agent as the chat manager if available, otherwise create one
        if "Manager" in self.agents:
            self.manager_agent = self.agents["Manager"]
        elif "Critic" in self.agents:
            # Use Critic as manager if available
            self.manager_agent = self.agents["Critic"]
        else:
            # The first agent will be temporarily used to evaluate consensus
            self.manager_agent = next(iter(self.agents.values()))
    
    def run(self, user_input: str, callback=None) -> Dict[str, str]:
        """
        Run the group chat with the given user input.
        
        Args:
            user_input: The user input to process
            callback: Optional callback function to receive updates during the conversation
            
        Returns:
            Dictionary mapping agent names to their responses
        """
        # Initialize conversation history and responses
        conversation = [{"role": "user", "content": user_input}]
        final_responses = {}
        current_round = 0
        consensus_reached = False
        
        # Continue discussion until consensus or max rounds reached
        while not consensus_reached and current_round < self.max_rounds:
            current_round += 1
            round_responses = {}
            
            # Check if any message in the conversation contains a code execution request
            code_executor_request = False
            last_message = conversation[-1] if conversation else {}
            
            if last_message and "@codeExecutor" in last_message.get("content", ""):
                code_executor_request = True
                print(f"Code execution request detected in round {current_round}")
            
            # Determine agent order, prioritizing Code Runner if code was detected
            agent_order = list(self.agents.keys())
            
            # If there's a code execution request, move codeExecutor to the front
            if code_executor_request and "codeExecutor" in agent_order:
                agent_order.remove("codeExecutor")
                agent_order.insert(0, "codeExecutor")
                print(f"Prioritizing Code Runner agent to execute code")
            
            # Get responses from each agent in the determined order
            for agent_name in agent_order:
                # Skip if agent not in the agents dictionary
                if agent_name not in self.agents:
                    continue
                    
                agent = self.agents[agent_name]
                
                # Skip the manager in the first round so they can evaluate after
                if current_round == 1 and agent_name == "Manager":
                    continue
                    
                # Format conversation context
                context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
                
                # Special handling for Code Runner agent
                if agent_name == "codeExecutor":
                    # Check for code execution requests or file mentions in the conversation
                    contains_code_request = False
                    code_file_mention = None
                    
                    # Look for code execution requests or file mentions in the last message
                    last_message = conversation[-1] if conversation else {}
                    if last_message and "content" in last_message:
                        last_content = last_message["content"]
                        
                        # Check for direct requests to execute code
                        if "@codeExecutor" in last_content or "EXECUTE THIS CODE" in last_content:
                            contains_code_request = True
                            print("Direct code execution request detected")
                            
                            # Extract the file name from the message if it exists
                            import re
                            file_pattern = r'file_name="([^"]+)"'
                            file_matches = re.findall(file_pattern, last_content)
                            
                            if file_matches:
                                code_file_mention = file_matches[0]
                                print(f"Found file to execute: {code_file_mention}")
                    
                    # Create a special prompt for the Code Runner when code execution is requested
                    if contains_code_request:
                        if code_file_mention:
                            # Very direct prompt with the exact file to run
                            full_input = f"EXECUTE THIS CODE FILE IMMEDIATELY: {code_file_mention}\n\nHere is the conversation context for reference:\n{context}\n\nDo not discuss the code, just execute it and report the results."
                        else:
                            # More general prompt to find and execute code
                            full_input = f"There is code that needs to be executed. Find the most recent code file in the workspace and execute it immediately.\n\nHere is the conversation context for reference:\n{context}\n\nDo not discuss the code, just execute it and report the results."
                    else:
                        # Standard prompt for Code Runner with emphasis on code execution
                        full_input = f"Previous messages:\n{context}\n\nYou are the Code Runner agent. Check if there are any code files in the workspace that should be executed. If yes, execute them and report the results. If not, provide your response as {agent_name}:"
                else:
                    # Regular prompt for other agents
                    if current_round == 1:
                        full_input = f"Previous messages:\n{context}\n\nPlease provide your response as {agent_name}:"
                    else:
                        full_input = f"Previous messages:\n{context}\n\nThis is round {current_round} of the discussion. Please refine your thoughts and work toward a consensus with the other agents as {agent_name}:"
                
                # Get agent's response
                response = agent.generate_response(full_input)
                
                # Process the response to extract and store code blocks
                processed_message = process_agent_message(
                    message=response,
                    agent_name=agent_name,
                    group_chat_name=getattr(self, 'group_chat_name', 'Default Group Chat'),
                    round_num=current_round
                )
                
                # Use the processed message (which may include file storage info)
                processed_response = processed_message["content"]
                round_responses[agent_name] = processed_response
                
                # Check if code blocks were extracted and this is not the Code Runner agent
                if processed_message["has_code"] and agent_name != "codeExecutor":
                    print(f"Code detected from {agent_name}. Triggering immediate Docker execution...")
                    
                    # Get the saved files from the processed message
                    saved_files = processed_message["saved_files"]
                    if saved_files:
                        # Handle only certain file types for execution
                        executable_extensions = ["py", "js", "go"]
                        executable_files = []
                        
                        # Find executable files in the saved files
                        for code_file in saved_files:
                            file_name = code_file["filename"]
                            extension = file_name.split('.')[-1] if '.' in file_name else ""
                            
                            if extension in executable_extensions:
                                executable_files.append(code_file)
                        
                        # Execute each executable file
                        for code_file in executable_files:
                            file_name = code_file["filename"]
                            language = code_file["language"]
                            
                            # Determine language from file extension if needed
                            if language == "text":
                                if file_name.endswith(".py"):
                                    language = "python"
                                elif file_name.endswith(".js"):
                                    language = "javascript"
                                elif file_name.endswith(".go"):
                                    language = "go"
                            
                            # Only execute specific languages
                            if language not in ["python", "javascript", "go"]:
                                continue
                                
                            print(f"DIRECT DOCKER EXECUTION: Will execute {file_name} ({language}) in Docker")
                            
                            # Use the new direct Docker execution script for more reliable execution
                            import subprocess
                            import os
                            import sys
                            import time
                            from pathlib import Path
                            
                            # Get the full path to the code file
                            workspace_root = Path("/Users/erling/code/llm-langgraph/workspaces")
                            
                            # Normalize group chat name: convert spaces to underscores and lowercase
                            normalized_group_chat = self.group_chat_name.lower().replace(" ", "_")
                            
                            # Find the actual directory that exists
                            if (workspace_root / normalized_group_chat).exists():
                                group_chat_dir = normalized_group_chat
                            else:
                                # Try to find a matching directory with different casing
                                found = False
                                for dir_path in workspace_root.iterdir():
                                    if dir_path.is_dir() and dir_path.name.lower() == normalized_group_chat:
                                        group_chat_dir = dir_path.name
                                        found = True
                                        break
                                if not found:
                                    # Create the directory if it doesn't exist
                                    group_chat_dir = normalized_group_chat
                                    (workspace_root / group_chat_dir).mkdir(parents=True, exist_ok=True)
                                    (workspace_root / group_chat_dir / "code").mkdir(exist_ok=True)
                                    (workspace_root / group_chat_dir / "output").mkdir(exist_ok=True)
                                    (workspace_root / group_chat_dir / "data").mkdir(exist_ok=True)
                            
                            # Create the full path to the code file
                            code_path = workspace_root / group_chat_dir / "code" / file_name
                            
                            # Print some debugging info
                            print(f"Executing code file: {code_path} (exists: {code_path.exists()})")
                            
                            # Use direct_docker_run.py script which is more reliable
                            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../direct_docker_run.py"))
                            
                            # Build the command to execute
                            cmd = [
                                "python", 
                                script_path,
                                str(code_path), 
                                language
                            ]
                            
                            # Execute the command
                            try:
                                print(f"Running command: {' '.join(cmd)}")
                                start_time = time.time()
                                
                                result = subprocess.run(
                                    cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=30
                                )
                                
                                execution_time = time.time() - start_time
                                
                                # Get the output regardless of return code
                                output_dir = workspace_root / group_chat_dir / "output"
                                # Get the most recent output file
                                output_files = sorted(output_dir.glob("result_*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
                                
                                if output_files:
                                    with open(output_files[0], 'r') as f:
                                        output_content = f.read()
                                else:
                                    output_content = result.stdout
                                
                                # Check for Python exceptions in the output
                                python_exceptions = [
                                    "Traceback (most recent call last):", 
                                    "ModuleNotFoundError:", 
                                    "ImportError:",
                                    "SyntaxError:",
                                    "NameError:",
                                    "TypeError:",
                                    "ValueError:",
                                    "IndexError:",
                                    "KeyError:",
                                    "AttributeError:",
                                    "ZeroDivisionError:",
                                    "RuntimeError:",
                                    "Exception:"
                                ]
                                
                                # Check if the output contains any Python exceptions
                                has_exception = any(exc in output_content for exc in python_exceptions)
                                
                                # Format the execution result
                                if result.returncode == 0 and not has_exception:
                                    execution_result = f"## Code Execution Successful\n\n"
                                    execution_result += f"**File:** `{file_name}`\n\n"
                                    execution_result += f"**Language:** {language}\n\n"
                                    execution_result += f"**Execution Time:** {execution_time:.2f} seconds\n\n"
                                    execution_result += f"### Output:\n\n```\n{output_content}\n```\n\n"
                                else:
                                    # An error occurred - either a Python exception or a non-zero exit code
                                    execution_result = f"## Code Execution Failed\n\n"
                                    execution_result += f"**File:** `{file_name}`\n\n"
                                    execution_result += f"**Language:** {language}\n\n"
                                    execution_result += f"**Execution Time:** {execution_time:.2f} seconds\n\n"
                                    
                                    if has_exception:
                                        execution_result += f"**Python Exception Detected:**\n\n```\n{output_content}\n```\n\n"
                                    else:
                                        execution_result += f"**Error:**\n\n```\n{result.stderr}\n```\n\n"
                                        execution_result += f"**Output:**\n\n```\n{output_content}\n```\n\n"
                                    
                                # Create a message from the Code Runner with the execution results
                                execution_message = {
                                    "role": "codeExecutor", 
                                    "content": f"I executed the code file `{file_name}` in a Docker container:\n\n{execution_result}", 
                                    "round": current_round
                                }
                                
                                # Add the execution result to the conversation
                                conversation.append(execution_message)
                                round_responses["codeExecutor"] = execution_message["content"]
                                
                                # Notify callback of execution result
                                if callback:
                                    callback("codeExecutor", execution_message["content"], current_round)
                                    
                            except Exception as e:
                                print(f"Error executing Docker command: {str(e)}")
                                # Continue the conversation even if execution fails
                
                # Store metadata about code blocks and saved files in the message
                new_message = {
                    "role": agent_name, 
                    "content": processed_response, 
                    "round": current_round,
                    "has_code": processed_message["has_code"],
                    "code_blocks": processed_message["code_blocks"],
                    "saved_files": processed_message["saved_files"]
                }
                conversation.append(new_message)
                
                # If a callback is provided, send the update as it happens
                if callback:
                    callback(agent_name, processed_response, current_round)
            
            # Update final responses with this round's responses
            final_responses.update(round_responses)
            
            # Check for consensus if required
            if self.require_consensus and current_round < self.max_rounds:
                consensus_reached, manager_response = self._evaluate_consensus(conversation, user_input)
                
                if manager_response:
                    # Add manager response to conversation
                    manager_message = {"role": "Manager", "content": manager_response, "round": current_round}
                    conversation.append(manager_message)
                    final_responses["Manager"] = manager_response
                    
                    # Notify callback of manager's response
                    if callback:
                        callback("Manager", manager_response, current_round, is_evaluation=True)
                    
                if consensus_reached:
                    # Add final consensus note
                    consensus_msg = "[Consensus reached] The agents have reached a satisfactory conclusion."
                    system_message = {"role": "System", "content": consensus_msg, "round": current_round}
                    conversation.append(system_message)
                    
                    # Notify callback of system message
                    if callback:
                        callback("System", consensus_msg, current_round, is_system=True)
            else:
                # If not requiring consensus, just do one round
                consensus_reached = True
        
        # If max rounds reached without consensus, add a note
        if self.require_consensus and not consensus_reached and current_round >= self.max_rounds:
            max_rounds_msg = f"[Discussion ended] Maximum of {self.max_rounds} rounds reached without full consensus."
            system_message = {"role": "System", "content": max_rounds_msg, "round": current_round}
            conversation.append(system_message)
            final_responses["System"] = max_rounds_msg
            
            # Notify callback of system message
            if callback:
                callback("System", max_rounds_msg, current_round, is_system=True)
        
        return final_responses
    
    def _evaluate_consensus(self, conversation: List[Dict[str, str]], original_question: str) -> Tuple[bool, Optional[str]]:
        """Evaluate if the agents have reached consensus."""
        # Format conversation for the manager
        formatted_convo = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
        
        # Create prompt for the manager to evaluate consensus
        manager_prompt = f"""You are evaluating whether the agents have reached a satisfactory consensus on this question: 

{original_question}

Below is the full conversation:
{formatted_convo}

Have the agents reached a consensus or provided a satisfactory collective response? 
Consider whether there are major disagreements or if the responses complement each other well.
Respond with your evaluation and suggest what is still needed if consensus hasn't been reached."""
        
        # Get manager's evaluation
        manager_response = self.manager_agent.generate_response(manager_prompt)
        
        # Determine if consensus reached based on manager's response
        consensus_keywords = ['consensus', 'agreement', 'agree', 'aligned', 'complementary', 'satisfactory']
        negative_keywords = ['disagree', 'conflict', 'contradiction', 'inconsistent', 'no consensus']
        
        consensus_score = sum(1 for word in consensus_keywords if word.lower() in manager_response.lower())
        negative_score = sum(1 for word in negative_keywords if word.lower() in manager_response.lower())
        
        # Determine consensus based on keyword presence
        consensus_reached = consensus_score > negative_score
        
        return consensus_reached, manager_response
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert group chat to a dictionary for serialization.
        
        Returns:
            Dictionary containing the group chat configuration
        """
        return {
            "agent_names": list(self.agents.keys()),
            "require_consensus": self.require_consensus,
            "max_rounds": self.max_rounds
        }


def create_group_chat(agents: Dict[str, Any], require_consensus: bool = False, max_rounds: int = 3, group_chat_name: str = "Default Group Chat") -> GroupChat:
    """Create a group chat with the given agents.
    
    Args:
        agents: Dictionary of agent name to agent object
        require_consensus: Whether agents need to reach consensus
        max_rounds: Maximum number of rounds before concluding
        group_chat_name: Name of the group chat (used for workspace management)
        
    Returns:
        A configured GroupChat object
    """
    return GroupChat(agents, require_consensus=require_consensus, max_rounds=max_rounds, group_chat_name=group_chat_name)
