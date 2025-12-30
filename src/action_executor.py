"""Action execution module for Android device control"""

import logging
import time
from typing import Dict, Tuple

from ppadb.client import Client as AdbClient


class ActionExecutor:
    """Executes actions on Android device via ADB"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Connect to ADB
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)
        self.device = self._connect_device()
        
    def _connect_device(self):
        """Connect to Android device via ADB"""
        devices = self.adb_client.devices()
        
        if not devices:
            raise RuntimeError("No Android devices connected")
        
        device_serial = self.config['adb'].get('device_serial')
        
        if device_serial:
            device = next((d for d in devices if d.serial == device_serial), None)
            if not device:
                raise RuntimeError(f"Device {device_serial} not found")
        else:
            device = devices[0]
        
        return device
    
    def tap(self, x: int, y: int) -> bool:
        """Tap at coordinates (x, y)"""
        try:
            self.logger.debug(f"Tapping at ({x}, {y})")
            self.device.shell(f"input tap {x} {y}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to tap at ({x}, {y}): {str(e)}")
            return False
    
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 300) -> bool:
        """Swipe from (start_x, start_y) to (end_x, end_y)"""
        try:
            self.logger.debug(f"Swiping from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            self.device.shell(f"input swipe {start_x} {start_y} {end_x} {end_y} {duration}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to swipe: {str(e)}")
            return False
    
    def input_text(self, text: str) -> bool:
        """Input text (spaces must be escaped as %s)"""
        try:
            # Escape spaces and special characters
            escaped_text = text.replace(' ', '%s')
            self.logger.debug(f"Inputting text: {text}")
            self.device.shell(f"input text {escaped_text}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to input text: {str(e)}")
            return False
    
    def press_key(self, key: str) -> bool:
        """Press hardware key (home, back, enter, etc.)"""
        key_codes = {
            'home': 3,
            'back': 4,
            'enter': 66,
            'menu': 82,
            'power': 26,
            'volume_up': 24,
            'volume_down': 25,
            'tab': 61,
            'space': 62,
            'delete': 67
        }
        
        try:
            key_code = key_codes.get(key.lower())
            if key_code is None:
                self.logger.error(f"Unknown key: {key}")
                return False
            
            self.logger.debug(f"Pressing key: {key}")
            self.device.shell(f"input keyevent {key_code}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to press key {key}: {str(e)}")
            return False
    
    def long_press(self, x: int, y: int, duration: int = 1000) -> bool:
        """Long press at coordinates"""
        try:
            self.logger.debug(f"Long pressing at ({x}, {y}) for {duration}ms")
            self.device.shell(f"input swipe {x} {y} {x} {y} {duration}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to long press: {str(e)}")
            return False
    
    def scroll_down(self, distance: int = 500) -> bool:
        """Scroll down on screen"""
        # Get screen center for swipe
        start_x, start_y = 540, 1400
        end_x, end_y = 540, 1400 - distance
        return self.swipe(start_x, start_y, end_x, end_y)
    
    def scroll_up(self, distance: int = 500) -> bool:
        """Scroll up on screen"""
        start_x, start_y = 540, 800
        end_x, end_y = 540, 800 + distance
        return self.swipe(start_x, start_y, end_x, end_y)
    
    def open_app(self, package_name: str) -> bool:
        """Open app by package name"""
        try:
            self.logger.info(f"Opening app: {package_name}")
            self.device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
            time.sleep(2)  # Wait for app to open
            return True
        except Exception as e:
            self.logger.error(f"Failed to open app {package_name}: {str(e)}")
            return False
    
    def close_app(self, package_name: str) -> bool:
        """Force close an app"""
        try:
            self.logger.info(f"Closing app: {package_name}")
            self.device.shell(f"am force-stop {package_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to close app {package_name}: {str(e)}")
            return False
    
    def get_current_activity(self) -> str:
        """Get currently running activity"""
        try:
            output = self.device.shell("dumpsys window windows | grep -E 'mCurrentFocus'")
            # Extract package/activity from output
            return output.strip()
        except Exception as e:
            self.logger.error(f"Failed to get current activity: {str(e)}")
            return ""
