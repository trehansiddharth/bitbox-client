from bitbox.cli.common import *
import typer
import os

#
# Parameters
#

BITBOX_CONFIG_FOLDER = os.environ.get("BITBOX_CONFIG_FOLDER") or os.path.join(os.path.expanduser("~"), ".bitbox")

#
# Global variables
#

app = typer.Typer()
config = Config(BITBOX_CONFIG_FOLDER)
