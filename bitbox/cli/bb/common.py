from bitbox.cli.common import *
import typer
from dataclasses import dataclass
import os

#
# Parameters
#

BB_CONFIG_FOLDER = os.environ.get("BB_CONFIG_FOLDER") or os.path.join(os.path.expanduser("~"), ".bb")

#
# Global variables
#

app = typer.Typer()
config = Config(BB_CONFIG_FOLDER)

#
# Utility functions
#

@dataclass
class Clip:
  filename: str
  content: bytes

def clipToBlob(clip: Clip) -> bytes:
  return f"{os.path.basename(clip.filename)}\0".encode("utf-8") + clip.content

def blobToClip(blob: bytes) -> Clip:
  sepIndex = blob.index(b"\0")
  filename = blob[:sepIndex].decode("utf-8")
  content = blob[sepIndex+1:]
  return Clip(filename=filename, content=content)
