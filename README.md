# Multi-Agent LLM Chat with GroupChat Functionality

A Streamlit application that leverages LangGraph to create multi-agent conversations with local LLM models served by Ollama. This application allows you to create and configure multiple AI agents with different personalities and capabilities, then have them collaborate in a group chat to solve problems.

> 📘 **For Developers**: For technical details and implementation notes, see [LLM_CONTEXT.md](LLM_CONTEXT.md)  
> 🔧 **New Users**: For detailed installation instructions across all platforms, see [INSTALL.md](INSTALL.md)

## Features

- **Multiple Agent Types**: Create specialized agents (Assistant, Researcher, Coder, Math Expert, Critic, or Custom)
- **Custom Model Integration**: Pull and configure custom Ollama models directly from the UI
- **Consensus-Based Discussion**: Agents can engage in multi-round discussions until reaching consensus
- **Group Chat Manager**: A designated agent evaluates when consensus has been reached
- **Local LLM Integration**: Uses Ollama to run models completely locally
- **Agent Memory**: Conversation history for contextual responses
- **Persistent Agents & Group Chats**: Agents and group chat configurations are automatically saved and can be reused across sessions
- **Configuration Management**: Save and load agent configurations
- **Conversation History**: All conversations are automatically saved to the 'conversations' folder and can be reloaded later
- **Dynamic Tools**: Different tools assigned based on agent type
- **Debug Mode**: Enable detailed logging and performance metrics
- **Secure Docker Execution**: All code is executed exclusively in isolated Docker containers with advanced security controls
- **Enhanced Error Reporting**: Comprehensive error detection and reporting for Python exceptions and other execution issues
- **Real-time Response Streaming**: See agent responses as they're generated for better interactivity
- **Result Verification**: Code Runner agent verifies mathematical results against known values
- **Persistent Workspace System**: Each group chat has its own workspace with code, data, and output folders

## System Architecture

```mermaid
graph TD
    User[User] <--> |Interacts with| WebUI[Streamlit Web UI]
    WebUI <--> |Manages| Config[Configuration Manager]
    WebUI <--> |Creates/Selects| Agents[Agent Factory]
    WebUI <--> |Sets up| GroupChat[Group Chat]
    WebUI <--> |Views/Loads| Convos[Conversation Manager]
    WebUI <--> |Toggles| Debug[Debug Mode]
    WebUI <--> |Browses| Workspace[Workspace Manager]
    
    Config --> |Loads/Saves| ConfigFiles[(Config Files)]
    Agents --> |Uses| LLMs[LLM Models]
    GroupChat --> |Coordinates| Agents
    GroupChat --> |Maintains| Context[Persistent Context]
    GroupChat --> |Processes| Messages[Message History]
    Context --> |Enables| FollowUp[Follow-up Questions]
    Convos --> |Stores| ConvoFiles[(Conversation Files)]
    Workspace --> |Manages| WorkFiles[Code, Data, Output]
    
    LLMs <--> |API Calls| Ollama[Ollama Service]
    
    subgraph Execution Environment
        Docker[Docker Container] --> |Executes| Code[User Code]
        Docker --> |Enforces| Security[Security Controls]
        Docker --> |Captures| Output[Execution Results]
        Docker --> |Verifies| Results[Result Accuracy]
    end
    
    subgraph Local Environment
        ConfigFiles
        ConvoFiles
        WorkFiles
        Ollama
    end
    
    Debug --> |Shows| DebugInfo[System Information]
    Debug --> |Displays| Timing[Performance Metrics]
```

## Prerequisites

- Ollama installed and running
- Python >= 3.13
- uv >= 0.5.0
- Docker >= 25.0.2 (Colima recommended for macOS users)
- VS Code or another Python IDE (recommended)

For detailed installation instructions for all prerequisites on macOS, Linux, and Windows, please refer to the [INSTALL.md](INSTALL.md) guide.

## Setup

### 1. Ensure Ollama is running

```bash
ollama serve
```

### 2. Pull recommended models

```bash
ollama pull llama3
ollama pull mistral
ollama pull codellama
```

### 3. Install dependencies

Please refer to the [INSTALL.md](INSTALL.md) guide for detailed installation instructions, including setting up virtual environments and installing dependencies.

## Running the Application

Use the following command to run the application. This will automatically set up a virtual environment and install all required packages before running:

```bash
uv run streamlit run src/app.py
```

To stop the application:
```bash
pkill -f "streamlit run" || echo "No running Streamlit processes found"
```

### Convenience Scripts

For easier startup and shutdown, you can use the provided scripts:

```bash
# Start the application
./run.sh

# Stop the application
./stop.sh
```

## Using the Application

1. **Connect to Ollama**: First, ensure Ollama is running and click "Connect to Ollama" in the sidebar
2. **Pull Custom Models** (Optional): Use the "Pull Custom Models" section in the sidebar to add new Ollama models
   - Enter the model name as it appears in Ollama (e.g., `llama3:latest`, `wizardcoder:python`)
   - Add optional display name, description, and tags for better organization
   - The model will be pulled from Ollama and added to models.json for future use
