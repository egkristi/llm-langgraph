from typing import Dict, List, Any, Optional, Tuple, Callable
from langchain_core.messages import HumanMessage, AIMessage
import random

class GroupChat:
    """Implements a group chat with consensus and chat manager functionality."""
    
    def __init__(self, agents: Dict[str, Any], require_consensus: bool = False, max_rounds: int = 3):
        """
        Initialize the group chat with a dictionary of agents.
        
        Args:
            agents: Dictionary of agent name to agent object
            require_consensus: Whether agents need to reach consensus
            max_rounds: Maximum number of rounds before concluding (default: 3)
        """
        self.agents = agents
        self.require_consensus = require_consensus
        self.max_rounds = max_rounds
        
        # Designate one agent as the chat manager if available, otherwise create one
        if "Manager" in self.agents:
            self.manager_agent = self.agents["Manager"]
        elif "Critic" in self.agents:
            # Use Critic as manager if available
            self.manager_agent = self.agents["Critic"]
        else:
            # The first agent will be temporarily used to evaluate consensus
            self.manager_agent = next(iter(self.agents.values()))
    
    def run(self, user_input: str) -> Dict[str, str]:
        """
        Run the group chat with the given user input.
        
        Args:
            user_input: The user input to process
            
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
            
            # Get responses from each agent
            for agent_name, agent in self.agents.items():
                # Skip the manager in the first round so they can evaluate after
                if current_round == 1 and agent_name == "Manager":
                    continue
                    
                # Format conversation context
                context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
                
                # Create appropriate prompt based on round
                if current_round == 1:
                    full_input = f"Previous messages:\n{context}\n\nPlease provide your response as {agent_name}:"
                else:
                    full_input = f"Previous messages:\n{context}\n\nThis is round {current_round} of the discussion. Please refine your thoughts and work toward a consensus with the other agents as {agent_name}:"
                
                # Get agent's response
                response = agent.generate_response(full_input)
                round_responses[agent_name] = response
                
                # Add response to conversation history
                conversation.append({"role": agent_name, "content": response})
            
            # Update final responses with this round's responses
            final_responses.update(round_responses)
            
            # Check for consensus if required
            if self.require_consensus and current_round < self.max_rounds:
                consensus_reached, manager_response = self._evaluate_consensus(conversation, user_input)
                
                if manager_response:
                    # Add manager response to conversation
                    conversation.append({"role": "Manager", "content": manager_response})
                    final_responses["Manager"] = manager_response
                    
                if consensus_reached:
                    # Add final consensus note
                    consensus_msg = "[Consensus reached] The agents have reached a satisfactory conclusion."
                    conversation.append({"role": "System", "content": consensus_msg})
            else:
                # If not requiring consensus, just do one round
                consensus_reached = True
        
        # If max rounds reached without consensus, add a note
        if self.require_consensus and not consensus_reached and current_round >= self.max_rounds:
            max_rounds_msg = f"[Discussion ended] Maximum of {self.max_rounds} rounds reached without full consensus."
            conversation.append({"role": "System", "content": max_rounds_msg})
            final_responses["System"] = max_rounds_msg
        
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


def create_group_chat(agents: Dict[str, Any], require_consensus: bool = False, max_rounds: int = 3) -> GroupChat:
    """Create a group chat with the given agents.
    
    Args:
        agents: Dictionary of agent name to agent object
        require_consensus: Whether agents need to reach consensus
        max_rounds: Maximum number of rounds before concluding
        
    Returns:
        A configured GroupChat object
    """
    return GroupChat(agents, require_consensus=require_consensus, max_rounds=max_rounds)
