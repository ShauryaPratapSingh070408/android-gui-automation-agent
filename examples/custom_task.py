"""Custom task runner for GUI automation"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import GUIAutomationAgent


def main():
    parser = argparse.ArgumentParser(description='Run custom GUI automation task')
    parser.add_argument('task', type=str, help='Task description in natural language')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    print(f"\n{'=' * 60}")
    print(f"GUI Automation Agent")
    print(f"{'=' * 60}")
    print(f"\nTask: {args.task}")
    print(f"\nStarting execution...\n")
    
    # Create and run agent
    agent = GUIAutomationAgent(config_path=args.config)
    success = agent.run_task(args.task)
    
    print(f"\n{'=' * 60}")
    if success:
        print("✅ Task completed successfully!")
    else:
        print("❌ Task failed or incomplete")
    print(f"{'=' * 60}\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
