from typing import Optional, Callable, Dict, Tuple, Union
import typer
import getpass
import requests
import os
import json
import hashlib
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
import cryptocode
from datetime import datetime
from bitbox.parameters import *
import bitbox.server as server
import sys
from bitbox.common import *
from bitbox.errors import *

BITBOX_KEYFILE_PATH = os.path.join(BITBOX_CONFIG_FOLDER, "keyfile.json")
BITBOX_SESSION_PATH = os.path.join(BITBOX_CONFIG_FOLDER, "session.str")

def getPersonalKeyFromPassword(password: str) -> str:
  return hashlib.sha256(password.encode("utf-8")).hexdigest()

def getPersonalKey() -> str:
  password = getpass.getpass("Password: ")
  return getPersonalKeyFromPassword(password)

def getSession(path: Optional[str] = None) -> Optional[str]:
  sessionPath = path or BITBOX_SESSION_PATH
  if os.path.exists(sessionPath):
    with open(sessionPath, "r") as f:
      return f.read()
  else:
    return None

def setSession(session: str, path: Optional[str] = None):
  sessionPath = path or BITBOX_SESSION_PATH
  with open(sessionPath, "w") as f:
    f.write(session)

# Raises: ConfigParseFailed
def getKeyInfo(path: Optional[str] = None) -> Optional[KeyInfo]:
  keyInfoPath = path or BITBOX_KEYFILE_PATH
  if not os.path.exists(keyInfoPath):
    return None
  try:
    with open(keyInfoPath, "r") as f:
      keyInfoJSON = f.read()
  except Exception as e:
    raise Exception(Error.CONFIG_PARSE_FAILED)
  return KeyInfo(**json.loads(keyInfoJSON))

def setKeyInfo(keyInfo: KeyInfo, path: Optional[str] = None):
  keyInfoPath = path or BITBOX_KEYFILE_PATH
  with open(keyInfoPath, "w") as f:
    f.write(json.dumps(keyInfo.__dict__, indent=2))

# Raises: ConfigParseFailed
def getPublicKey(keyInfo: KeyInfo) -> RSA.RsaKey:
  return RSA.import_key(keyInfo.publicKey)

# Raises: ConfigParseFailed, AuthenticationFailed
def getPrivateKey(keyInfo: KeyInfo, personalKey: Optional[str] = None) -> RSA.RsaKey:
  if keyInfo.encrypted:
    if personalKey == None:
      raise Exception
    else:
      privateKeyStr = cryptocode.decrypt(keyInfo.privateKey, personalKey)
  else:
    privateKeyStr = keyInfo.privateKey
  return RSA.import_key(privateKeyStr)

def rsaEncrypt(data: bytes, publicKey: RSA.RsaKey) -> bytes:
  cipher = PKCS1_OAEP.new(publicKey)
  return cipher.encrypt(data)

def rsaDecrypt(data: bytes, privateKey: RSA.RsaKey) -> bytes:
  cipher = PKCS1_OAEP.new(privateKey)
  return cipher.decrypt(data)

AuthMethod = Union[
  Literal['plain-key'],
  Literal['key-and-password'],
  Literal['prompt'],
]
def loginUser(authMethod: AuthMethod = 'prompt', keyfilePath: Optional[str] = None, password: Optional[str] = None, sessionPath: Optional[str] = None) -> AuthInfo:
  keyInfo = getKeyInfo(keyfilePath)
  # TODO: raise error instead of printing message
  if keyInfo is None:
    console = Console()
    console.print("It looks like you haven't set up bitbox on this computer yet.\n")
    console.print("Run `bitbox setup` to get started!", style="green")
    sys.exit(0)

  try:
    if authMethod == 'plain-key':
      if keyInfo.encrypted:
        raise Error.AUTH_METHOD_INVALID
      decryptKey = RSA.import_key
    elif authMethod == 'key-and-password':
      if (password is None) or (not keyInfo.encrypted):
        raise Error.AUTH_METHOD_INVALID
      personalKey = getPersonalKeyFromPassword(password)
      decryptKey = lambda keyStr: RSA.import_key(cryptocode.decrypt(keyStr, personalKey))
    elif authMethod == 'prompt':
      if not keyInfo.encrypted:
        raise Error.AUTH_METHOD_INVALID
      decryptKey = lambda keyStr: RSA.import_key(cryptocode.decrypt(keyStr, getPersonalKey()))
    privateKey = None
    session = getSession(sessionPath)
    if session is None:
      privateKey = decryptKey(keyInfo.privateKey)
      session = server.establishSession(keyInfo.username, privateKey)
    return AuthInfo(keyInfo, session, decryptKey, privateKey)
  except Exception as e:
    # TODO: raise error instead of printing message
    console = Console()
    if e.args[0] == Error.AUTHENTICATION_FAILED:
      console.print("Incorrect password!", style="red")
    else:
      console.print(f"An error occurred: {e}", style="red")
    sys.exit(0)


def fetchPrivateKey(authInfo: AuthInfo):
  # If we've already cached the private key, return it
  if authInfo.cachedPrivateKey is not None:
    return authInfo.cachedPrivateKey
  
  # Otherwise, get the private key using the decrypt function
  privateKey = authInfo.decryptPrivateKey(authInfo.keyInfo.privateKey)

  # Save it in the cache
  authInfo.cachedPrivateKey = privateKey

  # Return it
  return privateKey
