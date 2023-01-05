from dataclasses import dataclass
from typing import TypeVar, Dict, Any, Optional, Generic, Literal, List, Callable
import sys
from rich.console import Console
from bitbox.parameters import *
import time
from bitbox.errors import *
from Crypto.PublicKey import RSA

# A unique hex string for each time the program is run, used for logging
CURRENT_CONTEXT = hex(round(time.time() * 1000))[2:]

PersonalKey = str
Session = str

@dataclass
class KeyInfo:
  username: str
  clientCreated: int
  publicKey: str
  privateKey: str
  encrypted: bool

@dataclass
class AuthInfo:
  keyInfo: KeyInfo
  session: str
  decryptPrivateKey: Callable[[str], RSA.RsaKey]
  cachedPrivateKey: Optional[RSA.RsaKey]

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
