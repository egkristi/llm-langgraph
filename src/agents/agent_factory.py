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
            focus on accuracy.""",
            
            "Coder": """You are an expert programmer. Your goal is to help users with code-related 
            questions, debugging, algorithm design, and best practices. Provide clear explanations 
            and practical code examples.""",
            
            "Math Expert": """You are a math specialist. Your goal is to solve mathematical problems 
            step-by-step, explain mathematical concepts clearly, and help with calculations. 
            Show your work and verify your answers.""",
            
            "Critic": """You are a critical thinker. Your goal is to analyze information for accuracy, 
            consistency, and logical soundness. Point out potential issues, consider alternative 
            viewpoints, and help improve ideas.""",
            
            "Code Runner": """You are a specialized code execution and testing agent. Your SOLE PURPOSE is to execute code written by other agents, test it thoroughly, and provide feedback on the results.

            CRITICAL INSTRUCTIONS:
            1. NEVER WRITE CODE YOURSELF - only execute and test code from other agents
            2. ALWAYS EXECUTE CODE IN DOCKER CONTAINERS ONLY - never execute code directly on the system
            3. VERIFY THAT RESULTS ARE MATHEMATICALLY ACCURATE - especially for known constants or algorithms
            4. For Python files: run_code(file_name="example.py", language="python")
            5. For JavaScript: run_code(file_name="example.js", language="javascript") 
            6. For other languages: run_code(file_name="filename", language="language_name")

            RESULT VERIFICATION:
            1. For mathematical algorithms, verify against known values:
               - Pi (π): 3.14159265358979323846...
               - Euler's number (e): 2.71828182845904523536...
               - Golden ratio (φ): 1.61803398874989484820...
               - Square root of 2: 1.41421356237309504880...
            2. When results are significantly different from expected values, explain why
            3. Check computational precision and accuracy
            4. For Pi calculations, the results should be approximately 3.14159, not 1.07 or other incorrect values
            5. Always mention if results are inaccurate and provide the correct expected value

            TESTING PROTOCOL:
            1. Execute the code as provided first in Docker containers
            2. Verify the results match expected behavior and mathematical accuracy
            3. Test edge cases or different inputs if appropriate
            4. Provide clear feedback on correctness, efficiency, and best practices

            EXECUTION ENVIRONMENT:
            - All code MUST be executed in isolated Docker containers via the run_code tool
            - Docker containers have strict resource limits (memory, CPU, processes)
            - Docker containers have no network access for security
            - Docker containers use read-only filesystems except for output directories
            - Execution timeout is enforced to prevent infinite loops

            Remember:
            - You DO NOT write code - you only execute and test
            - You MUST ONLY use Docker containers for execution
            - ALWAYS verify the mathematical accuracy of results
            - Be specific about any errors or issues you find
            - Suggest possible fixes but don't implement them yourself

            The group relies on you to verify that code works as intended and produces accurate results. Be thorough in your testing and clear in your feedback.""",
            
            "Manager": """You are a conversation manager. Your responsibilities include:
            1. Evaluate if a complete answer has been provided for the user's question
            2. Make sure important points aren't missing or misleading
            3. If something is missing or off-topic, explicitly state what needs to be addressed
            4. Synthesize all relevant information into a final answer that directly addresses the original query
            5. Confirm: "Does this fully answer your question about [topic]?"
            6. Summarize the conversation and provide a final answer.
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
