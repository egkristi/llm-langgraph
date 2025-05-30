# Installation Guide for LLM-LangGraph

This guide provides detailed instructions for installing all prerequisites needed to run the LLM-LangGraph application on macOS, Linux, and Windows.

## Quick Installation with Homebrew (macOS)

If you're using macOS, you can install most dependencies with Homebrew for a streamlined setup:

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Make sure Homebrew is in your PATH
eval "$(/opt/homebrew/bin/brew shellenv)"

# Install all required dependencies
brew install git python@3.13 ollama
brew tap astral-sh/tap
brew install astral-sh/tap/uv

# Choose one Docker provider:
# Option 1: Colima (RECOMMENDED - lightweight, no licensing restrictions)
brew install colima docker

# Configure Colima with sufficient resources for LLMs
colima start --cpu 4 --memory 8 --disk 20

# Option 2: Docker Desktop
# brew install --cask docker

# Option 3: OrbStack (alternative with UI)
# brew install --cask orbstack

# Install VS Code (recommended IDE)
brew install --cask visual-studio-code

# Clone the repository
git clone https://github.com/egkristi/llm-langgraph.git
cd llm-langgraph

# Create and activate a virtual environment (recommended)
python3.13 -m venv venv
source venv/bin/activate

# Install Python dependencies
uv pip install -r requirements.txt

# Start Ollama and pull required models
ollama serve & # Run in background
sleep 5 # Wait for Ollama to start
ollama pull llama3
ollama pull mistral
ollama pull codellama

# Run the application
./run.sh
```

If you prefer step-by-step installation, follow the detailed instructions below.

## Quick Installation with apt (Debian/Ubuntu Linux)

If you're using a Debian-based Linux distribution like Ubuntu, you can install most dependencies with apt for a streamlined setup:

```bash
#!/bin/bash
# Run this script with sudo

# Update package lists
apt update

# Install Git
apt install -y git

# Install dependencies for building Python
apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
    libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev \
    wget libbz2-dev

# Install Docker
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to the docker group
usermod -aG docker $USER

# Download and install Python 3.13
cd /tmp
wget https://www.python.org/ftp/python/3.13.0/Python-3.13.0.tgz
tar -xf Python-3.13.0.tgz
cd Python-3.13.0
./configure --enable-optimizations
make -j$(nproc)
make altinstall

# Verify Python installation
python3.13 --version

# Install uv package manager
pip3.13 install uv

# Download and install Ollama
curl -fsSL https://ollama.com/download/ollama-linux-amd64 -o ollama
chmod +x ollama
mv ollama /usr/local/bin/

# Install VS Code (recommended IDE)
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
rm -f packages.microsoft.gpg
apt update
apt install -y code

# Clone the repository (as normal user, not root)
echo -e "\nNow run the following commands as a regular user (not root):\n"
echo "git clone https://github.com/egkristi/llm-langgraph.git"
echo "cd llm-langgraph"
echo "python3.13 -m venv venv"
echo "source venv/bin/activate"
echo "uv pip install -r requirements.txt"
echo "ollama serve &  # Start Ollama in the background"
echo "sleep 5  # Wait for Ollama to start"
echo "ollama pull llama3"
echo "ollama pull mistral"
echo "ollama pull codellama"
echo "./run.sh"
```

You can save this script as `install-llm-langgraph.sh`, make it executable with `chmod +x install-llm-langgraph.sh`, and run it with `sudo ./install-llm-langgraph.sh`.

Note that you should run the final repository cloning and application startup commands as a regular user, not as root.

## Quick Installation with winget (Windows)

If you're using Windows, you can install most dependencies with winget for a streamlined setup. 

[winstall.app](https://winstall.app/) is a helpful web interface for generating winget commands and creating installation scripts:

- **Create installation bundles**: Select multiple applications and generate a single script to install them all
- **Search for packages**: Find applications by name or browse categories
- **Share installation scripts**: Generate links to share your configuration with others

For LLM-LangGraph, you can use this [pre-configured bundle](https://winstall.app/bundle/llm-langgraph) to install Git, Python 3.13, and Docker Desktop in one go.

Here's the complete installation script:

```powershell
# Open PowerShell as Administrator

