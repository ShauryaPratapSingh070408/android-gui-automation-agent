"""Model handler for Gemma 3 inference"""

import json
import logging
from typing import Dict, List, Optional
import io
import base64

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from PIL import Image
import numpy as np


class ModelHandler:
    """Handles Gemma 3 model inference for action planning"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        model_config = config['model']
        self.device = torch.device(model_config['device'])
        
        # Load tokenizer and model
        self.logger.info(f"Loading model: {model_config['name']}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_config['name'])
        self.model = AutoModelForCausalLM.from_pretrained(
            model_config['name'],
            torch_dtype=torch.float16 if model_config['device'] == 'cuda' else torch.float32,
            device_map=model_config['device']
        )
        
        # Apply quantization if specified
        if model_config.get('quantization') == 'int8':
            self._quantize_model_int8()
        
        self.model.eval()
        self.logger.info("Model loaded successfully")
    
    def _quantize_model_int8(self):
        """Apply INT8 quantization for smaller memory footprint"""
        try:
            self.model = torch.quantization.quantize_dynamic(
                self.model, {torch.nn.Linear}, dtype=torch.qint8
            )
            self.logger.info("Model quantized to INT8")
        except Exception as e:
            self.logger.warning(f"Quantization failed: {str(e)}")
    
    def get_next_action(self, screen_data: Dict, conversation_history: List[Dict]) -> Dict:
        """Generate next action based on screen state"""
        try:
            # Build prompt from screen data
            prompt = self._build_prompt(screen_data, conversation_history)
            
            # Generate response
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=self.config['model']['max_tokens'],
                    temperature=self.config['model']['temperature'],
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract JSON response from model output
            action_dict = self._parse_model_response(response_text)
            
            return action_dict
            
        except Exception as e:
            self.logger.error(f"Model inference failed: {str(e)}")
            return {
                'reasoning': 'Error in model inference',
                'action': {'type': 'wait', 'duration': 1},
                'task_complete': False
            }
    
    def _build_prompt(self, screen_data: Dict, conversation_history: List[Dict]) -> str:
        """Build prompt from screen data and conversation history"""
        # Extract UI elements
        ui_elements = screen_data.get('ui_elements', [])
        
        # Create structured representation of UI
        ui_description = "\n".join([
            f"{i+1}. {elem['class'].split('.')[-1]} at ({elem['center']['x']}, {elem['center']['y']}): "
            f"text='{elem['text']}', desc='{elem['content_desc']}', clickable={elem['clickable']}"
            for i, elem in enumerate(ui_elements[:20])  # Limit to top 20 elements
        ])
        
        # Build conversation context
        context = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in conversation_history[-5:]  # Last 5 messages
        ])
        
        prompt = f"""Current Screen State:
{ui_description}

Conversation History:
{context}

Provide the next action as JSON:
"""
        
        return prompt
    
    def _parse_model_response(self, response: str) -> Dict:
        """Parse JSON from model response"""
        try:
            # Try to find JSON in response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                action_dict = json.loads(json_str)
                return action_dict
            else:
                self.logger.warning("No JSON found in model response")
                return self._fallback_action(response)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {str(e)}")
            return self._fallback_action(response)
    
    def _fallback_action(self, response: str) -> Dict:
        """Generate fallback action when parsing fails"""
        # Simple heuristic-based fallback
        if 'complete' in response.lower() or 'done' in response.lower():
            return {
                'reasoning': 'Task appears complete',
                'action': {'type': 'wait', 'duration': 0},
                'task_complete': True
            }
        else:
            return {
                'reasoning': 'Waiting for next observation',
                'action': {'type': 'wait', 'duration': 2},
                'task_complete': False
            }
    
    def analyze_screenshot(self, screenshot: Image.Image) -> str:
        """Analyze screenshot using vision capabilities (optional)"""
        # This would use PaliGemma or similar vision model
        # For now, return placeholder
        return "Screenshot analysis not implemented yet"
