"""Installer for the Axonius Libs."""

__author__ = "Axonius, Inc"

from setuptools import setup

setup(
    name="Axonius",
    packages=["axonius", "axonius.mixins", "axonius.consts", "axonius.devices", "axonius.utils", "axonius.users",
              "axonius.pql",
              "axonius.logging", "axonius.types", "axonius.clients",
              "axonius.clients.service_now",
              "axonius.clients.fresh_service",
              "axonius.clients.rest",
              "axonius.clients.mssql",
              "axonius.clients.ldap",
              "axonius.clients.cisco",
              "axonius.clients.sysaid",
              "axonius.async"],
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
    install_requires=['json_log_formatter==0.2.0', 'Flask==0.12.2', 'Werkzeug==0.16.0'],
    data_files=[('axonius', ['axonius/oui.csv'])]
)
