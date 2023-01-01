import requests
from bitbox.parameters import *
from dataclasses import dataclass
from typing import Dict, Union, Any, List, Literal
import sys
from rich.console import Console
from Crypto.PublicKey import RSA
from bitbox.common import *
import bitbox.util as util
import binascii
from bitbox.errors import *

def err(value: Any, errs: List[Error] = []) -> bool:
  if isinstance(value, Error):
    if errs == []:
      return True
    else:
      return value in errs

def printServerError() -> None:
  console = Console()
  console.print("An error occurred on the server", style="red")
  sys.exit(1)

def printInvalidVersionError() -> None:
  console = Console()
  console.print("Your Bitbox version is invalid. Please update to the latest version.", style="red")
  sys.exit(1)

#
# Get User Info
#

@dataclass
class UserInfoResponse:
  publicKey: str

UserInfoError = Literal[Error.USER_NOT_FOUND]

def userInfo(username: str) -> Union[UserInfoResponse, UserInfoError]:
  response = requests.post(f"http://{BITBOX_HOST}/api/info/user", json={ "username" : username })
  if response.status_code == BITBOX_STATUS_OK:
    return UserInfoResponse(**response.json())
  elif response.text == Error.SERVER_SIDE_ERROR.value:
    printServerError()
  else:
    return Error(response.text)

#
# Register User
#

RegisterUserError = Union[
  Literal[Error.USER_EXISTS],
  Literal[Error.INVALID_USERNAME],
  Literal[Error.INVALID_PUBLIC_KEY]
]

def registerUser(username: str, publicKey: str, encryptedPrivateKey: str) -> Union[None, RegisterUserError]:
  registerUserBody = {
    "username": username,
    "publicKey": publicKey,
    "encryptedPrivateKey": encryptedPrivateKey,
    "version": BITBOX_VERSION,
  }
  response = requests.post(f"http://{BITBOX_HOST}/api/auth/register/user", json=registerUserBody)
  if response.status_code == BITBOX_STATUS_OK:
    return None
  elif response.text == Error.INVALID_VERSION.value:
    printInvalidVersionError()
  elif response.text == Error.SERVER_SIDE_ERROR.value:
    printServerError()
  else:
    return Error(response.text)

#
# Generate OTC
#

GenerateOTCResponse = str

def generateOTC(authInfo: AuthInfo) -> GenerateOTCResponse:
  response = requestWithSession("GET", f"http://{BITBOX_HOST}/api/auth/recover/generate-otc", None, authInfo)
  if response.status_code == BITBOX_STATUS_OK:
    return response.text
  else:
    printServerError()

#
# Recover Keys
#

RecoverKeysError = Union[
  Literal[Error.USER_NOT_FOUND],
  Literal[Error.OTC_NOT_GENERATED],
  Literal[Error.INVALID_OTC]
]

def recoverKeys(username: str, otc: str) -> Union[str, RecoverKeysError]:
  recoverKeysBody = {
    "username": username,
    "otc": otc,
    "version": BITBOX_VERSION
  }
  response = requests.post(f"http://{BITBOX_HOST}/api/auth/recover/recover-keys", json=recoverKeysBody)
  if response.status_code == BITBOX_STATUS_OK:
    return response.text
  elif response.text == Error.INVALID_VERSION.value:
    printInvalidVersionError()
  elif response.text == Error.SERVER_SIDE_ERROR.value:
    printServerError()
  else:
    return Error(response.text)

#
# Challenge
#

ChallengeResponse = str

ChallengeError = Literal[Error.USER_NOT_FOUND]

def challenge(username: str) -> Union[ChallengeResponse, ChallengeError]:
  challengeBody = {
    "username": username
  }
  response = requests.post(f"http://{BITBOX_HOST}/api/auth/login/challenge", json=challengeBody)
  if response.status_code == BITBOX_STATUS_OK:
    return response.text
  elif response.text == Error.SERVER_SIDE_ERROR.value:
    printServerError()
  else:
    return Error(response.text)

#
# Login
#

LoginError = Union[
  Literal[Error.USER_NOT_FOUND],
  Literal[Error.AUTHENTICATION_FAILED]
]

def login(username: str, challengeResponse: str) -> Union[Session, LoginError]:
  loginBody = {
    "username": username,
    "challengeResponse": challengeResponse,
    "version": BITBOX_VERSION
  }
  response = requests.post(f"http://{BITBOX_HOST}/api/auth/login/login", json=loginBody)
  if response.status_code == BITBOX_STATUS_OK:
    return response.headers["set-cookie"]
  elif response.text == Error.INVALID_VERSION.value:
    printInvalidVersionError()
  elif response.text == Error.SERVER_SIDE_ERROR.value:
    printServerError()
  else:
    return Error(response.text)

