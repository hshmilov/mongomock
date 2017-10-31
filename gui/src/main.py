"""
main.py Main file for running active directory plugin"
"""
from GUIPlugin import GUIPlugin

__author__ = "Mark Segal"

if __name__ == '__main__':
    # Initialize
    GUI = GUIPlugin()
    # Run (Blocking)
    GUI.start_serve()
