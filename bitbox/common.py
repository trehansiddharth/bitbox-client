from dataclasses import dataclass
from typing import TypeVar, Dict, Any, Optional, Generic, Literal, List
import sys
from rich.console import Console
from bitbox.parameters import *
import time
from bitbox.errors import *

# A unique hex string for each time the program is run, used for logging
CURRENT_CONTEXT = hex(round(time.time() * 1000))[2:]

@dataclass
class UserInfo:
  username: str
  clientCreated: int
  publicKeyPath: str
  encryptedPrivateKeyPath: str

@dataclass
class AuthInfo:
  userInfo: UserInfo
  session: str
  personalKey: Optional[str] = None

PersonalKey = str
Session = str

@dataclass
class BasicFileInfo:
  fileId: str
  name: str
  owner: str
  bytes: int
  lastModified: int
  encryptedKey: str
  hash: str

@dataclass
class FileInfo(BasicFileInfo):
  sharedWith: List[str]

Session = str

def guard(value: Any, exceptions: Dict[str, str] = {}) -> None:
  if not isinstance(value, Error):
    return
  console = Console()
  console.print(f"ERROR: {exceptions[value] if value in exceptions else value}", style="red")
  sys.exit(1)
