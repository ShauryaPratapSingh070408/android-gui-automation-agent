"""Utility functions for the agent"""

import yaml
import logging
from pathlib import Path
from typing import Dict
from datetime import datetime


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file"""
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def setup_logging(config: Dict) -> logging.Logger:
    """Setup logging configuration"""
    log_config = config['logging']
    log_level = getattr(logging, log_config['level'].upper())
    
    # Create logs directory
    log_file = Path(log_config['log_file'])
    log_file.parent.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('gui_agent')


def save_task_report(task_description: str, steps: list, success: bool, output_dir: str = "test_results"):
    """Save task execution report"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_path / f"task_report_{timestamp}.md"
    
    with open(report_file, 'w') as f:
        f.write(f"# Task Execution Report\n\n")
        f.write(f"**Task**: {task_description}\n\n")
        f.write(f"**Status**: {'✅ Success' if success else '❌ Failed'}\n\n")
        f.write(f"**Timestamp**: {timestamp}\n\n")
        f.write(f"## Execution Steps\n\n")
        
        for i, step in enumerate(steps, 1):
            f.write(f"### Step {i}\n")
            f.write(f"- **Action**: {step.get('action', 'N/A')}\n")
            f.write(f"- **Reasoning**: {step.get('reasoning', 'N/A')}\n")
            f.write(f"- **Result**: {step.get('result', 'N/A')}\n\n")
    
    return str(report_file)
