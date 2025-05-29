# Installation Guide for LLM-LangGraph

This guide provides detailed instructions for installing all prerequisites needed to run the LLM-LangGraph application on macOS, Linux, and Windows.

## System Requirements

- **RAM**: Minimum 8GB, recommended 16GB or more (for running LLMs)
- **Disk Space**: At least 10GB free space (for models and application)
- **Internet Connection**: Required for the initial setup and model downloads

## Prerequisites

### 1. Git

Git is needed to clone the repository and manage version control.

#### macOS

You can install Git via Homebrew:
```bash
# First install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Git
brew install git
```

Or download the installer from [git-scm.com](https://git-scm.com/download/mac).

#### Linux

For Debian/Ubuntu:
```bash
sudo apt-get update
sudo apt-get install git
```

For Fedora:
```bash
sudo dnf install git
```

For other distributions, consult your package manager.

#### Windows

1. Download the Git installer from [git-scm.com](https://git-scm.com/download/win)
2. Run the installer, using the default options (or customize as needed)
3. Verify installation by opening Git Bash and running `git --version`

### 2. Python 3.13+

The application requires Python 3.13 or higher.

#### macOS

Using Homebrew:
```bash
brew install python@3.13
```

#### Linux

Most Linux distributions don't package Python 3.13 yet. You can install it from source:

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev

# Download and compile Python 3.13
wget https://www.python.org/ftp/python/3.13.0/Python-3.13.0.tgz
tar -xf Python-3.13.0.tgz
cd Python-3.13.0
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall

# Verify installation
python3.13 --version
```

#### Windows

1. Download the Python 3.13 installer from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. Make sure to check "Add Python to PATH"
4. Verify installation by opening Command Prompt and running `python --version`

### 3. uv Package Manager

uv is a Python packaging tool that's required for dependency management.

#### All Platforms (macOS, Linux, Windows)

Install uv using pip:

```bash
pip install uv
```

Or install as per the official instructions:

```bash
curl -sSf https://raw.githubusercontent.com/astral-sh/uv/main/install.sh | bash
```

For Windows, you can use:

```bash
curl.exe -sSf https://raw.githubusercontent.com/astral-sh/uv/main/install.ps1 | powershell
```

Verify installation:
```bash
uv --version
```

### 4. Ollama

Ollama is required to run LLMs locally.

#### macOS

```bash
curl -fsSL https://ollama.com/download/ollama-darwin -o ollama
chmod +x ollama
sudo mv ollama /usr/local/bin/
```

Or download from [ollama.ai](https://ollama.ai/download).

#### Linux

```bash
curl -fsSL https://ollama.com/download/ollama-linux-amd64 -o ollama
chmod +x ollama
sudo mv ollama /usr/local/bin/
```

Or follow the instructions at [ollama.ai](https://ollama.ai/download).

#### Windows

1. Download the Ollama installer from [ollama.ai](https://ollama.ai/download)
2. Run the installer
3. Follow the installation prompts

### 5. Docker

Docker is required for code execution in secure containers.

#### macOS

1. Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
2. Open Docker Desktop after installation
3. Verify installation: `docker --version`

#### Linux

For Ubuntu/Debian:
```bash
# Install prerequisites
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository
echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to the docker group (to run Docker without sudo)
sudo usermod -aG docker $USER

# Activate the changes to groups
newgrp docker
```

#### Windows

1. Install [WSL2](https://docs.microsoft.com/en-us/windows/wsl/install) (Windows Subsystem for Linux)
2. Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
3. Ensure "Use WSL 2 based engine" is checked in Docker Desktop settings
4. Start Docker Desktop
5. Verify installation: `docker --version`

## Installation Steps

After installing all prerequisites, follow these steps to set up and run the application:

### 1. Clone the Repository

```bash
git clone https://github.com/egkristi/llm-langgraph.git
cd llm-langgraph
```

### 2. Install Dependencies

```bash
uv init .
uv pip install -r requirements.txt
```

### 3. Start Ollama

Start the Ollama service:

```bash
ollama serve
```

### 4. Pull Required Models

```bash
ollama pull llama3
ollama pull devstral
ollama pull mistral
ollama pull codellama
```

### 5. Run the Application

```bash
./run.sh
```

Or on Windows:

```bash
.\run.bat
```

## Troubleshooting

### Common Issues

#### Docker Permissions on Linux

If you encounter permission issues with Docker:

```bash
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
```

#### Ollama Model Download Issues

If you have trouble downloading models:

1. Ensure you have sufficient disk space
2. Check your internet connection
3. Try running with sudo: `sudo ollama pull modelname`

#### Python Version Conflicts

If you have multiple Python versions and encounter issues:

```bash
# Create a virtual environment with the correct Python version
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### WSL2 Issues on Windows

If Docker has issues with WSL2:

1. Ensure WSL2 is properly installed: `wsl --status`
2. Update WSL2: `wsl --update`
3. Restart your computer

#### Memory Issues with Large Models

If models fail to load due to memory constraints:

1. Close unnecessary applications
2. Use smaller models (e.g., mistral instead of llama3)
3. Configure Ollama with lower memory usage: create a `.env` file with `OLLAMA_MEMORY_LIMIT=4GB`

## Next Steps

Once installation is complete, refer to the [README.md](README.md) for usage instructions.

For further assistance, please open an issue on the project's GitHub repository.
