"""CLI helper utilities for the plant controller."""

import os

CANCELLATION_KEYWORDS = ['stop', 'exit', 'cancel', 'quit']

def clear_screen():
    """Clear the terminal screen (cross-platform)."""
    os.system('cls' if os.name == 'nt' else 'clear')