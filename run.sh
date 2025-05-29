#!/bin/bash
# Script to start the LLM-LangGraph application

echo "Starting LLM-LangGraph application..."
cd "$(dirname "$0")" || { echo "Failed to change directory"; exit 1; }

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "⚠️  Warning: Ollama doesn't seem to be running at http://localhost:11434"
  echo "Please start Ollama before continuing."
  echo "You can start it with: ollama serve"
fi

# Run the application with UV
uv run streamlit run src/app.py

# Note: This script will block until the app is stopped