#
# Prepare Store
#

@dataclass
class PrepareStoreResponse:
  fileId: str
  uploadURL: str

PrepareStoreError = Union[
  Literal[Error.INVALID_NUM_BYTES],
  Literal[Error.FILE_TOO_LARGE],
  Literal[Error.FILE_EXISTS]
]

def prepareStore(filename: str, bytes: int, hash: str, personalEncryptedKey: str, authInfo: AuthInfo) -> Union[PrepareStoreResponse, PrepareStoreError]:
  prepareStoreBody = {
    "filename": filename,
    "bytes": bytes,
    "hash": hash,
    "personalEncryptedKey": personalEncryptedKey
  }
  response = requestWithSession("POST",
    f"http://{BITBOX_HOST}/api/storage/prepare-store",
    prepareStoreBody,
    authInfo)
  if isinstance(response, Error):
    if response == Error.SERVER_SIDE_ERROR:
      printServerError()
    else:
      return response
  else:
    return PrepareStoreResponse(**response.json())

#
# Prepare Update
#

@dataclass
class PrepareUpdateResponse:
  uploadURL: str

PrepareUpdateError = Union[
  Literal[Error.INVALID_NUM_BYTES],
  Literal[Error.FILE_TOO_LARGE],
  Literal[Error.FILE_NOT_READY],
  Literal[Error.FILE_NOT_FOUND]
]

def prepareUpdate(fileId: str, bytes: int, hash: str, authInfo: AuthInfo) -> Union[PrepareUpdateResponse, PrepareUpdateError]:
  prepareUpdateBody = {
    "fileId": fileId,
    "bytes": bytes,
    "hash": hash
  }
  response = requestWithSession("POST",
    f"http://{BITBOX_HOST}/api/storage/prepare-update",
    prepareUpdateBody,
    authInfo)
  if isinstance(response, Error):
    if response == Error.SERVER_SIDE_ERROR:
      printServerError()
    else:
      return response
  else:
    return PrepareUpdateResponse(**response.json())

#
# Store
#

StoreError = Union[
  Literal[Error.FILE_NOT_FOUND],
  Literal[Error.ACCESS_DENIED]
]

def store(fileId: str, authInfo: AuthInfo) -> Union[None, StoreError]:
  storeBody = {
    "fileId": fileId
  }
  response = requestWithSession("POST",
    f"http://{BITBOX_HOST}/api/storage/store",
    storeBody,
    authInfo)
  if isinstance(response, Error):
    if response == Error.SERVER_SIDE_ERROR:
      printServerError()
    else:
      return response

#
# Share
#

ShareError = Union[
  Literal[Error.FILE_NOT_FOUND],
  Literal[Error.USER_NOT_FOUND]
]

def share(fileId: str, recipientEncryptedKeys: Dict[str, str], authInfo: AuthInfo) -> Union[None, ShareError]:
  shareBody = {
    "fileId": fileId,
    "recipientEncryptedKeys": recipientEncryptedKeys
  }
  response = requestWithSession("POST",
    f"http://{BITBOX_HOST}/api/storage/share",
    shareBody,
    authInfo)
  if isinstance(response, Error):
    if response == Error.SERVER_SIDE_ERROR:
      printServerError()
    else:
      return response

#
# Save
#

@dataclass
class SaveResponse:
  downloadURL: str
  encryptedKey: str
  hash: str

SaveError = Union[
  Literal[Error.FILE_NOT_FOUND],
  Literal[Error.FILE_NOT_READY]
]

def save(fileId: str, authInfo: AuthInfo) -> Union[SaveResponse, SaveError]:
  saveBody = {
    "fileId": fileId
  }
  response = requestWithSession("POST",
    f"http://{BITBOX_HOST}/api/storage/save",
    saveBody,
    authInfo)
  if isinstance(response, Error):
    if response == Error.SERVER_SIDE_ERROR:
      printServerError()
    else:
      return response
  else:
    return SaveResponse(**response.json())

#
# Delete
#

DeleteError = Union[
  Literal[Error.FILE_NOT_FOUND],
  Literal[Error.FILE_NOT_READY]
]

def delete(fileId: str, authInfo: AuthInfo) -> Union[None, DeleteError]:
  deleteBody = {
    "fileId": fileId
  }
  response = requestWithSession("POST",
    f"http://{BITBOX_HOST}/api/storage/delete",
    deleteBody,
    authInfo)
  if isinstance(response, Error):
    if response == Error.SERVER_SIDE_ERROR:
      printServerError()
    else:
      return response