# Install Git
winget install -e --id Git.Git

# Install Python 3.13
winget install -e --id Python.Python.3.13

# Install Docker Desktop
winget install -e --id Docker.DockerDesktop

# Install Windows Terminal (recommended for a better command-line experience)
winget install -e --id Microsoft.WindowsTerminal

# Install VS Code (recommended IDE)
winget install -e --id Microsoft.VisualStudioCode

# Make sure Python is in your PATH
Refresh-Environment  # You may need to restart PowerShell

# Install uv package manager
pip install uv

# Download and install Ollama
$ollamaUrl = "https://ollama.com/download/ollama-windows-amd64.zip"
$ollamaZipPath = "$env:TEMP\ollama.zip"
$ollamaExtractPath = "$env:USERPROFILE\ollama"

Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaZipPath
Expand-Archive -Path $ollamaZipPath -DestinationPath $ollamaExtractPath -Force

# Add Ollama to PATH
$env:PATH += ";$ollamaExtractPath"
[Environment]::SetEnvironmentVariable('PATH', $env:PATH, 'User')

# Clone the repository
git clone https://github.com/egkristi/llm-langgraph.git
cd llm-langgraph

# Create and activate a virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate

# Install Python dependencies
uv pip install -r requirements.txt

# Start Ollama and pull required models
Start-Process ollama -ArgumentList "serve" -NoNewWindow
Start-Sleep -Seconds 5  # Wait for Ollama to start
ollama pull llama3
ollama pull mistral
ollama pull codellama

# Run the application
.\run.bat
```

After running these commands, you should have a fully functional LLM-LangGraph environment on Windows.

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

**Option 1: Debian/Ubuntu (apt)**
```bash
sudo apt update
sudo apt install -y git

# Verify installation
git --version
```

**Option 2: Fedora/RHEL (dnf)**
```bash
sudo dnf install -y git

# Verify installation
git --version
```

**Option 3: Arch Linux (pacman)**
```bash
sudo pacman -S git

# Verify installation
git --version
```

For other distributions, consult your package manager.

#### Windows

**Option 1: Using winget (Recommended)**
```powershell
winget install -e --id Git.Git
```
You can also generate this command via [winstall.app](https://winstall.app/apps/Git.Git)

**Option 2: Manual Installation**
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

This will install Python 3.13 and set up the necessary symlinks. You can verify the installation with:
```bash
python3.13 --version
```

#### Linux

**Option 1: Debian/Ubuntu (building from source)**

Most Linux distributions don't package Python 3.13 yet, so you'll need to build from source:

```bash
# Install dependencies
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
    libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev

# Download and compile Python 3.13
cd /tmp
wget https://www.python.org/ftp/python/3.13.0/Python-3.13.0.tgz
tar -xf Python-3.13.0.tgz
cd Python-3.13.0
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall

# Verify installation
python3.13 --version

# Create symlinks (optional)
sudo ln -sf /usr/local/bin/python3.13 /usr/local/bin/python3
sudo ln -sf /usr/local/bin/pip3.13 /usr/local/bin/pip3
```

**Option 2: Using PPA (Ubuntu only)**

For Ubuntu users, you can try a PPA if available:

```bash
# Add deadsnakes PPA (may or may not have 3.13 yet)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# Verify installation
python3.13 --version
```

**Option 3: Fedora/RHEL**

Fedora may have Python 3.13 in its repositories:

```bash
sudo dnf install python3.13

# Verify installation
python3.13 --version
```

#### Windows

**Option 1: Using winget (Recommended)**
```powershell
# Install Python 3.13
winget install -e --id Python.Python.3.13

