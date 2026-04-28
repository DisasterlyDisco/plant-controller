"""
AD20P-1230E Pump implementation.

This module provides the pump control for AD20P-1230E 12V submersible pumps.
The CS_IO404_Based_AD20P_1230E class has been moved to cs_io404.py with
full MODBUS RTU implementation.

For new implementations, use:
    from plant_controller.pumps.cs_io404 import CS_IO404Based_AD20P_1230E

This file is kept for backward compatibility.
"""

# Re-export the implementation from cs_io404.py
from .cs_io404 import CS_IO404Based_AD20P_1230E as CS_IO404_Based_AD20P_1230E

__all__ = ['CS_IO404_Based_AD20P_1230E']
