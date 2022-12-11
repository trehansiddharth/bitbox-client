from typing import Optional, Callable, Dict
import typer
import getpass
import requests
import os
import json
import hashlib
import keyring
from dataclasses import dataclass, asdict
import binascii
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
import cryptocode
from datetime import datetime
from parameters import *

@dataclass
class UserInfo:
  username: str
  clientCreated: int
  publicKeyPath: str
  encryptedPrivateKeyPath: str

PersonalKey = str
Session = str

@dataclass
class FileInfo:
  fileId: str
  name: str
  owner: str
  bytes: int
  lastModified: int
  encryptedKey: str

def getPersonalKeyFromPassword(password: str) -> str:
  return hashlib.sha256(password.encode("utf-8")).hexdigest()

def getPersonalKey() -> str:
  password = getpass.getpass("Password: ")
  return getPersonalKeyFromPassword(password)

# Raises: ConfigParseFailed
def getUserInfo() -> Optional[UserInfo]:
  userInfoPath = os.path.join(BITBOX_CONFIG_FOLDER, "userinfo.json")
  try:
    with open(userInfoPath, "r") as f:
      userInfoJSON = f.read()
  except Exception as e:
    raise Exception(BITBOX_ERR_CONFIG_PARSE_FAILED)
  return UserInfo(**json.loads(userInfoJSON))

# Raises: ConfigParseFailed
def getPublicKey(userInfo: UserInfo) -> RSA.RsaKey:
  publicKeyPath = os.path.join(BITBOX_CONFIG_FOLDER, userInfo.publicKeyPath)
  try:
    with open(publicKeyPath, "r") as f:
      publicKey = f.read()
  except Exception as e:
    raise Exception(BITBOX_ERR_CONFIG_PARSE_FAILED)
  return RSA.import_key(publicKey)

# Raises: ConfigParseFailed, AuthenticationFailed
def getPrivateKey(userInfo: UserInfo, personalKey: str) -> RSA.RsaKey:
  privateKeyPath = os.path.join(BITBOX_CONFIG_FOLDER, userInfo.encryptedPrivateKeyPath)
  try:
    with open(privateKeyPath, "r") as f:
      encryptedPrivateKey = f.read()
    decryptedPrivateKey = cryptocode.decrypt(encryptedPrivateKey, personalKey)
    if (decryptedPrivateKey == False):
      raise Exception(BITBOX_ERR_AUTHENTICATION_FAILED)
  except Exception as e:
    raise Exception(BITBOX_ERR_CONFIG_PARSE_FAILED)
  return RSA.import_key(decryptedPrivateKey)

def rsaEncrypt(data: bytes, publicKey: RSA.RsaKey) -> bytes:
  cipher = PKCS1_OAEP.new(publicKey)
  return cipher.encrypt(data)

def rsaDecrypt(data: bytes, privateKey: RSA.RsaKey) -> bytes:
  cipher = PKCS1_OAEP.new(privateKey)
  return cipher.decrypt(data)

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
  return datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

# Raises: AuthenticationFailed, UserNotFound, ConfigParseFailed
def authenticateUser(userInfo: UserInfo, personalKey: str) -> str:
  privateKey = getPrivateKey(userInfo, personalKey)

  challengeBody = {
    "username": userInfo.username
  }
  challengeResponse = requests.post(
    f"http://{BITBOX_HOST}/api/auth/login/challenge",
    json=challengeBody)
  if challengeResponse.status_code != BITBOX_STATUS_OK:
    raise Exception(challengeResponse.text)
  challenge = challengeResponse.text
  
  challengeBytes = bytearray.fromhex(challenge)
  try:
    answerBytes = rsaDecrypt(challengeBytes, privateKey)
  except:
    raise Exception(BITBOX_ERR_AUTHENTICATION_FAILED)
  answer = binascii.hexlify(answerBytes).decode("utf-8")

  loginBody = {
    "username": userInfo.username,
    "challengeResponse": answer
  }
  loginResponse = requests.post(
    f"http://{BITBOX_HOST}/api/auth/login/login",
    json=loginBody)
  if loginResponse.status_code != BITBOX_STATUS_OK:
    raise Exception(loginResponse.text)
  return loginResponse.headers['set-cookie']

# Raises: AuthenticationFailed, UserNotFound, ConfigParseFailed
def loginUser() -> tuple[UserInfo, Session]:
  userInfo = getUserInfo()
  if userInfo is None:
    raise Exception(BITBOX_ERR_CONFIG_PARSE_FAILED)
  session = keyring.get_password("bitbox", "session")
  if session is None:
    personalKey = getPersonalKey()
    session = authenticateUser(userInfo, personalKey)
    keyring.set_password("bitbox", "session", session)
  return userInfo, session

# Raises: AuthenticationFailed, UserNotFound, ConfigParseFailed, any Bitbox exception
# TODO: add exception handling
def attemptWithSession(f: Callable[[Session], requests.Response], session: Session,
  userInfo: UserInfo, personalKey: Optional[PersonalKey] = None,
  exceptions: Optional[Dict[str, Callable[[], None]]] = None) -> requests.Response:
  response = f(session)
  if (response.status_code != BITBOX_STATUS_OK):
    if response.text == BITBOX_ERR_AUTHENTICATION_FAILED:
      if personalKey is None:
        personalKey = getPersonalKey()
      session = authenticateUser(userInfo, personalKey)
      keyring.set_password("bitbox", "session", session)
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