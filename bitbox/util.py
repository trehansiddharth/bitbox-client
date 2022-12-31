from typing import Optional, Callable, Dict
import typer
import getpass
import requests
import os
import json
import hashlib
import keyring
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
import cryptocode
from datetime import datetime
from bitbox.parameters import *
import bitbox.server as server
import sys
from bitbox.common import *
from bitbox.errors import *

def getPersonalKeyFromPassword(password: str) -> str:
  return hashlib.sha256(password.encode("utf-8")).hexdigest()

def getPersonalKey() -> str:
  password = getpass.getpass("Password: ")
  return getPersonalKeyFromPassword(password)

def getSession(userInfo: UserInfo) -> Optional[str]:
  return keyring.get_password("bitbox", f"session_{userInfo.username}")

def setSession(userInfo: UserInfo, session: str):
  keyring.set_password("bitbox", f"session_{userInfo.username}", session)

# Raises: ConfigParseFailed
def getUserInfo() -> Optional[UserInfo]:
  userInfoPath = os.path.join(BITBOX_CONFIG_FOLDER, "userinfo.json")
  if not os.path.exists(userInfoPath):
    return None
  try:
    with open(userInfoPath, "r") as f:
      userInfoJSON = f.read()
  except Exception as e:
    raise Exception(Error.CONFIG_PARSE_FAILED)
  return UserInfo(**json.loads(userInfoJSON))

# Raises: ConfigParseFailed
def getPublicKey(userInfo: UserInfo) -> RSA.RsaKey:
  publicKeyPath = os.path.join(BITBOX_CONFIG_FOLDER, userInfo.publicKeyPath)
  try:
    with open(publicKeyPath, "r") as f:
      publicKey = f.read()
  except Exception as e:
    raise Exception(Error.CONFIG_PARSE_FAILED)
  return RSA.import_key(publicKey)

# Raises: ConfigParseFailed, AuthenticationFailed
def getPrivateKey(userInfo: UserInfo, personalKey: str) -> RSA.RsaKey:
  privateKeyPath = os.path.join(BITBOX_CONFIG_FOLDER, userInfo.encryptedPrivateKeyPath)
  try:
    with open(privateKeyPath, "r") as f:
      encryptedPrivateKey = f.read()
    decryptedPrivateKey = cryptocode.decrypt(encryptedPrivateKey, personalKey)
  except Exception as e:
    raise Exception(Error.CONFIG_PARSE_FAILED)
  if decryptedPrivateKey == False:
    console = Console()
    console.print("Incorrect password!", style="red")
    sys.exit(1)
  return RSA.import_key(decryptedPrivateKey)

def rsaEncrypt(data: bytes, publicKey: RSA.RsaKey) -> bytes:
  cipher = PKCS1_OAEP.new(publicKey)
  return cipher.encrypt(data)

def rsaDecrypt(data: bytes, privateKey: RSA.RsaKey) -> bytes:
  cipher = PKCS1_OAEP.new(privateKey)
  return cipher.decrypt(data)

# Raises: AuthenticationFailed, UserNotFound, ConfigParseFailed, any Bitbox exception
# TODO: add exception handling
def attemptWithSession(f: Callable[[Session], requests.Response], session: Session,
  userInfo: UserInfo, personalKey: Optional[PersonalKey] = None,
  exceptions: Optional[Dict[str, Callable[[], None]]] = None) -> requests.Response:
  response = f(session)
  if (response.status_code != BITBOX_STATUS_OK):
    if response.text == Error.AUTHENTICATION_FAILED:
      if personalKey is None:
        personalKey = getPersonalKey()
      session = server.authenticateUser(userInfo, personalKey)
      setSession(userInfo, session)
      response = f(session)
      if (response.status_code != BITBOX_STATUS_OK):
        if response.text in exceptions:
          exceptions[response.text]()
        else:
          raise Exception(response.text)
        raise typer.Exit(1)
    else:
      if response.text in exceptions:
        exceptions[response.text]()
      else:
        raise Exception(response.text)
      raise typer.Exit(1)
  return response

def loginUser() -> tuple[UserInfo, Session]:
  userInfo = getUserInfo()
  if userInfo is None:
    console = Console()
    console.print("It looks like you haven't set up bitbox on this computer yet.\n")
    console.print("Run `bitbox setup` to get started!", style="green")
    sys.exit(0)
  session = getSession(userInfo)
  try:
    if session is None:
      personalKey = getPersonalKey()
      session = server.authenticateUser(userInfo, personalKey)
      setSession(userInfo, session)
    return userInfo, session
  except Exception as e:
    console = Console()
    if e.args[0] == Error.AUTHENTICATION_FAILED:
      console.print("Incorrect password!", style="red")
    else:
      console.print(f"An error occurred: {e}", style="red")
    sys.exit(0)
