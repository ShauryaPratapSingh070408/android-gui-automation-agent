"""Perception module for capturing and processing screen state."""

import os
import time
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image
import io

from .utils import setup_logger


class PerceptionModule:
    """Handles screen capture and UI hierarchy extraction."""
    
    def __init__(self, config: Dict):
        """Initialize perception module.
        
        Args:
            config: Configuration dictionary
        """
        self.logger = setup_logger(__name__, config.get('log_level', 'INFO'))
        self.config = config
        self.device_id = config.get('device_id')
        self.screenshot_dir = Path(config.get('screenshot_dir', 'screenshots'))
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # Verify ADB connection
        self._verify_adb_connection()
    
    def _verify_adb_connection(self):
        """Verify ADB is installed and device is connected."""
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                check=True
            )
            
            if 'device' not in result.stdout:
                raise RuntimeError("No Android device connected")
            
            self.logger.info("ADB connection verified")
            
        except FileNotFoundError:
            raise RuntimeError("ADB not found. Please install Android SDK Platform Tools")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ADB error: {e}")
    
    def _run_adb_command(self, command: List[str]) -> subprocess.CompletedProcess:
        """Run an ADB command.
        
        Args:
            command: ADB command as list of strings
            
        Returns:
            CompletedProcess object
        """
        adb_cmd = ['adb']
        if self.device_id:
            adb_cmd.extend(['-s', self.device_id])
        adb_cmd.extend(command)
        
        return subprocess.run(
            adb_cmd,
            capture_output=True,
            check=True
        )
    
    def capture_screenshot(self) -> Image.Image:
        """Capture screenshot from Android device.
        
        Returns:
            PIL Image object
        """
        try:
            # Capture screenshot
            result = self._run_adb_command(
                ['shell', 'screencap', '-p']
            )
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(result.stdout))
            
            # Save screenshot with timestamp
            timestamp = int(time.time())
            screenshot_path = self.screenshot_dir / f"screenshot_{timestamp}.png"
            image.save(screenshot_path)
            
            self.logger.debug(f"Screenshot saved: {screenshot_path}")
            
            return image
            
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
            raise
    
    def extract_ui_hierarchy(self) -> Dict:
        """Extract UI hierarchy using uiautomator.
        
        Returns:
            Dictionary containing parsed UI elements
        """
        try:
            # Dump UI hierarchy to device
            self._run_adb_command(
                ['shell', 'uiautomator', 'dump', '/sdcard/window_dump.xml']
            )
            
            # Pull XML file
            result = self._run_adb_command(
                ['shell', 'cat', '/sdcard/window_dump.xml']
            )
            
            xml_content = result.stdout.decode('utf-8')
            
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Extract UI elements
            ui_elements = self._parse_ui_elements(root)
            
            return {
                'elements': ui_elements,
                'element_count': len(ui_elements),
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract UI hierarchy: {e}")
            return {'elements': [], 'element_count': 0, 'timestamp': time.time()}
    
    def _parse_ui_elements(self, root: ET.Element, parent_path: str = "") -> List[Dict]:
        """Recursively parse UI elements from XML.
        
        Args:
            root: XML element
            parent_path: Path of parent element
            
        Returns:
            List of UI element dictionaries
        """
        elements = []
        
        for idx, child in enumerate(root):
            element_path = f"{parent_path}/{child.tag}[{idx}]"
            
            # Extract bounds
            bounds_str = child.attrib.get('bounds', '[0,0][0,0]')
            bounds = self._parse_bounds(bounds_str)
            
            element = {
                'path': element_path,
                'class': child.attrib.get('class', ''),
                'text': child.attrib.get('text', ''),
                'content_desc': child.attrib.get('content-desc', ''),
                'resource_id': child.attrib.get('resource-id', ''),
                'clickable': child.attrib.get('clickable', 'false') == 'true',
                'scrollable': child.attrib.get('scrollable', 'false') == 'true',
                'enabled': child.attrib.get('enabled', 'true') == 'true',
                'bounds': bounds,
                'center': self._calculate_center(bounds)
            }
            
            # Only include interactive or informative elements
            if (element['clickable'] or element['scrollable'] or 
                element['text'] or element['content_desc']):
                elements.append(element)
            
            # Recursively process children
            elements.extend(self._parse_ui_elements(child, element_path))
        
        return elements
    
    def _parse_bounds(self, bounds_str: str) -> Dict:
        """Parse bounds string to coordinates.
        
        Args:
            bounds_str: Bounds string like '[x1,y1][x2,y2]'
            
        Returns:
            Dictionary with x1, y1, x2, y2 coordinates
        """
        try:
            # Remove brackets and split
            coords = bounds_str.replace('][', ',').replace('[', '').replace(']', '').split(',')
            return {
                'x1': int(coords[0]),
                'y1': int(coords[1]),
                'x2': int(coords[2]),
                'y2': int(coords[3])
            }
        except:
            return {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}
    
    def _calculate_center(self, bounds: Dict) -> Dict:
        """Calculate center point of bounds.
        
        Args:
            bounds: Dictionary with x1, y1, x2, y2
            
        Returns:
            Dictionary with x, y center coordinates
        """
        return {
            'x': (bounds['x1'] + bounds['x2']) // 2,
            'y': (bounds['y1'] + bounds['y2']) // 2
        }
    
    def capture_screen_state(self) -> Dict:
        """Capture complete screen state including screenshot and UI hierarchy.
        
        Returns:
            Dictionary containing screen information
        """
        screenshot = self.capture_screenshot()
        ui_hierarchy = self.extract_ui_hierarchy()
        
        return {
            'screenshot': screenshot,
            'ui_hierarchy': ui_hierarchy,
            'screen_size': screenshot.size,
            'timestamp': time.time()
        }
    
    def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Perception module cleanup completed")
