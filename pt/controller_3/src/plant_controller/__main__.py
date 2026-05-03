#!/usr/bin/env python3

import sys
import anyio

if __package__ is None and not getattr(sys, 'frozen', False):
    # direct call of __main__.py
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import plant_controller

if __name__ == "__main__":
    try:
        anyio.run(plant_controller.main)
    except KeyboardInterrupt:
        print("Goodbye for now!")