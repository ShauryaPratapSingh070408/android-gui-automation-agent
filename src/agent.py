"""Main agent orchestrator implementing the perception-reasoning-action cycle."""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from .perception import PerceptionModule
from .action import ActionExecutor
from .inference import GemmaInference
from .utils import setup_logger


@dataclass
class AgentState:
    """Represents the current state of the agent."""
    task_description: str
    current_screen: Optional[Dict] = None
    action_history: List[Dict] = None
    step_count: int = 0
    max_steps: int = 50
    task_completed: bool = False
    
    def __post_init__(self):
        if self.action_history is None:
            self.action_history = []


class GUIAutomationAgent:
    """Main agent class for Android GUI automation."""
    
    def __init__(self, config: Dict):
        """Initialize the agent with configuration.
        
        Args:
            config: Configuration dictionary containing model and device settings
        """
        self.logger = setup_logger(__name__, config.get('log_level', 'INFO'))
        self.config = config
        
        # Initialize core modules
        self.perception = PerceptionModule(config)
        self.action_executor = ActionExecutor(config)
        self.inference = GemmaInference(config)
        
        self.logger.info("Agent initialized successfully")
    
    def execute_task(self, task_description: str, max_steps: int = 50) -> bool:
        """Execute a high-level task on the Android device.
        
        Args:
            task_description: Natural language description of the task
            max_steps: Maximum number of steps to attempt
            
        Returns:
            True if task completed successfully, False otherwise
        """
        state = AgentState(
            task_description=task_description,
            max_steps=max_steps
        )
        
        self.logger.info(f"Starting task: {task_description}")
        
        while not state.task_completed and state.step_count < state.max_steps:
            try:
                # Perception: Observe current screen state
                screen_state = self.perception.capture_screen_state()
                state.current_screen = screen_state
                
                self.logger.info(f"Step {state.step_count + 1}: Analyzing screen")
                
                # Reasoning: Determine next action using Gemma model
                action = self.inference.decide_next_action(
                    screen_state=screen_state,
                    task_description=task_description,
                    action_history=state.action_history
                )
                
                self.logger.info(f"Planned action: {action['type']}")
                
                # Check if task is complete
                if action['type'] == 'task_complete':
                    state.task_completed = True
                    self.logger.info("Task completed successfully!")
                    break
                
                # Action: Execute the decided action
                success = self.action_executor.execute(action)
                
                if not success:
                    self.logger.warning(f"Action failed: {action}")
                
                # Update state
                state.action_history.append({
                    'step': state.step_count,
                    'action': action,
                    'success': success,
                    'timestamp': time.time()
                })
                
                state.step_count += 1
                
                # Wait for UI to update
                time.sleep(self.config.get('step_delay', 1.5))
                
            except Exception as e:
                self.logger.error(f"Error at step {state.step_count}: {str(e)}")
                if not self.config.get('continue_on_error', False):
                    break
        
        if not state.task_completed:
            self.logger.warning(f"Task not completed after {state.step_count} steps")
        
        return state.task_completed
    
    def cleanup(self):
        """Cleanup resources."""
        self.perception.cleanup()
        self.action_executor.cleanup()
        self.inference.cleanup()
        self.logger.info("Agent cleanup completed")
