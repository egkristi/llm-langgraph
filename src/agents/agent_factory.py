from typing import Dict, Optional, Any, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import BaseTool
from langchain.agents import create_react_agent, AgentExecutor

import json
from pathlib import Path
import ollama
from models.model_manager import get_model
from tools.tool_registry import get_tools_for_agent_type

# Path to agent types configuration
AGENT_TYPES_FILE = Path("config/agent_types.json")

class Agent:
    def __init__(self, name: str, agent_type: str, model: str, custom_prompt: Optional[str] = None):
        self.name = name
        self.agent_type = agent_type
        self.model = model
        self.custom_prompt = custom_prompt
        self.llm = get_model(model)
        self.tools = get_tools_for_agent_type(agent_type)
        self.agent_executor = self._create_agent_executor()
        
    def _create_agent_executor(self) -> AgentExecutor:
        """Create a LangChain agent executor with the tools."""
        # Get the system prompt based on agent type
        system_base_prompt = self._get_system_prompt()
        
        # Create a system message that includes tool information
        system_prompt = f"{system_base_prompt}\n\nYou have access to the following tools:\n\n{{tools}}\n\nUse the following format:\n\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [{{tool_names}}]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the final answer to the original input question"
        
        # Create a prompt with ReAct format
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the ReAct agent
        agent = create_react_agent(self.llm, self.tools, prompt)
        
        # Create the agent executor
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            handle_parsing_errors=True
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt based on agent type.
        
        Loads agent types and prompts from the agent_types.json configuration file.
        Falls back to a default prompt if the agent type is not found.
        
        Returns:
            str: The system prompt for the agent
        """
        # Return custom prompt if provided
        if self.custom_prompt:
            return self.custom_prompt
        
        try:
            # Load agent types from the configuration file
            if AGENT_TYPES_FILE.exists():
                with open(AGENT_TYPES_FILE, 'r') as f:
                    agent_types_config = json.load(f)
                    
                # Get the system prompt for the agent type
                agent_types = agent_types_config.get("agent_types", {})
                agent_config = agent_types.get(self.agent_type, {})
                
                # If we found a system prompt for this agent type, return it
                if "system_prompt" in agent_config:
                    return agent_config["system_prompt"]
        except Exception as e:
            print(f"Error loading agent types from {AGENT_TYPES_FILE}: {str(e)}")
        
        # Default prompt if agent type not found or error occurred
        return f"You are a helpful AI assistant named {self.name}. Your role is to act as a {self.agent_type}. \
Provide helpful, accurate, and concise responses."

    
    def generate_response(self, input_text: str) -> str:
        """Generate a response to the input text using the agent executor."""
        try:
            # Create a simpler, non-ReAct response when there are issues
            try:
                # Run the agent executor with proper parameters
                response = self.agent_executor.invoke({
                    "input": input_text,
                    "chat_history": [],
                    "agent_scratchpad": []  # Initialize as empty list of messages
                })
                
                # Extract the agent's response
                if "output" in response:
                    return response["output"]
                elif "answer" in response:
                    return response["answer"]
                else:
                    return str(response)
            except Exception as agent_error:
                # Fallback to a simpler approach if the agent executor fails
                system_message = self._get_system_prompt()
                prompt = f"{system_message}\n\nUser: {input_text}"
                
                # Use a simple invoke that returns a string
                response = self.llm.invoke(prompt)
                
                # Handle different response types
                if hasattr(response, 'content'):
                    return response.content
                elif isinstance(response, str):
                    return response
                else:
                    return str(response)
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary for serialization."""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "model": self.model,
            "custom_prompt": self.custom_prompt
        }

def create_agent(name: str, agent_type: str, model: str, custom_prompt: Optional[str] = None) -> Agent:
    """Create an agent with the specified parameters."""
    return Agent(name=name, agent_type=agent_type, model=model, custom_prompt=custom_prompt)
