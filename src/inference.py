"""Inference module using Gemma 3 models for action planning."""

import json
import re
from typing import Dict, List, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from PIL import Image
import numpy as np

from .utils import setup_logger


class GemmaInference:
    """Handles inference using Gemma 3 models for GUI automation."""
    
    def __init__(self, config: Dict):
        """Initialize Gemma inference module.
        
        Args:
            config: Configuration dictionary
        """
        self.logger = setup_logger(__name__, config.get('log_level', 'INFO'))
        self.config = config
        
        # Model configuration
        self.model_name = config.get('model_name', 'google/gemma-2-2b-it')
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.logger.info(f"Loading model: {self.model_name} on {self.device}")
        
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
            device_map='auto' if self.device == 'cuda' else None,
            trust_remote_code=True
        )
        
        if self.device == 'cpu':
            self.model = self.model.to(self.device)
        
        self.model.eval()
        
        self.logger.info("Model loaded successfully")
    
    def decide_next_action(
        self,
        screen_state: Dict,
        task_description: str,
        action_history: List[Dict]
    ) -> Dict:
        """Decide the next action based on screen state and task.
        
        Args:
            screen_state: Current screen state with UI hierarchy
            task_description: Description of the task to accomplish
            action_history: List of previous actions
            
        Returns:
            Action dictionary with type and parameters
        """
        # Prepare prompt with screen context
        prompt = self._create_action_prompt(
            screen_state, task_description, action_history
        )
        
        # Generate response from model
        response = self._generate_response(prompt)
        
        # Parse response into action
        action = self._parse_action_from_response(response, screen_state)
        
        return action
    
    def _create_action_prompt(
        self,
        screen_state: Dict,
        task_description: str,
        action_history: List[Dict]
    ) -> str:
        """Create a prompt for action planning.
        
        Args:
            screen_state: Current screen state
            task_description: Task description
            action_history: Previous actions
            
        Returns:
            Formatted prompt string
        """
        ui_elements = screen_state['ui_hierarchy']['elements']
        
        # Create element list with IDs
        elements_text = "Available UI Elements:\n"
        for idx, elem in enumerate(ui_elements[:20]):  # Limit to 20 elements
            text = elem.get('text', '')
            desc = elem.get('content_desc', '')
            elem_type = elem.get('class', '').split('.')[-1]
            clickable = "[CLICKABLE]" if elem['clickable'] else ""
            
            label = text or desc or elem_type
            elements_text += f"  {idx}: {label} ({elem_type}) {clickable} at ({elem['center']['x']}, {elem['center']['y']})\n"
        
        # Format action history
        history_text = ""
        if action_history:
            recent_actions = action_history[-3:]  # Last 3 actions
            history_text = "\nRecent Actions:\n"
            for action_record in recent_actions:
                action = action_record['action']
                history_text += f"  - {action['type']}: {action.get('description', 'N/A')}\n"
        
        prompt = f"""You are an Android GUI automation agent. Your task is to determine the next action to accomplish the user's goal.

Task: {task_description}

{elements_text}
{history_text}

Instructions:
1. Analyze the available UI elements
2. Consider the task goal and action history
3. Decide the next action to take
4. Respond with a JSON object containing the action

Action types:
- tap: Click an element (requires: element_id or x, y coordinates)
- text_input: Enter text (requires: text)
- swipe: Swipe gesture (requires: x1, y1, x2, y2)
- key_event: Press hardware key (requires: key like HOME, BACK, ENTER)
- scroll_down/scroll_up: Scroll (requires: x, y)
- task_complete: Task is finished
- wait: Wait briefly (requires: duration in seconds)

Example response:
{{
  "action_type": "tap",
  "element_id": 5,
  "reasoning": "Clicking the search button to proceed with the task"
}}

Your response (JSON only):"""
        
        return prompt
    
    def _generate_response(self, prompt: str, max_length: int = 512) -> str:
        """Generate response from Gemma model.
        
        Args:
            prompt: Input prompt
            max_length: Maximum response length
            
        Returns:
            Generated text
        """
        try:
            # Tokenize input
            inputs = self.tokenizer(
                prompt,
                return_tensors='pt',
                truncation=True,
                max_length=2048
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            )
            
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            return '{}'
    
    def _parse_action_from_response(
        self,
        response: str,
        screen_state: Dict
    ) -> Dict:
        """Parse action from model response.
        
        Args:
            response: Model's response text
            screen_state: Current screen state
            
        Returns:
            Action dictionary
        """
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if not json_match:
                self.logger.warning("No JSON found in response")
                return {'type': 'wait', 'duration': 1}
            
            json_str = json_match.group(0)
            action_data = json.loads(json_str)
            
            action_type = action_data.get('action_type', 'wait')
            
            # Build action based on type
            if action_type == 'tap':
                element_id = action_data.get('element_id')
                if element_id is not None:
                    elements = screen_state['ui_hierarchy']['elements']
                    if 0 <= element_id < len(elements):
                        elem = elements[element_id]
                        return {
                            'type': 'tap',
                            'x': elem['center']['x'],
                            'y': elem['center']['y'],
                            'description': action_data.get('reasoning', '')
                        }
                
                # Fallback to coordinates
                return {
                    'type': 'tap',
                    'x': action_data.get('x', 100),
                    'y': action_data.get('y', 100),
                    'description': action_data.get('reasoning', '')
                }
            
            elif action_type == 'text_input':
                return {
                    'type': 'text_input',
                    'text': action_data.get('text', ''),
                    'description': action_data.get('reasoning', '')
                }
            
            elif action_type == 'swipe':
                return {
                    'type': 'swipe',
                    'x1': action_data.get('x1', 500),
                    'y1': action_data.get('y1', 1000),
                    'x2': action_data.get('x2', 500),
                    'y2': action_data.get('y2', 300),
                    'description': action_data.get('reasoning', '')
                }
            
            elif action_type in ['key_event', 'press_key']:
                return {
                    'type': 'key_event',
                    'key': action_data.get('key', 'BACK'),
                    'description': action_data.get('reasoning', '')
                }
            
            elif action_type == 'task_complete':
                return {
                    'type': 'task_complete',
                    'description': action_data.get('reasoning', 'Task completed')
                }
            
            else:
                return {
                    'type': 'wait',
                    'duration': 1,
                    'description': 'Unknown action, waiting'
                }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return {'type': 'wait', 'duration': 1}
        except Exception as e:
            self.logger.error(f"Error parsing action: {e}")
            return {'type': 'wait', 'duration': 1}
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'model'):
            del self.model
        if hasattr(self, 'tokenizer'):
            del self.tokenizer
        torch.cuda.empty_cache()
        self.logger.info("Inference module cleanup completed")
