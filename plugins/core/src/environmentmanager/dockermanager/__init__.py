"""A package for controlling docker environments."""
# Set DockerManager available at the package level.
from .dockermanager import DockerManager
from . import exceptions

__author__ = 'Avidor Bartov'

__all__ = ['DockerManager', 'exceptions']
