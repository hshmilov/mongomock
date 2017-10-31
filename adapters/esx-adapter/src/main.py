"""
main.py Main file for running active directory plugin"
"""
from ESXAdapter import ESXAdapter

__author__ = "Mark Segal"

if __name__ == '__main__':
    # Initialize
    ESX_WRAPPER = ESXAdapter()
    # Run (Blocking)
    ESX_WRAPPER.start_serve()
