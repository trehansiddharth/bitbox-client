from bitbox.common import *
from bitbox.encryption import getPublicKey, rsaEncrypt
from bitbox.lib.exceptions import *
import bitbox.server as server
from cryptography.fernet import Fernet
import binascii
import requests
import hashlib

def upload(blob: bytes, filename: str, authInfo: AuthInfo, overwrite: bool = False):
  """
  Upload a blob to the server.

  :param blob: Contents of the blob to upload.
  :param filename: Remote filename for the blob.
  :param authInfo: Authentication information.

  :raises FileTooLargeException: If the file is too large to upload.
  :raises FileExistsException: If overwrite = False and a file with the same name already exists.
  :raises UploadException: If the upload failed.
  :raises DecryptionException: If the password to decrypt the private key is incorrect.
  :raises AuthenticationException: If login failed with the server.
  :raises BitboxException: Any other exception indicating an bug in Bitbox.
  """

  # Create a hash of the blob
  blobHash = hashlib.sha256(blob).hexdigest()

  # Encrypt the blob with a random key
  fileKey = Fernet.generate_key()
  encryptedBlob = Fernet(fileKey).encrypt(blob)

  # Get the user's public key
  publicKey = getPublicKey(authInfo.keyInfo)

  # Encrypt the file key with the user's public key
  personalEncryptedKey = rsaEncrypt(fileKey, publicKey)
  personalEncryptedKeyHex = binascii.hexlify(personalEncryptedKey).decode("utf-8")

  # Tell the server we want to add this file, and get the file ID and URL to upload to
  prepareStoreResponse = server.prepareStore(filename, len(encryptedBlob), blobHash, personalEncryptedKeyHex, authInfo)
  if isinstance(prepareStoreResponse, server.Error):
    # Check if this is a FILE_EXISTS error
    if prepareStoreResponse == server.Error.FILE_EXISTS:
      if overwrite:
        # If the file already exists and overwrite = True, delete the file and try again
        fileInfo = server.fileInfo(filename, authInfo.keyInfo.username, authInfo)
        if isinstance(fileInfo, server.Error):
          raise BitboxException(fileInfo)
        fileId = fileInfo.fileId
        deleteResponse = server.delete(fileId, authInfo)
        if isinstance(deleteResponse, server.Error):
          raise BitboxException(deleteResponse)
        prepareStoreResponse = server.prepareStore(filename, len(encryptedBlob), blobHash, personalEncryptedKeyHex, authInfo)

        # If that still fails, throw an error
        if isinstance(prepareStoreResponse, server.Error):
          raise BitboxException(prepareStoreResponse)
      else:
        # Otherwise, raise an error
        raise FileExistsException(filename)
    elif prepareStoreResponse == server.Error.FILE_TOO_LARGE:
      # If it's any other error, raise the appropriate error
      raise FileTooLargeException()
    else:
      raise BitboxException(prepareStoreResponse)
  
  # Grab parameters from the prepareStore response
  fileId = prepareStoreResponse.fileId
  uploadURL = prepareStoreResponse.uploadURL
  
  # Create a resumable session from the prepareStore response
  resumableSession = requests.post(uploadURL, "", headers={
      "x-goog-resumable": "start",
      "content-type": "text/plain",
      "x-goog-content-length-range": f"0,{len(encryptedBlob)}"
  })
  if resumableSession.status_code != 201:
    raise UploadException()

  # Get the location to upload to
  location = resumableSession.headers["location"]

  # Upload to that location via a PUT request
  uploadResponse = requests.put(location, data=encryptedBlob, headers={
    "content-type": "text/plain",
    "content-length": str(len(encryptedBlob))
  })
  
  # Check if the upload was successful
  if uploadResponse.status_code != 200:
    raise UploadException()
  
  # Tell the server we're done uploading
  storeResponse = server.store(fileId, authInfo)
  if isinstance(storeResponse, server.Error):
    raise BitboxException(storeResponse)
