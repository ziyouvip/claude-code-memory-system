"""
Claude Code Memory System - Python Package
"""

__version__ = "1.0.0"

from .installer import install, uninstall, status
from .analyzer import analyze_observations, evolve_instincts
from .injector import inject_memories

__all__ = [
    "install",
    "uninstall",
    "status",
    "analyze_observations",
    "evolve_instincts",
    "inject_memories",
]
