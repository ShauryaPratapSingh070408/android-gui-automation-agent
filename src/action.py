"""Action executor module for performing Android device interactions."""

import subprocess
import time
from typing import Dict, List, Optional

from .utils import setup_logger


class ActionExecutor:
    """Executes actions on Android device via ADB."""
    
    def __init__(self, config: Dict):
        """Initialize action executor.
        
        Args:
            config: Configuration dictionary
        """
        self.logger = setup_logger(__name__, config.get('log_level', 'INFO'))
        self.config = config
        self.device_id = config.get('device_id')
    
    def _run_adb_command(self, command: List[str]) -> bool:
        """Run an ADB command.
        
        Args:
            command: ADB command as list of strings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            adb_cmd = ['adb']
            if self.device_id:
                adb_cmd.extend(['-s', self.device_id])
            adb_cmd.extend(command)
            
            subprocess.run(adb_cmd, capture_output=True, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"ADB command failed: {e}")
            return False
    
    def execute(self, action: Dict) -> bool:
        """Execute an action on the device.
        
        Args:
            action: Action dictionary with type and parameters
            
        Returns:
            True if action executed successfully, False otherwise
        """
        action_type = action.get('type')
        
        if action_type == 'tap':
            return self.tap(action['x'], action['y'])
        elif action_type == 'swipe':
            return self.swipe(
                action['x1'], action['y1'],
                action['x2'], action['y2'],
                action.get('duration', 300)
            )
        elif action_type == 'text_input':
            return self.input_text(action['text'])
        elif action_type == 'key_event':
            return self.press_key(action['key'])
        elif action_type == 'long_press':
            return self.long_press(action['x'], action['y'], action.get('duration', 1000))
        elif action_type == 'wait':
            time.sleep(action.get('duration', 1))
            return True
        elif action_type == 'task_complete':
            return True
        else:
            self.logger.warning(f"Unknown action type: {action_type}")
            return False
    
    def tap(self, x: int, y: int) -> bool:
        """Tap at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful
        """
        self.logger.info(f"Tapping at ({x}, {y})")
        return self._run_adb_command(
            ['shell', 'input', 'tap', str(x), str(y)]
        )
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """Swipe from one point to another.
        
        Args:
            x1: Start X coordinate
            y1: Start Y coordinate
            x2: End X coordinate
            y2: End Y coordinate
            duration: Swipe duration in milliseconds
            
        Returns:
            True if successful
        """
        self.logger.info(f"Swiping from ({x1}, {y1}) to ({x2}, {y2})")
        return self._run_adb_command(
            ['shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)]
        )
    
    def input_text(self, text: str) -> bool:
        """Input text (requires focused text field).
        
        Args:
            text: Text to input
            
        Returns:
            True if successful
        """
        # Replace spaces with %s for ADB
        text_escaped = text.replace(' ', '%s')
        self.logger.info(f"Inputting text: {text}")
        return self._run_adb_command(
            ['shell', 'input', 'text', text_escaped]
        )
    
    def press_key(self, key: str) -> bool:
        """Press a hardware key.
        
        Args:
            key: Key name (HOME, BACK, ENTER, etc.)
            
        Returns:
            True if successful
        """
        key_codes = {
            'HOME': '3',
            'BACK': '4',
            'ENTER': '66',
            'DELETE': '67',
            'MENU': '82',
            'POWER': '26',
            'VOLUME_UP': '24',
            'VOLUME_DOWN': '25'
        }
        
        key_code = key_codes.get(key.upper(), key)
        self.logger.info(f"Pressing key: {key}")
        return self._run_adb_command(
            ['shell', 'input', 'keyevent', key_code]
        )
    
    def long_press(self, x: int, y: int, duration: int = 1000) -> bool:
        """Long press at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration: Press duration in milliseconds
            
        Returns:
            True if successful
        """
        self.logger.info(f"Long pressing at ({x}, {y}) for {duration}ms")
        return self.swipe(x, y, x, y, duration)
    
    def scroll_down(self, x: int, y: int, distance: int = 500) -> bool:
        """Scroll down from a point.
        
        Args:
            x: X coordinate
            y: Y coordinate (top of scroll)
            distance: Scroll distance in pixels
            
        Returns:
            True if successful
        """
        return self.swipe(x, y + distance, x, y, 300)
    
    def scroll_up(self, x: int, y: int, distance: int = 500) -> bool:
        """Scroll up from a point.
        
        Args:
            x: X coordinate
            y: Y coordinate (bottom of scroll)
            distance: Scroll distance in pixels
            
        Returns:
            True if successful
        """
        return self.swipe(x, y - distance, x, y, 300)
    
    def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Action executor cleanup completed")
