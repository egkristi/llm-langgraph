"""Entry point for llm-langgraph."""

import subprocess
import sys


def main():
    """Launch the Streamlit application."""
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "src/app.py"],
        check=True,
    )


if __name__ == "__main__":
    main()
