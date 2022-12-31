import time
import typer
import requests
import os
import random
import string
import json
from dataclasses import asdict
import binascii
from Crypto.PublicKey import RSA
from cryptography.fernet import Fernet
import re
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from commands.otc_dict import otcDict
from parameters import *
from util import *
from commands import *
import server
from common import *
import enum
from typing import Optional

#
# Global variables
#

app = typer.Typer()
console = Console()

#
# Printing
#

class PrintMode(enum.Enum):
  DEFAULT = "default"
  SUCCESS = "success"
  WARNING = "warning"
  ERROR = "error"

def print(message: str, mode : PrintMode = PrintMode.DEFAULT):
  if mode == PrintMode.DEFAULT:
    console.print(message)
  elif mode == PrintMode.SUCCESS:
    success(message)
  elif mode == PrintMode.WARNING:
    warning(message)
  elif mode == PrintMode.ERROR:
    error(message)

def success(message: str):
  console.print(f"{message}", style="green")

def warning(message: str):
  console.print(f"{message}", style="yellow")

def error(message: str):
  console.print(f"{message}", style="red")
  raise typer.Exit(code=1)

#
# Utility functions
#

def confirmLocalFileExists(file: str):
  if (not os.path.isfile(file)):
    if (os.path.isdir(file)):
      error(f"Local file '{file}' is a directory, whereas file was expected.")
    else:
      error(f"Local file '{file}' does not exist.")

def parseRemoteFilename(remote: str, defaultOwner: Optional[str] = None):
    # Parse the remote file name as either the owner's username and filename or just a filename
  if (re.match(BITBOX_FILENAME_REGEX, remote)):
    splitFile = remote.split("/")
    owner = splitFile[0][1:]
    filename = splitFile[1]
  else:
    owner = defaultOwner
    filename = remote
  return owner, filename

def renderRemoteFilename(remote: str, owner: Optional[str] = None):
  if (owner):
    return f"@{owner}/{remote}"
  else:
    return remote

def uploadFile(uploadURL: str, encryptedFileBytes: bytes) -> None:
  # Print a progress message, if the file is more than 1 MiB
  if (len(encryptedFileBytes) > 1024 ** 2):
    console.print(f"Uploading file...", end="")
  
  # Create a resumable session
  resumableSession = requests.post(uploadURL, "", headers={
      "x-goog-resumable": "start",
      "content-type": "text/plain",
      "x-goog-content-length-range": f"0,{len(encryptedFileBytes)}"
  })
  if resumableSession.status_code != 201:
    console.print("Error while uploading file.", style="red")
    console.print(resumableSession.text)
    raise typer.Exit(code=1)

  # Get the location to upload to
  location = resumableSession.headers["location"]

  # Upload to that location via a PUT request
  uploadResponse = requests.put(location, data=encryptedFileBytes, headers={
    "content-type": "text/plain",
    "content-length": str(len(encryptedFileBytes))
  })

  # End the progress message, if the file is more than 1 MiB
  if (len(encryptedFileBytes) > 1024 ** 2):
    console.print(" Done.")
  
  # Check if the upload was successful
  if uploadResponse.status_code != 200:
    console.print("Error while uploading file.", style="red")
    console.print(uploadResponse.text)
    raise typer.Exit(code=1)

def humanReadableFilesize(bytes: int) -> str:
  if bytes < 1024:
    return f"{bytes} B"
  elif bytes < 1024 ** 2:
    return f"{bytes / 1024:.1f} KiB"
  elif bytes < 1024 ** 3:
    return f"{bytes / 1024 ** 2:.1f} MiB"
  else:
    return f"{bytes / 1024 ** 3:.1f} GiB"

def humanReadableJSTimestamp(timestamp: int) -> str:
  minute = 60 * 1000
  hour = 60 * minute
  now = int(time.time() * 1000)
  elapsed = now - timestamp
  if (elapsed < 24 * hour):
    if (elapsed < hour):
      if (elapsed < minute):
        return "Just now"
      else:
        return f"{int(elapsed / minute)} minutes ago"
    else:
      return f"{int(elapsed / hour)} hours ago"
  else:
    return datetime.utcfromtimestamp(timestamp / 1000).strftime("%a, %b %d, %Y")

def printFilesInfo(userInfo: UserInfo, filesInfo: list[FileInfo]) -> None:
  table = Table()
  table.add_column("Remote Filename")
  table.add_column("Size")
  table.add_column("Last Modified")
  table.add_column("Shared With")
  for fileInfo in filesInfo:
    if fileInfo.owner != userInfo.username:
      filename = f"@{fileInfo.owner}/{fileInfo.name}"
    else:
      filename = fileInfo.name
    sharedWith = []
    if (userInfo.username in fileInfo.sharedWith) and (userInfo.username != fileInfo.owner):
      sharedWith.append("me")
    for username in fileInfo.sharedWith:
      if (username != fileInfo.owner) and (username != userInfo.username):
        sharedWith.append(f"@{username}")
    table.add_row(
      filename,
      humanReadableFilesize(fileInfo.bytes),
      humanReadableJSTimestamp(fileInfo.lastModified),
      ", ".join(sharedWith))
  console.print(table)
