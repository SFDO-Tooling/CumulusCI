"""
This file is needed as an entry point for building with pyinstaller. There is
no need to use this file as part of normal usage. Use the entry points defined
in setup.py instead.
"""

from cumulusci.cli.cli import cli

cli()
