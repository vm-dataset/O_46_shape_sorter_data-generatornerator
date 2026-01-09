"""
Shape Sorter Task implementation.

This module contains the shape sorter task generator that creates
2D shape matching puzzles where colored cards must be matched to outline slots.

Key files:
    - config.py   : Shape sorter configuration (TaskConfig)
    - generator.py: Shape sorter generation logic (TaskGenerator)
    - prompts.py  : Shape sorter prompt templates (get_prompt)
"""

from .config import TaskConfig
from .generator import TaskGenerator
from .prompts import get_prompt

__all__ = ["TaskConfig", "TaskGenerator", "get_prompt"]
