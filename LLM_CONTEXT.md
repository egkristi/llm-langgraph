# AI/LLM Coding Instructions

## Project Overview
App based on streamlit and uv that use langchain with multiple agents served by ollama locally. 
Everything should run offline locally once set up and models are pulled from ollama.
In the web ui the user can configure the controls for langgraph multi-agent chat.

## Technology Stack
- **Python**: 3.13+ (or your version)
- **Package Manager**: uv
- **Framework**: Streamlit
- **LLM Framework**: LangGraph, ollama

# Set up project
```bash
uv init llm-langgraph2 && cd llm-langgraph2
uv add streamlit langchain ollama
```
# Features

- Preset Agents: Pre-configured agents for common tasks
- Full Agent Creation: Complete ReAct agent with proper prompt formatting
- Agents independent of LLM-models, can be configured to use different models
- Tool Management: Dynamic tool creation based on agent type
- Memory Management: Conversation history for each agent
- Agent Lifecycle: Create, update, delete, and list agents
- Error Handling: Robust error handling throughout
- debug mode switch that enables verbose logging and feedback in ui
- Dynamic Tools: Agents get different tools based on their purpose
- Memory Persistence: Each agent can maintain its own conversation history
- Model Caching: Reuses LLM instances for efficiency
- Flexible Configuration: Easy to extend with new agent types
- Proper ReAct Format: Follows the Thought/Action/Observation pattern

### Additional Features:

- Conversation saving
- Configuration import/export
- Response timing
- Error handling
- Auto-save option

### Ollama Configuration:

- Connection settings
- Performance parameters
- Set up ollama servers locally per available model
- Ollama Integration: Connection testing and model discovery
- Common Ollama models
- Functionality for pulling new models from ollama in ui

### Persistence:

- Save/load settings from files
- JSON serialization

# Running app
```bash
uv run streamlit run src/app.py
```