from bitbox.common import *
from bitbox.util import *
import bitbox.server as server
from cryptography.fernet import Fernet
import binascii

def download(filename: str, owner: str, authInfo: AuthInfo) -> bytes:
  """
  Download a blob from the server.

  :param filename: Remote filename for the blob.
  :param owner: Owner of the file. Should be just the username and not `"@" + username`.
  :param authInfo: Authentication information.

  :raises Error.FILE_NOT_FOUND: If the file doesn't exist.
  :raises Error.USER_NOT_FOUND: If the owner doesn't exist.
  :raises Error.FILE_NOT_READY: If the file is not ready to be downloaded.
  :raises Error.DOWNLOAD_ERROR: If the download failed.

  :returns: The decrypted blob.
  """

  # Get the file info
  fileInfo = server.fileInfo(filename, owner, authInfo)
  if isinstance(fileInfo, Error):
    raise fileInfo
  
  # Grab the file ID and hash of the blob
  fileId = fileInfo.fileId
  blobHash = fileInfo.hash

  # Grab the download link for the encrypted blob
  saveResponse = server.save(fileId, authInfo)
  if isinstance(saveResponse, Error):
    raise saveResponse
  
  # Download the file
  downloadResponse = requests.get(saveResponse.downloadURL)
  if downloadResponse.status_code != 200:
    raise Error.DOWNLOAD_ERROR
  
  # Decrypt the file
  encryptedBlobStr = downloadResponse.text
  privateKey = fetchPrivateKey(authInfo)
  fileKey = rsaDecrypt(binascii.unhexlify(saveResponse.encryptedKey), privateKey)
  blob = Fernet(fileKey).decrypt(encryptedBlobStr)

  # As a security measure, check if the hash of the decrypted blob matches the hash of the blob on the server
  if hashlib.sha256(blob).hexdigest() != blobHash:
    raise Error.DOWNLOAD_ERROR

  # Return the decrypted blob
  return blob