"""A package for controlling core and plugins docker environments."""
from .environmentmanager import EnvironmentManager
from . import exceptions, dockermanager
__author__ = 'Avidor Bartov'

# Set DockerManager available at the package level.
__all__ = ['EnvironmentManager', 'exceptions', 'dockermanager']
