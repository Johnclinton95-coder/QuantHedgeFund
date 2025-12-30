"""
Start Dashboard Script

Launch the Streamlit dashboard.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Start the Streamlit dashboard."""
    
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "app.py"
    
    print("🚀 Starting QS Hedge Fund Dashboard...")
    print(f"   Dashboard: {dashboard_path}")
    print()
    print("   Open http://localhost:8501 in your browser")
    print("   Press Ctrl+C to stop")
    print()
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(dashboard_path),
            "--server.port", "8501",
            "--server.headless", "true",
        ])
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")


if __name__ == "__main__":
    main()
