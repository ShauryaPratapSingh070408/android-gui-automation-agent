"""Example tasks for GUI automation agent"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import GUIAutomationAgent


def example_open_settings():
    """Example: Open Settings and navigate to Display settings"""
    agent = GUIAutomationAgent()
    
    task = "Open the Settings app and go to Display settings"
    success = agent.run_task(task)
    
    print(f"\nTask {'✅ COMPLETED' if success else '❌ FAILED'}")
    return success


def example_send_message():
    """Example: Open Messages app and send a text"""
    agent = GUIAutomationAgent()
    
    task = "Open Messages app, create new message, enter 'Test message', but don't send"
    success = agent.run_task(task)
    
    print(f"\nTask {'✅ COMPLETED' if success else '❌ FAILED'}")
    return success


def example_browse_web():
    """Example: Open browser and search"""
    agent = GUIAutomationAgent()
    
    task = "Open Chrome browser and search for 'Android automation'"
    success = agent.run_task(task)
    
    print(f"\nTask {'✅ COMPLETED' if success else '❌ FAILED'}")
    return success


if __name__ == "__main__":
    print("=" * 50)
    print("GUI Automation Agent - Example Tasks")
    print("=" * 50)
    
    # Run example tasks
    print("\n1. Opening Settings...")
    example_open_settings()
    
    print("\n" + "=" * 50)
    print("\n2. Composing message...")
    example_send_message()
    
    print("\n" + "=" * 50)
    print("\n3. Web browsing...")
    example_browse_web()