3. **Create Agents**: Configure and create agents with different specialties
4. **Setup Group Chat**: Select multiple agents to participate in a group chat
   - **Enable Consensus Mode**: Check "Require Consensus" to have agents discuss until agreement
   - **Set Discussion Rounds**: Choose how many rounds of discussion to allow (1-99)
   - **Add a Critic or Manager**: For best results in consensus mode, include a Critic or create a Manager agent
5. **Chat Interface**: Interact with your agents through the main chat interface
6. **Access Saved Conversations**: Open the Group Chat Management section and go to the Conversations tab to browse, filter, and reload past conversations
7. **Save Configuration**: Save your agent configurations for future use

## Agent Types

- **Assistant**: General-purpose helpful assistant
- **Researcher**: Specializes in gathering and analyzing information
- **Coder**: Focuses on programming and code-related tasks
- **Math Expert**: Specializes in mathematical problem solving
- **Critic**: Provides critical analysis and feedback
- **Code Runner**: Executes and tests code securely in Docker containers
- **Custom**: Create your own agent with a custom prompt

## Consensus-Based Discussions

The application supports a powerful consensus mechanism that allows agents to engage in multi-round discussions:

```mermaid
sequenceDiagram
    participant User
    participant Manager
    participant Agent1
    participant Agent2
    participant Agent3
    participant Context
    
    User->>Context: Ask question
    Context->>Manager: Forward question with history
    
    par Forward to agents with context
        Manager->>Agent1: Question + prior context
        Manager->>Agent2: Question + prior context
        Manager->>Agent3: Question + prior context
    end
    
    Note over Agent1,Agent3: Each agent has access to<br/>all previous conversation context
    
    Agent1-->>Context: Initial response
    Agent2-->>Context: Initial response
    Agent3-->>Context: Initial response
    
    loop Until consensus or max rounds
        Manager->>Manager: Evaluate consensus
        alt Consensus not reached
            Manager->>Context: Request refinement
            Context->>Agent1: Request with all previous responses
            Context->>Agent2: Request with all previous responses
            Context->>Agent3: Request with all previous responses
            
            Agent1-->>Context: Refined response
            Agent2-->>Context: Refined response
            Agent3-->>Context: Refined response
        else Consensus reached
            Manager-->>Context: Final consensus reached
            Context-->>User: Final consensus response
        end
    end
    
    Note over Manager: If max rounds reached<br>without consensus
    
    Manager-->>Context: Select best response
    Context-->>User: Best response with<br>explanation
    
    Note over Context: Chat context persists for<br>follow-up questions
```

- **Discussion Rounds**: Agents refine their thoughts over multiple rounds of conversation
- **Consensus Evaluation**: A Manager or Critic agent evaluates when consensus has been reached
- **Adaptive Responses**: Agents modify their responses based on other agents' input
- **Maximum Round Limit**: Set a cap on discussion rounds (1-99) before concluding

This approach is particularly effective for complex questions that benefit from multiple perspectives and collaborative problem-solving. The consensus feature works best with at least 3 agents including a Critic or Manager agent.

## Advanced Features

- **Custom Prompts**: Define your own agent personalities
- **Tool Integration**: Agents have access to different tools based on their type
- **Docker Code Execution**: Safely test and run code in isolated containers
- **Performance Metrics**: Track response times in debug mode

## Conversation Management

The application includes a robust conversation management system:

```mermaid
graph TD
    Chat[Chat Interface] -->|User Sends Message| Process[Process Message]
    Process -->|Maintain Context| Context[Persistent Context]
    Context -->|Provide History| Agents[Agent Processing]
    Agents -->|Real-time Stream| Stream[Streaming Responses]
    Stream -->|Display| UI[User Interface]
    
    Process -->|Agent Responses| Update[Update Chat History]
    Update -->|Auto-Save| Save[Save Conversation]
    Save -->|JSON File| Storage[(Conversations Folder)]
    
    subgraph History Management
        UI_Tab[Conversations Tab] -->|Browse| List[List Conversations]
        List -->|Read| Storage
        UI_Tab -->|Filter| Filter[Filter Conversations]
        UI_Tab -->|Select| View[View Conversation]
        View -->|Load from| Storage
        UI_Tab -->|Reload| Reload[Reload Conversation]
        Reload -->|Restore to| Chat
    end
    
    subgraph Debug Features
        DebugMode[Debug Mode] -->|Enable| Metrics[Performance Metrics]
        DebugMode -->|Show| Config[Configuration Details]
        DebugMode -->|Display| DockerStatus[Docker Status]
        DebugMode -->|Expose| WorkspaceInfo[Workspace Information]
    end
    
    Storage -->|Structured Format| Format["JSON Structure:<br>- Metadata<br>- Messages<br>- Timestamps<br>- Agent Info<br>- Context History"]
```

- **Automatic Saving**: All conversations are automatically saved as JSON files in the 'conversations' folder
- **Conversation Browser**: Browse and filter past conversations by group chat name
- **Metadata Storage**: Each conversation file includes metadata about participants and settings
- **Conversation Reloading**: Reload any past conversation to continue where you left off
- **Preview Feature**: Preview conversation content before loading

