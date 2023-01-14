from bitbox.parameters import *
from bitbox.encryption import *
from bitbox.common import *
from bitbox.server import Error
from bitbox.cli.otc_dict import otcDict
import bitbox.lib as lib
import time
import typer
import requests
import os
import random
import json
import re
from rich.console import Console
from rich.table import Table
import enum
from typing import Optional, List, Any, Dict
from datetime import datetime
import sys

#
# Parameters
#

BITBOX_CONFIG_FOLDER = os.environ.get("BITBOX_CONFIG_FOLDER") or os.path.join(os.path.expanduser("~"), ".bitbox")
BITBOX_KEYFILE_PATH = os.path.join(BITBOX_CONFIG_FOLDER, "keyfile.json")
BITBOX_SESSION_PATH = os.path.join(BITBOX_CONFIG_FOLDER, "session.str")
OTC_WORDS = 6
BITBOX_USERNAME_REGEX = r"^[a-z0-9]+$"
BITBOX_FILENAME_REGEX = r"^@[a-z0-9]+\/[^\/\r\n ]+$"
BITBOX_SYNCS_FOLDER = os.path.join(BITBOX_CONFIG_FOLDER, "syncs")
BITBOX_SYNC_INFO_PATH = os.path.join(BITBOX_CONFIG_FOLDER, "syncinfo.json")

#
# Global variables
#

console = Console()


#
# Exceptions
#

class ConfigParseException(Exception):
  def __init__(self, filename: str, message: any):
    self.filename = filename
    self.message = message

#
# Configuration
#

def getSession(path: Optional[str] = None) -> Optional[Session]:
  try:
    sessionPath = path or BITBOX_SESSION_PATH
    if os.path.exists(sessionPath):
      with open(sessionPath, "r") as f:
        return f.read()
    else:
      return None
  except Exception as e:
    raise ConfigParseException(BITBOX_SESSION_PATH, e)

def setSession(session: Session, path: Optional[str] = None):
  try:
    sessionPath = path or BITBOX_SESSION_PATH
    with open(sessionPath, "w") as f:
      f.write(session)
  except Exception as e:
    raise ConfigParseException(BITBOX_SESSION_PATH, e)

def getKeyInfo(path: Optional[str] = None) -> Optional[KeyInfo]:
  keyInfoPath = path or BITBOX_KEYFILE_PATH
  if not os.path.exists(keyInfoPath):
    return None
  try:
    with open(keyInfoPath, "r") as f:
      keyInfoJSON = f.read()
  except Exception as e:
    raise ConfigParseException(BITBOX_KEYFILE_PATH, e)
  return KeyInfo(**json.loads(keyInfoJSON))

def setKeyInfo(keyInfo: KeyInfo, path: Optional[str] = None):
  try:
    keyInfoPath = path or BITBOX_KEYFILE_PATH
    with open(keyInfoPath, "w") as f:
      f.write(json.dumps(keyInfo.__dict__, indent=2))
  except Exception as e:
    raise ConfigParseException(BITBOX_KEYFILE_PATH, e)

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

def handleLoginUser() -> AuthInfo:
  # Get key info
  keyInfo = getKeyInfo()
  if (not keyInfo):
    console.print("It looks like you haven't set up bitbox on this computer yet.\n")
    console.print("Run `bitbox setup` to get started!", style="green")
    typer.Exit()
  
  # Get existing session, if any
  session = getSession()

  # Try to login with the key info and session
  try:
    return lib.login(keyInfo, None, session=session)
  except Exception as e:
    # Print an error message if login fails
    if e.args[0] == Error.AUTHENTICATION_FAILED:
      error("Incorrect password!")
    else:
      error(f"An error occurred: {e}")

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

def printFilesInfo(username: str, filesInfo: List[FileInfo]) -> None:
  table = Table()
  table.add_column("Remote Filename")
  table.add_column("Size")
  table.add_column("Last Modified")
  table.add_column("Shared With")
  for fileInfo in filesInfo:
    if fileInfo.owner != username:
      filename = f"@{fileInfo.owner}/{fileInfo.name}"
    else:
      filename = fileInfo.name
    sharedWith = []
    if (username in fileInfo.sharedWith) and (username != fileInfo.owner):
      sharedWith.append("me")
    for username in fileInfo.sharedWith:
      if (username != fileInfo.owner) and (username != username):
        sharedWith.append(f"@{username}")
    table.add_row(
      filename,
      humanReadableFilesize(fileInfo.bytes),
      humanReadableJSTimestamp(fileInfo.lastModified),
      ", ".join(sharedWith))
  console.print(table)

def createOTC() -> str:
  # Select 4 random words from the dictionary
  otcWords = random.choices(list(otcDict.values()), k=OTC_WORDS)

  # Return a concatenation of the words
  return " ".join(otcWords).lower()

def guard(value: Any, exceptions: Dict[str, str] = {}) -> None:
  if not isinstance(value, Error):
    return
  console = Console()
  console.print(f"ERROR: {exceptions[value] if value in exceptions else value}", style="red")
  sys.exit(1)
