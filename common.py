from dataclasses import dataclass
from typing import TypeVar, Dict, Any, Optional, Generic, Literal
import sys
from rich.console import Console
from parameters import *

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
  sharedWith: list[str]

Session = str

def guard(value: Any, exceptions: Dict[str, str] = {}) -> None:
  if not isinstance(value, Error):
    return
  console = Console()
  console.print(f"ERROR: {exceptions[value] if value in exceptions else value}", style="red")
  sys.exit(1)
