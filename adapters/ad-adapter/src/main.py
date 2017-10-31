"""main.py: Main file for running active directory plugin"""
# TODO ofir: Change the return values protocol

__author__ = "Ofir Yefet"

from ActiveDirectoryPlugin import ActiveDirectoryPlugin

if __name__ == '__main__':
    # Initialize
    AD_WRAPPER = ActiveDirectoryPlugin()
    
    # Run (Blocking)
    AD_WRAPPER.start_serve()
