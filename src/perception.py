"""Screen perception module for capturing and analyzing screen state"""

import io
import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

from ppadb.client import Client as AdbClient
from PIL import Image


class ScreenPerception:
    """Handles screen capture and UI hierarchy extraction"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Connect to ADB
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)
        self.device = self._connect_device()
        
        # Create screenshot directory
        self.screenshot_dir = Path(config['logging']['screenshot_dir'])
        self.screenshot_dir.mkdir(exist_ok=True)
        
    def _connect_device(self):
        """Connect to Android device via ADB"""
        devices = self.adb_client.devices()
        
        if not devices:
            raise RuntimeError("No Android devices connected. Enable USB debugging and connect device.")
        
        device_serial = self.config['adb'].get('device_serial')
        
        if device_serial:
            device = next((d for d in devices if d.serial == device_serial), None)
            if not device:
                raise RuntimeError(f"Device {device_serial} not found")
        else:
            device = devices[0]
            self.logger.info(f"Auto-selected device: {device.serial}")
        
        return device
    
    def capture_screen_state(self) -> Optional[Dict]:
        """Capture complete screen state including screenshot and UI hierarchy"""
        try:
            # Capture screenshot
            screenshot = self._capture_screenshot()
            
            # Extract UI hierarchy
            ui_elements = self._extract_ui_hierarchy()
            
            # Get screen dimensions
            screen_size = self._get_screen_size()
            
            return {
                'screenshot': screenshot,
                'ui_elements': ui_elements,
                'screen_size': screen_size,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to capture screen state: {str(e)}")
            return None
    
    def _capture_screenshot(self) -> Image.Image:
        """Capture screenshot from device"""
        screenshot_bytes = self.device.screencap()
        screenshot = Image.open(io.BytesIO(screenshot_bytes))
        
        # Resize if needed
        max_width = self.config['screen']['max_width']
        if screenshot.width > max_width:
            ratio = max_width / screenshot.width
            new_height = int(screenshot.height * ratio)
            screenshot = screenshot.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Save screenshot if configured
        if self.config['logging']['save_screenshots']:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot.save(self.screenshot_dir / f"screen_{timestamp}.png")
        
        return screenshot
    
    def _extract_ui_hierarchy(self) -> List[Dict]:
        """Extract UI element hierarchy using uiautomator"""
        try:
            # Dump UI hierarchy
            self.device.shell("uiautomator dump /sdcard/ui_dump.xml")
            xml_content = self.device.shell("cat /sdcard/ui_dump.xml")
            
            # Parse XML
            root = ET.fromstring(xml_content)
            elements = []
            
            self._parse_ui_node(root, elements)
            
            return elements
            
        except Exception as e:
            self.logger.warning(f"Failed to extract UI hierarchy: {str(e)}")
            return []
    
    def _parse_ui_node(self, node: ET.Element, elements: List[Dict], depth: int = 0):
        """Recursively parse UI node tree"""
        bounds = node.get('bounds', '')
        if bounds:
            # Parse bounds format: [x1,y1][x2,y2]
            coords = bounds.replace('][', ',').strip('[]').split(',')
            if len(coords) == 4:
                x1, y1, x2, y2 = map(int, coords)
                
                element = {
                    'class': node.get('class', ''),
                    'text': node.get('text', ''),
                    'content_desc': node.get('content-desc', ''),
                    'resource_id': node.get('resource-id', ''),
                    'clickable': node.get('clickable', 'false') == 'true',
                    'enabled': node.get('enabled', 'false') == 'true',
                    'bounds': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
                    'center': {'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2},
                    'depth': depth
                }
                
                # Only include interactive elements
                if element['clickable'] or element['text'] or element['content_desc']:
                    elements.append(element)
        
        # Recurse through children
        for child in node:
            self._parse_ui_node(child, elements, depth + 1)
    
    def _get_screen_size(self) -> Dict[str, int]:
        """Get device screen dimensions"""
        output = self.device.shell("wm size")
        # Output format: Physical size: 1080x2400
        if 'Physical size:' in output:
            size_str = output.split('Physical size:')[1].strip()
            width, height = map(int, size_str.split('x'))
            return {'width': width, 'height': height}
        return {'width': 1080, 'height': 2400}  # Default
    
    def save_error_screenshot(self, prefix: str = "error"):
        """Save screenshot for debugging"""
        try:
            screenshot = self._capture_screenshot()
            filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot.save(self.screenshot_dir / filename)
            self.logger.info(f"Error screenshot saved: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save error screenshot: {str(e)}")