All saved conversations are accessible through the "Conversations" tab in the Group Chat Management section, where you can filter, browse, and reload past discussions.

## Conversation Context Flow

The system maintains conversation context between user interactions, allowing for natural follow-up questions:

```mermaid
sequenceDiagram
    participant User
    participant GroupChat
    participant PersistentContext
    participant Agents
    
    User->>GroupChat: Initial question
    GroupChat->>PersistentContext: Store question
    PersistentContext->>Agents: Forward question
    Agents->>PersistentContext: Store responses
    PersistentContext->>GroupChat: Deliver responses
    GroupChat->>User: Show responses
    
    Note over PersistentContext: Context maintained between interactions
    
    User->>GroupChat: Follow-up question
    GroupChat->>PersistentContext: Add to existing context
    PersistentContext->>Agents: Forward question with full history
    Note over Agents: Agents can reference prior questions & answers
    Agents->>PersistentContext: Store new responses
    PersistentContext->>GroupChat: Deliver responses with context
    GroupChat->>User: Show contextual responses
    
    Note over User,GroupChat: This continues for multiple interactions
```

- **Context Preservation**: All user questions and agent responses are maintained in persistent memory
- **Reference Resolution**: Follow-up questions can reference earlier parts of the conversation
- **Contextual Understanding**: Agents can understand phrases like "it", "that", or "the code" in context
- **Session Persistence**: Context is maintained even if the connection is temporarily lost

## Docker Code Runner

The application includes a Code Runner agent that safely executes code inside Docker containers with improved error reporting and result verification:

```mermaid
flowchart TD
    User[User] -->|"Submit Code"| Agent[Code Runner Agent]
    Agent -->|"Analyze Code"| CheckCode[Validate Code Safety]
    
    subgraph "Workspace System"
        CheckCode -->|"Save to Workspace"| CodeDir[code/ Directory]
        CodeDir -->|"Read Input"| DataDir[data/ Directory]
        CodeDir -->|"Write Results"| OutputDir[output/ Directory]
    end
    
    Workspace[(Persistent Workspace)] -->|"Contains"| WorkspaceSystem
    
    CodeDir -->|"Mount Read-Only"| Docker[Docker Container]
    DataDir -->|"Mount Read-Only"| Docker
    OutputDir -->|"Mount Read-Write"| Docker
    
    Docker -->|"Isolated Execution"| ExecProcess[Execution Process]
    
    subgraph "Security Controls"
        NS[No Network Access]
        MEM[Memory Limits: 256MB]
        CPU[CPU Limits: 0.5 cores]
        RO[Read-Only Filesystem]
        TO[Timeout: 10 seconds]
        CAP[Dropped Capabilities]
        SEC[Secure Execution Environment]
    end
    
    Security -->|"Enforce"| Docker
    
    ExecProcess -->|"Capture Output"| Results[Raw Results]
    Results -->|"Error Detection"| ErrorCheck{Has Errors?}
    
    ErrorCheck -->|"Yes"| ErrorAnalysis[Error Analysis]
    ErrorCheck -->|"No"| SuccessCheck[Success Validation]
    
    ErrorAnalysis -->|"Python Exception Detection"| FormatError[Format Error Report]
    SuccessCheck -->|"Mathematical Validation"| ResultCheck{Results Accurate?}
    
    ResultCheck -->|"Yes"| FormatSuccess[Format Success Report]
    ResultCheck -->|"No"| Correction[Add Correction Note]
    
    Correction -->|"Compare with Expected"| FormatSuccess
    FormatError -->|"Detailed Feedback"| User
    FormatSuccess -->|"Formatted Response"| User
```

### Features

- **Supported Languages**: Python, JavaScript, and Go
- **Secure Execution**: All code runs in isolated, constrained Docker containers
- **Security Controls**: No network access, limited resources, read-only filesystem
- **Runtime Management**: List and terminate running code executions
- **Enhanced Error Detection**: Comprehensive detection of Python exceptions and other execution issues
- **Result Verification**: Mathematical results are verified against known values (Pi, e, etc.)
- **Detailed Feedback**: Execution results include accuracy checks and suggested improvements
- **Real-time Streaming**: See execution results as they're generated

### Workspace System

Each group chat has a persistent workspace with three directories:

- **code/**: For source code files that can be executed
- **data/**: For input data, configuration files, and other resources
- **output/**: For execution results and generated outputs

The workspace system ensures that files persist between conversations, allowing for iterative development and testing.

### Requirements

- Docker must be installed and running on your system (Colima recommended for macOS users)
- For macOS users, Colima provides better performance and no licensing restrictions:
  ```bash
  # Install and configure Colima with appropriate resources
  brew install colima docker docker-compose
  colima start --cpu 4 --memory 8 --disk 20
  ```
- The application automatically detects and uses your Docker installation
- All paths are dynamically managed by the workspace system for maximum portability

### Usage

1. Create a Code Runner agent in the Agent Configuration section
2. Include the agent in a group chat
3. Submit code to run by asking the agent to execute it
4. Receive results, error analysis, and verification of mathematical accuracy