# Verify installation
python --version
```
You can also generate this command via [winstall.app](https://winstall.app/apps/Python.Python.3.13)

**Option 2: Manual Installation**
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

**Option 1: Using Homebrew (Recommended)**
```bash
brew install ollama
```

**Option 2: Manual Installation**
```bash
curl -fsSL https://ollama.com/download/ollama-darwin -o ollama
chmod +x ollama
sudo mv ollama /usr/local/bin/
```

Or download from [ollama.ai](https://ollama.ai/download).

#### Linux

**Option 1: Debian/Ubuntu (direct download)**
```bash
# Download and install Ollama
curl -fsSL https://ollama.com/download/ollama-linux-amd64 -o ollama
chmod +x ollama
sudo mv ollama /usr/local/bin/

# Verify installation
ollama --version
```

**Option 2: Using apt repository (if available)**
```bash
# Add Ollama's repository (when available)
curl -fsSL https://ollama.ai/repo/ollama.gpg | sudo tee /usr/share/keyrings/ollama-archive-keyring.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/ollama-archive-keyring.gpg] https://ollama.ai/repo/apt stable main" | sudo tee /etc/apt/sources.list.d/ollama.list > /dev/null
sudo apt update
sudo apt install -y ollama

# Verify installation
ollama --version
```

**Option 3: Build from source**
```bash
# Install Go first (required to build Ollama)
sudo apt update
sudo apt install -y golang-go git

# Clone and build Ollama
git clone https://github.com/ollama/ollama
cd ollama
go build
sudo mv ollama /usr/local/bin/

# Verify installation
ollama --version
```

For more information, visit [ollama.ai](https://ollama.ai/download).

#### Windows

**Option 1: Using PowerShell**
```powershell
# Download and install Ollama
$ollamaUrl = "https://ollama.com/download/ollama-windows-amd64.zip"
$ollamaZipPath = "$env:TEMP\ollama.zip"
$ollamaExtractPath = "$env:USERPROFILE\ollama"

Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaZipPath
Expand-Archive -Path $ollamaZipPath -DestinationPath $ollamaExtractPath -Force

# Add Ollama to PATH
$env:PATH += ";$ollamaExtractPath"
[Environment]::SetEnvironmentVariable('PATH', $env:PATH, 'User')

# Verify installation
& "$ollamaExtractPath\ollama.exe" --version
```

**Option 2: Manual Installation**
1. Download the Ollama installer from [ollama.ai](https://ollama.ai/download)
2. Run the installer
3. Follow the installation prompts

### 5. Docker

Docker is required for code execution in secure containers.

#### macOS

**Option 1: Colima (RECOMMENDED)**

Colima is a lightweight Docker Desktop alternative that doesn't require a license for commercial use and is ideal for LLM-LangGraph:

```bash
# Install Colima and Docker CLI using Homebrew
brew install colima docker docker-compose

# Start Colima with optimized settings for LLM workloads
colima start --cpu 4 --memory 8 --disk 20

# Verify installation
docker --version
docker run hello-world
```

**Colima Configuration Options:**

```bash
# View all configuration options
colima help start

# Start with specific Kubernetes version (if needed)
colima start --kubernetes

# Start with a specific VM runtime (default is Lima)
colima start --runtime docker

# Use a custom Docker socket location
colima start --socket $HOME/.colima/docker.sock

# Start with specific CPU architecture (for M1/M2 Macs)
colima start --arch aarch64

# For using Colima with Docker Compose
export DOCKER_HOST="unix://${HOME}/.colima/docker.sock"
```

**Colima Management Commands:**

```bash
# Check Colima status
colima status

# Stop Colima
colima stop

# Delete Colima instance
colima delete

