"""Main Agent orchestrating perception-reasoning-action cycle"""

import time
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .perception import ScreenPerception
from .action_executor import ActionExecutor
from .model_handler import ModelHandler
from .utils import load_config, setup_logging


class GUIAutomationAgent:
    """Main agent for Android GUI automation using Gemma 3 models"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)
        
        # Initialize components
        self.logger.info("Initializing GUI Automation Agent...")
        self.perception = ScreenPerception(self.config)
        self.executor = ActionExecutor(self.config)
        self.model = ModelHandler(self.config)
        
        self.task_history: List[Dict] = []
        self.current_step = 0
        
    def run_task(self, task_description: str) -> bool:
        """Execute a complete task through perception-reasoning-action cycle"""
        self.logger.info(f"Starting task: {task_description}")
        self.current_step = 0
        max_steps = self.config['agent']['max_steps']
        
        system_prompt = self._build_system_prompt()
        conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task_description}"}
        ]
        
        while self.current_step < max_steps:
            self.current_step += 1
            self.logger.info(f"Step {self.current_step}/{max_steps}")
            
            try:
                # Perception: Capture screen state
                screen_data = self.perception.capture_screen_state()
                
                if not screen_data:
                    self.logger.error("Failed to capture screen state")
                    return False
                
                # Reasoning: Get next action from model
                action_response = self.model.get_next_action(
                    screen_data=screen_data,
                    conversation_history=conversation_history
                )
                
                # Log reasoning
                self.logger.info(f"Model reasoning: {action_response.get('reasoning', 'N/A')}")
                
                # Check if task is complete
                if action_response.get('task_complete', False):
                    self.logger.info("Task completed successfully!")
                    return True
                
                # Action: Execute the planned action
                action = action_response.get('action')
                if not action:
                    self.logger.error("No action received from model")
                    return False
                
                success = self._execute_action(action)
                
                if not success:
                    self.logger.warning(f"Action execution failed: {action}")
                    conversation_history.append({
                        "role": "assistant",
                        "content": f"Action failed: {action}. Trying alternative approach."
                    })
                else:
                    # Update conversation history
                    conversation_history.append({
                        "role": "assistant",
                        "content": f"Executed: {action['type']} - {action_response.get('reasoning', '')}"
                    })
                
                # Wait for UI to update
                time.sleep(self.config['agent']['action_delay'])
                
            except Exception as e:
                self.logger.error(f"Error in step {self.current_step}: {str(e)}")
                if self.config['agent']['screenshot_on_error']:
                    self.perception.save_error_screenshot(f"error_step_{self.current_step}")
                return False
        
        self.logger.warning(f"Task not completed within {max_steps} steps")
        return False
    
    def _execute_action(self, action: Dict) -> bool:
        """Execute a single action"""
        action_type = action.get('type')
        
        if action_type == 'tap':
            return self.executor.tap(action['x'], action['y'])
        elif action_type == 'swipe':
            return self.executor.swipe(
                action['start_x'], action['start_y'],
                action['end_x'], action['end_y']
            )
        elif action_type == 'input_text':
            return self.executor.input_text(action['text'])
        elif action_type == 'press_key':
            return self.executor.press_key(action['key'])
        elif action_type == 'wait':
            time.sleep(action.get('duration', 2))
            return True
        else:
            self.logger.error(f"Unknown action type: {action_type}")
            return False
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the model"""
        return """You are an AI agent controlling an Android device through GUI automation.

Your task is to analyze the current screen state and decide the next action to perform.
You will receive:
1. Screenshot description or UI hierarchy
2. Available UI elements with their coordinates and properties

You must respond in JSON format with:
{
  "reasoning": "Your thought process for this action",
  "action": {
    "type": "tap|swipe|input_text|press_key|wait",
    "x": <int>,  // for tap
    "y": <int>,  // for tap
    "start_x": <int>,  // for swipe
    "start_y": <int>,  // for swipe
    "end_x": <int>,  // for swipe
    "end_y": <int>,  // for swipe
    "text": "<string>",  // for input_text
    "key": "home|back|enter",  // for press_key
    "duration": <float>  // for wait
  },
  "task_complete": false  // Set to true when task is finished
}

Be precise with coordinates. Analyze the UI hierarchy carefully before acting.
"""


if __name__ == "__main__":
    agent = GUIAutomationAgent()
    
    # Example task
    task = "Open the Settings app and enable Dark Mode"
    success = agent.run_task(task)
    
    print(f"Task {'completed' if success else 'failed'}")
