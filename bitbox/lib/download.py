from bitbox.common import *
from bitbox.encryption import *
from bitbox.lib.exceptions import *
import bitbox.server as server
from cryptography.fernet import Fernet
import binascii
import requests
import hashlib

def download(filename: str, owner: str, authInfo: AuthInfo) -> bytes:
  """
  Download a blob from the server.

  :param filename: Remote filename for the blob.
  :param owner: Owner of the file. Should be just the username and not `"@" + username`.
  :param authInfo: Authentication information.

  :raises FileNotFoundException: If the file doesn't exist.
  :raises UserNotFoundException: If the owner doesn't exist.
  :raises FileNotReadyException: If the file is not ready to be downloaded.
  :raises DownloadException: If the download failed.
  :raises DecryptionException: If the password to decrypt the private key is incorrect.
  :raises AuthenticationException: If login failed with the server.
  :raises InvalidVersionException: If the server no longer supports the current version of Bitbox.
  :raises BitboxException: Any other exception indicating an bug in Bitbox.

  :returns: The decrypted blob.
  """

  # Get the file info
  fileInfo = server.fileInfo(filename, owner, authInfo)
  if isinstance(fileInfo, server.Error):
    if fileInfo == server.Error.FILE_NOT_FOUND:
      raise FileNotFoundException(fileInfo.name)
    elif fileInfo == server.Error.USER_NOT_FOUND:
      raise UserNotFoundException(owner)
    else:
      raise BitboxException(fileInfo)
  
  # Grab the file ID and hash of the blob
  fileId = fileInfo.fileId
  blobHash = fileInfo.hash

  # Grab the download link for the encrypted blob
  saveResponse = server.save(fileId, authInfo)
  if isinstance(saveResponse, server.Error):
    if saveResponse == server.Error.FILE_NOT_FOUND:
      raise FileNotFoundException(fileInfo.name)
    elif saveResponse == server.Error.FILE_NOT_READY:
      raise FileNotReadyException(fileInfo.name)
    else:
      raise BitboxException(saveResponse)
  
  # Download the file
  downloadResponse = requests.get(saveResponse.downloadURL)
  if downloadResponse.status_code != 200:
    raise DownloadException()
  
  # Decrypt the file
  encryptedBlobStr = downloadResponse.text
  privateKey = authInfo.getPrivateKey()
  fileKey = rsaDecrypt(binascii.unhexlify(saveResponse.encryptedKey), privateKey)
  blob = Fernet(fileKey).decrypt(encryptedBlobStr)

  # As a security measure, check if the hash of the decrypted blob matches the hash of the blob on the server
  if hashlib.sha256(blob).hexdigest() != blobHash:
    raise DownloadException()

  # Return the decrypted blob
  return blob