#
# File Info
#

FileInfoResponse = FileInfo

FileInfoError = Union[
  Literal[Error.USER_NOT_FOUND],
  Literal[Error.FILE_NOT_FOUND],
  Literal[Error.FILENAME_NOT_SPECIFIC]
]

def fileInfo(filename: str, owner: Optional[str], authInfo: AuthInfo) -> Union[FileInfoResponse, FileInfoError]:
  fileInfoBody = {
    "filename": filename
  }
  if owner is not None:
    fileInfoBody["owner"] = owner
  response = requestWithSession("POST",
    f"http://{BITBOX_HOST}/api/info/file",
    fileInfoBody,
    authInfo)
  if isinstance(response, Error):
    if response == Error.SERVER_SIDE_ERROR:
      printServerError()
    else:
      return response
  else:
    return FileInfoResponse(**response.json())

def fileInfoById(fileId: str, authInfo: AuthInfo) -> Union[FileInfoResponse, FileInfoError]:
  fileInfoBody = {
    "fileId": fileId
  }
  response = requestWithSession("POST",
    f"http://{BITBOX_HOST}/api/info/file",
    fileInfoBody,
    authInfo)
  if isinstance(response, Error):
    if response == Error.SERVER_SIDE_ERROR:
      printServerError()
    else:
      return response
  else:
    return FileInfoResponse(**response.json())

#
# Files Info
#

FilesInfoResponse = List[FileInfo]

def filesInfo(authInfo: AuthInfo) -> FilesInfoResponse:
  response = requestWithSession("GET",
    f"http://{BITBOX_HOST}/api/info/files",
    None,
    authInfo)
  if isinstance(response, Error):
    printServerError()
  else:
    return [FileInfoResponse(**fileInfo) for fileInfo in response.json()]

#
# Log Command
#

def logCommand(data: str, username: str) -> None:
  logCommandBody = {
    "data": data,
    "username": username,
    "context": CURRENT_CONTEXT
  }
  response = requests.post(f"http://{BITBOX_HOST}/api/log/command", json=logCommandBody)
  print(response.text)
  if response.status_code != BITBOX_STATUS_OK:
    printServerError()

#
# Log Error
#

def logError(data: str, username: str) -> None:
  logErrorBody = {
    "data": data,
    "username": username,
    "context": CURRENT_CONTEXT
  }
  response = requests.post(f"http://{BITBOX_HOST}/api/log/error", json=logErrorBody)
  if response.status_code != BITBOX_STATUS_OK:
    printServerError()

#
# Utility functions
#

def requestWithSession(method: str, url: str, body: Any, authInfo: AuthInfo) -> Union[requests.Response, Error]:
  response = requests.request(method, url, json=body, headers={"Cookie": authInfo.session})
  if (response.status_code != BITBOX_STATUS_OK):
    if response.text == Error.AUTHENTICATION_FAILED.value:
      if authInfo.personalKey is None:
        authInfo.personalKey = util.getPersonalKey()
      
      try:
        authInfo.session = authenticateUser(authInfo.userInfo, authInfo.personalKey)
      except Exception as e:
        if e.args == (Error.AUTHENTICATION_FAILED,):
          console = Console()
          console.print("Incorrect password.", style="red")
          sys.exit(1)
        else:
          raise e

      util.setSession(authInfo.userInfo, authInfo.session)
      response = requests.request(method, url, json=body, headers={"Cookie": authInfo.session})
      if response.status_code == BITBOX_STATUS_OK:
        return response
      elif response.text == Error.AUTHENTICATION_FAILED.value:
        console = Console()
        console.print("Incorrect password.", style="red")
        sys.exit(1)
      else:
        return Error(response.text)
    else:
      return Error(response.text)
  return response

# Raises: AuthenticationFailed, UserNotFound, ConfigParseFailed
def authenticateUser(userInfo: UserInfo, personalKey: str) -> str:
  privateKey = util.getPrivateKey(userInfo, personalKey)

  challengeStr = challenge(userInfo.username)
  guard(challengeStr)
  
  challengeBytes = bytearray.fromhex(challengeStr)
  try:
    answerBytes = util.rsaDecrypt(challengeBytes, privateKey)
  except:
    raise Exception(Error.AUTHENTICATION_FAILED)
  answer = binascii.hexlify(answerBytes).decode("utf-8")

  session = login(userInfo.username, answer)
  if isinstance(session, Error):
    raise Exception(session)
  else:
    return session
