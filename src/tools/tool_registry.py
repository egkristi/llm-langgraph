from typing import Dict, List, Any, Callable
from langchain_core.tools import BaseTool, tool

# Import manager-specific tools
from tools.manager_tools import analyze_question, validate_response, identify_gaps, summarize_responses

# Import Docker code runner tools
from tools.docker_code_runner import run_code, list_running_code, kill_running_code, docker_available

# Import workspace tools
from tools.workspace_tools import list_workspace_files, read_workspace_file, save_workspace_file, get_workspace_details

# Dictionary to store registered tools
_tools: Dict[str, List[BaseTool]] = {}

@tool
def search_tool(query: str) -> str:
    """Search for information based on a query."""
    return f"Simulated search results for: {query}"

@tool
def calculator_tool(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"

@tool
def code_analyzer_tool(code: str) -> str:
    """Analyze code and provide feedback."""
    return f"Simulated code analysis: Code looks good with minor optimizations possible."

@tool
def fact_checker_tool(statement: str) -> str:
    """Check if a statement is factually correct."""
    return f"Fact check for '{statement}': This would require additional verification."

# Register default tools
_tools["default"] = [search_tool]
_tools["Assistant"] = [search_tool, fact_checker_tool]
_tools["Researcher"] = [search_tool, fact_checker_tool]
_tools["Coder"] = [search_tool, code_analyzer_tool, calculator_tool]
_tools["Math Expert"] = [calculator_tool]
_tools["Critic"] = [fact_checker_tool]
_tools["Manager"] = [analyze_question, validate_response, identify_gaps, summarize_responses]

# Create and register a new Code Runner agent type
_tools["Code Runner"] = [run_code, list_running_code, kill_running_code, code_analyzer_tool, search_tool, 
                       list_workspace_files, read_workspace_file, save_workspace_file, get_workspace_details]

def register_tool(tool_obj: BaseTool, agent_types: List[str] = ["default"]):
    """
    Register a tool for use with specific agent types.
    
    Args:
        tool_obj: The tool object to register
        agent_types: List of agent types that should have access to this tool
    """
    for agent_type in agent_types:
        if agent_type not in _tools:
            _tools[agent_type] = []
        _tools[agent_type].append(tool_obj)

def get_tools_for_agent_type(agent_type: str) -> List[BaseTool]:
    """
    Get all tools available for a specific agent type.
    
    Args:
        agent_type: The type of agent
        
    Returns:
        List of tools available for the agent type
    """
    # Return tools for the specific agent type and default tools
    specific_tools = _tools.get(agent_type, [])
    default_tools = _tools.get("default", [])
    
    # Combine tools - but don't use set() as tools aren't hashable
    all_tools = []
    tool_names = set()
    
    # Add tools while tracking names to avoid duplicates
    for tool in specific_tools + default_tools:
        if tool.name not in tool_names:
            all_tools.append(tool)
            tool_names.add(tool.name)
    
    return all_tools
