from typing import Dict, Optional, Any, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import BaseTool
from langchain.agents import create_react_agent, AgentExecutor

import ollama
from models.model_manager import get_model
from tools.tool_registry import get_tools_for_agent_type

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
        """Get the system prompt based on agent type."""
        if self.custom_prompt:
            return self.custom_prompt
            
        prompts = {
            "Assistant": """You are a helpful AI assistant. Your goal is to provide accurate, 
            concise, and helpful responses to user queries. Be polite and informative. 
            Use the tools available to you when appropriate.""",
            
            "Researcher": """You are a research specialist. Your goal is to analyze information, 
            gather facts, and provide well-researched answers. Cite sources when possible and 
            maintain academic rigor in your responses. Use the tools available to you to 
            find the most accurate information.""",
            
            "Coder": """You are a coding expert. Provide clean, efficient code solutions to 
            programming problems. Explain your code when appropriate and follow best practices 
            for the language or framework in question. Use the tools available to you to help 
            analyze and improve code.""",
            
            "Math Expert": """You are a mathematics specialist. Solve mathematical problems 
            step-by-step, showing your work. Be precise in your calculations and explanations. 
            Use the calculator tool when needed to ensure accuracy.""",
            
            "Critic": """You are a critical thinker. Analyze arguments, identify flaws in reasoning, 
            and provide constructive criticism. Be thorough but fair in your assessments. 
            Use the fact-checking tools available to you to verify information.""",

            "Manager": """You are the supervising manager agent. Your sole responsibility is ensuring the user's original question gets answered completely and accurately.
            For every interaction:
            1. First, identify exactly what the user is asking
            2. Review all agent responses to check if they answer the question
            3. If something is missing or off-topic, explicitly state what needs to be addressed
            4. Synthesize all relevant information into a final answer that directly addresses the original query
            5. Confirm: "Does this fully answer your question about [topic]?"
            Never let the conversation drift without first ensuring the initial question is resolved. You are the quality gatekeeper - if the user's question isn't properly answered, it's your job to fix that."""
        }
        
        return prompts.get(self.agent_type, "You are a helpful AI assistant. Use the tools available to you when needed.")
    
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
