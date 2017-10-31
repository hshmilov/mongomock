"""
The purpose of this file is to export the PuppetPlugin exceptions.
"""

__author__ = 'Ofri Shur'


class PuppetException(Exception):
    def __init__(self, message=""):
        super().__init__(message)
