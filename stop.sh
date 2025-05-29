#!/bin/bash
# Script to stop the LLM-LangGraph application

echo "Stopping any running Streamlit processes..."
pkill -f "streamlit run" || echo "No running Streamlit processes found"
echo "LLM-LangGraph application stopped."