# Create a different instance (useful for different projects)
colima start myproject --cpu 2 --memory 4
```

**Option 2: Docker Desktop**

1. Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
2. Open Docker Desktop after installation
3. Verify installation: `docker --version`

**Option 3: OrbStack (Another Docker alternative)**

OrbStack is another Docker alternative with a friendly UI:

```bash
# Install OrbStack using Homebrew
brew install --cask orbstack

# Launch OrbStack from Applications folder and follow the setup
# Or start from the terminal
open -a OrbStack

# Verify installation
docker --version
```

#### Linux

**Option 1: Debian/Ubuntu (apt)**
```bash
# Install prerequisites
sudo apt update
sudo apt install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository
echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to the docker group (to run Docker without sudo)
sudo usermod -aG docker $USER

# Activate the changes to groups
newgrp docker

# Verify installation
docker --version
docker run hello-world
```

**Option 2: Fedora/RHEL (dnf)**
```bash
# Add Docker repository
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo

# Install Docker
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to the docker group
sudo usermod -aG docker $USER

# Verify installation
docker --version
```

**Option 3: Using Docker's Convenience Script (any Linux)**
```bash
# Install Docker using the convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group
sudo usermod -aG docker $USER

# Verify installation
docker --version
```

#### Windows

**Option 1: Using winget (Recommended)**
```powershell
# First make sure WSL2 is installed
wsl --install

# Install Docker Desktop
winget install -e --id Docker.DockerDesktop

# Start Docker Desktop and verify installation
docker --version
```
You can also generate this command via [winstall.app](https://winstall.app/apps/Docker.DockerDesktop)

**Option 2: Manual Installation**
1. Install [WSL2](https://docs.microsoft.com/en-us/windows/wsl/install) (Windows Subsystem for Linux)
2. Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
3. Ensure "Use WSL 2 based engine" is checked in Docker Desktop settings
4. Start Docker Desktop
5. Verify installation: `docker --version`

### 6. Code Editor / IDE

While not strictly required, a good code editor or IDE will greatly enhance your development experience with LLM-LangGraph.

#### Visual Studio Code (Recommended)

VS Code is a lightweight but powerful code editor with excellent Python support.

**macOS Installation:**
```bash
# Using Homebrew
brew install --cask visual-studio-code

# Verify installation
code --version
```

**Linux Installation:**

**Option 1: Debian/Ubuntu (apt)**
```bash
# Add Microsoft's GPG key
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
rm -f packages.microsoft.gpg

sudo apt update
sudo apt install -y code
```

**Option 2: Fedora/RHEL/CentOS**
```bash
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'

# For dnf-based systems (Fedora)
sudo dnf install -y code

# For yum-based systems (older RHEL/CentOS)
# sudo yum install -y code
```

**Windows Installation:**
```powershell
# Using winget
winget install -e --id Microsoft.VisualStudioCode

# Verify installation
code --version
```
You can also generate this command via [winstall.app](https://winstall.app/apps/Microsoft.VisualStudioCode)

**Recommended VS Code Extensions for Python Development:**

After installing VS Code, add these helpful extensions:

```bash
# Python extension pack (includes linting, debugging, etc.)
code --install-extension ms-python.python

# Python type checking
code --install-extension ms-python.vscode-pylance

# Docker support
code --install-extension ms-azuretools.vscode-docker

# Better YAML support (for Docker compose, etc.)
code --install-extension redhat.vscode-yaml

# Git integration
code --install-extension eamodio.gitlens
```

#### PyCharm (Alternative)

PyCharm is a full-featured Python IDE with excellent debugging capabilities.

**macOS Installation:**
```bash
# Using Homebrew (Community Edition)
brew install --cask pycharm-ce

# For Professional Edition
# brew install --cask pycharm
```

**Linux Installation:**
Download the appropriate package from [JetBrains website](https://www.jetbrains.com/pycharm/download/) and follow their installation instructions.

**Windows Installation:**
```powershell
# Using winget (Community Edition)
winget install -e --id JetBrains.PyCharm.Community

