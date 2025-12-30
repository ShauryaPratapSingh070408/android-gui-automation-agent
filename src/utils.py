"""Utility functions for the automation agent."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    level: str = 'INFO',
    log_file: Optional[Path] = None
) -> logging.Logger:
    """Setup a logger with consistent formatting.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def parse_coordinates(coord_str: str) -> tuple:
    """Parse coordinate string like '100,200' to tuple.
    
    Args:
        coord_str: Coordinate string
        
    Returns:
        Tuple of (x, y)
    """
    try:
        x, y = map(int, coord_str.split(','))
        return (x, y)
    except:
        return (0, 0)


def format_action_history(history: list, max_items: int = 5) -> str:
    """Format action history for display.
    
    Args:
        history: List of action records
        max_items: Maximum items to include
        
    Returns:
        Formatted string
    """
    recent = history[-max_items:] if len(history) > max_items else history
    
    formatted = "Action History:\n"
    for record in recent:
        action = record['action']
        status = '✓' if record['success'] else '✗'
        formatted += f"  {status} Step {record['step']}: {action['type']}\n"
    
    return formatted
