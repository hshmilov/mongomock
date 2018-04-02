"""Installer for the Axonius Libs."""

__author__ = "Axonius, Inc"

from setuptools import setup

setup(
    name="Axonius",
    packages=["axonius", "axonius.mixins", "axonius.consts", "axonius.devices", "axonius.utils", "axonius.users",
              "axonius.logging"],
    version="1.0.0",
    description="External libs for Axonius",
    author="Axonius, Inc",
    author_email="contact@axonius.com",
    url="https://www.axonius.com",
    download_url="",
    keywords=["Axonius", "Plugin", "Adapter", "IT"],
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
    long_description="""Will install all Axonius libs. For example, the PluginBase class""",
    install_requires=['json_log_formatter==0.2.0', 'Flask==0.12.2', 'elasticsearch==5.4.0', 'elasticsearch_dsl==5.3.0',
                      'requests==2.18.4']
)