# For Professional Edition
# winget install -e --id JetBrains.PyCharm.Professional
```

## Installation Steps

After installing all prerequisites, follow these steps to set up and run the application:

### 1. Get the Repository

#### Option A: Clone the Repository (Read-only)

If you just want to run the application without making contributions:

```bash
git clone https://github.com/egkristi/llm-langgraph.git
cd llm-langgraph
```

#### Option B: Fork and Clone (For Contributors)

If you want to contribute to the project:

1. Fork the repository on GitHub by visiting https://github.com/egkristi/llm-langgraph and clicking the 'Fork' button
2. Clone your forked repository:

```bash
git clone https://github.com/YOUR-USERNAME/llm-langgraph.git
cd llm-langgraph

# Add the original repository as a remote to keep your fork updated
git remote add upstream https://github.com/egkristi/llm-langgraph.git
```

To keep your fork updated with the main repository:

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

### 2. Install Dependencies

**Option A: Using uv directly**
```bash
uv init .
uv pip install -r requirements.txt
```

**Option B: Using a virtual environment (recommended for isolation)**
```bash
# Create a virtual environment (Python 3.13)
python3.13 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies with uv in the virtual environment
uv pip install -r requirements.txt
```

Using a virtual environment helps isolate dependencies and prevents conflicts with other Python projects.

### 3. Start Ollama

Start the Ollama service:

```bash
ollama serve
```

### 4. Pull Required Models

```bash
ollama pull llama3
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

#### Colima Troubleshooting

If you encounter issues with Colima:

```bash
# Check the Colima logs
colima status
colima logs

# Restart Colima with debug logging
colima stop
colima start --verbose

# Reset Colima if it becomes unresponsive
colima delete
colima start --cpu 4 --memory 8 --disk 20

# Ensure Docker CLI can connect to Colima
export DOCKER_HOST="unix://${HOME}/.colima/docker.sock"
```

Issues and solutions:

1. **Socket connection errors**: Make sure Colima is running with `colima status`
2. **Resource constraints**: Increase memory/CPU with `colima stop && colima start --memory 8 --cpu 4`
3. **Network issues**: Check firewall settings and try `colima stop && colima start --network-address`
4. **Lima VM issues**: Update Lima with `brew upgrade lima` and restart Colima

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
4. **Recommended approach**: Use Colima with appropriate resource allocation:
   ```bash
   colima stop
   colima start --cpu 4 --memory 8 --disk 20
   ```
5. Optimize Colima VM settings in `~/.colima/default/colima.yaml`:
   ```yaml
   # Example optimized configuration
   vm:
     cpus: 4
     memory: 8
     disk: 20
   kubernetes:
     enabled: false
   ```
6. If using Docker Desktop, increase memory allocation in Docker's resource settings (but consider switching to Colima for better performance and no licensing restrictions)

## Workspace System

The LLM-LangGraph application uses a workspace system to manage files for each group chat. Understanding this system will help you work with the application more effectively:

### Workspace Structure

Each group chat has its own persistent workspace with three folders:

