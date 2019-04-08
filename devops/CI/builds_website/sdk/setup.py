"""Installer for the Axonius Builds framework."""

__author__ = "Axonius, Inc"

from setuptools import setup

setup(
    name="builds",
    packages=["builds"],
    version="1.0.0",
    description="Axonius Builds Framework",
    author="Axonius, Inc",
    author_email="contact@axonius.com",
    url="https://www.axonius.com",
    download_url="",
    keywords=[],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 1 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    long_description="""Will install all Axonius Builds Framework.""",
    install_requires=['requests', 'paramiko']
)