- **code/**: Contains source code files that can be executed by the Code Runner agent
- **data/**: For input data, configuration files, and other resources
- **output/**: For execution results and generated output

All these workspaces are stored under the `workspaces` directory in the project root, with a subdirectory for each group chat. The directory name is the normalized group chat name (lowercase with underscores instead of spaces).

### Workspace Management

The workspace system is implemented in these key files:

- `src/utils/workspace_manager.py`: Core workspace functionality
- `src/tools/workspace_tools.py`: Tools for interacting with workspaces
- `src/tools/docker_code_runner.py`: Integration with Docker execution

The Code Runner agent can:
- Save code to the workspace before execution
- List files in the workspace
- Read files from the workspace
- Save data to the workspace
- Get information about the workspace

Files in the workspace persist between conversations, allowing for iterative development and testing.

## Additional Configuration

### Network Requirements

LLM-LangGraph requires internet access during installation and for certain features:

- **Initial Setup**: Required for downloading models and dependencies
- **Model Downloads**: Ollama needs internet access to pull models
- **Proxy Configuration**: If you're behind a corporate proxy, configure as follows:

```bash
# For Homebrew (macOS)
export HTTP_PROXY=http://proxy.example.com:port
export HTTPS_PROXY=http://proxy.example.com:port

# For apt (Linux)
export http_proxy=http://proxy.example.com:port
export https_proxy=http://proxy.example.com:port

# For pip/uv
pip config set global.proxy http://proxy.example.com:port

# For Docker
mkdir -p ~/.docker
cat > ~/.docker/config.json << EOF
{
  "proxies": {
    "default": {
      "httpProxy": "http://proxy.example.com:port",
      "httpsProxy": "http://proxy.example.com:port",
      "noProxy": "localhost,127.0.0.1"
    }
  }
}
EOF
```

### Environment Variables

LLM-LangGraph uses several environment variables for configuration:

| Variable | Description | Default | Example |
|----------|-------------|---------|--------|
| `OLLAMA_HOST` | Host address for Ollama server | localhost | `export OLLAMA_HOST=ollama.local` |
| `OLLAMA_PORT` | Port for Ollama server | 11434 | `export OLLAMA_PORT=8000` |
| `OLLAMA_MEMORY_LIMIT` | Memory limit for Ollama | System dependent | `export OLLAMA_MEMORY_LIMIT=4GB` |
| `DOCKER_HOST` | Docker socket location (for Colima) | System dependent | `export DOCKER_HOST=unix://$HOME/.colima/docker.sock` |

Create a `.env` file in the project root to set these variables permanently.

### Health Check

Verify your installation is working correctly:

```bash
# Check Python version
python --version  # Should be 3.13+

# Verify Ollama is running
curl http://localhost:11434/api/tags  # Should return JSON with available models

# Verify Docker is working
docker run hello-world  # Should show "Hello from Docker!"

# Verify the application
./run.sh  # Should start without errors
```

### Upgrading

To upgrade LLM-LangGraph to the latest version:

```bash
# Navigate to the project directory
cd llm-langgraph

# Stop any running instances
./stop.sh

# Pull the latest changes
git pull

# Update dependencies
uv pip install -r requirements.txt

# Restart the application
./run.sh
```

### Uninstallation and Cleanup

If you need to remove LLM-LangGraph or perform a clean reinstall:

**Stop and Remove the Application:**
```bash
# Navigate to the project directory
cd llm-langgraph

# Stop any running instances
./stop.sh

# Remove the repository (BE CAREFUL - this deletes all workspaces and local changes)
cd ..
rm -rf llm-langgraph
```

**Clean Up Dependencies (Optional):**

*macOS:*
```bash
# Remove Ollama and models
brew uninstall ollama
rm -rf ~/.ollama

# Stop and remove Colima (if using)
colima stop
colima delete

# Uninstall Colima and Docker CLI (optional)
# brew uninstall colima docker docker-compose
```

*Linux:*
```bash
# Remove Ollama and models
sudo rm -f /usr/local/bin/ollama
rm -rf ~/.ollama

# Remove Docker (Ubuntu/Debian)
# sudo apt-get purge docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
# sudo rm -rf /var/lib/docker
```

*Windows:*
```powershell
# Remove Ollama and models
Remove-Item -Recurse -Force "$env:USERPROFILE\ollama"
Remove-Item -Recurse -Force "$env:USERPROFILE\.ollama"

# Uninstall applications using winget
# winget uninstall Microsoft.VisualStudioCode
# winget uninstall Docker.DockerDesktop
# winget uninstall Python.Python.3.13
```

## Next Steps

Once installation is complete, refer to the [README.md](README.md) for usage instructions.

For further assistance, please open an issue on the project's GitHub repository.
