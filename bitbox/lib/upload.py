from bitbox.common import *
from bitbox.util import *
import bitbox.server as server
from cryptography.fernet import Fernet
import binascii

def upload(blob: bytes, filename: str, authInfo: AuthInfo, overwrite: bool = False):
  """
  Upload a blob to the server.

  :param blob: Contents of the blob to upload.
  :param filename: Remote filename for the blob.
  :param authInfo: Authentication information.

  :raises Error.FILE_TOO_LARGE: If the file is too large to upload.
  :raises Error.FILE_EXISTS: If overwrite = False and a file with the same name already exists.
  :raises Error.FILE_NOT_READY: If overwrite = True and the file is being modified elsewhere.
  :raises Error.UPLOAD_ERROR: If the upload failed.
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
  if isinstance(prepareStoreResponse, Error):
    if prepareStoreResponse == Error.FILE_EXISTS.value:
      if overwrite:
        # If the file already exists and overwrite = True, do a prepareUpdate instead
        fileInfo = server.fileInfo(filename, authInfo.keyInfo.username, authInfo)
        if isinstance(fileInfo, Error):
          raise fileInfo
        fileId = fileInfo.fileId
        prepareUpdateResponse = server.prepareUpdate(fileId, len(encryptedBlob), blobHash, authInfo)
        if isinstance(prepareUpdateResponse, Error):
          raise prepareUpdateResponse
        uploadURL = prepareUpdateResponse.uploadURL
      else:
        # Otherwise, raise an error
        raise Error.FILE_EXISTS
    raise prepareStoreResponse
  else:
    fileId = prepareStoreResponse.fileId
    uploadURL = prepareStoreResponse.uploadURL
  
  # Create a resumable session from the prepareStore response
  resumableSession = requests.post(uploadURL, "", headers={
      "x-goog-resumable": "start",
      "content-type": "text/plain",
      "x-goog-content-length-range": f"0,{len(encryptedBlob)}"
  })
  if resumableSession.status_code != 201:
    raise Error.UPLOAD_ERROR

  # Get the location to upload to
  location = resumableSession.headers["location"]

  # Upload to that location via a PUT request
  uploadResponse = requests.put(location, data=encryptedBlob, headers={
    "content-type": "text/plain",
    "content-length": str(len(encryptedBlob))
  })
  
  # Check if the upload was successful
  if uploadResponse.status_code != 200:
    raise Error.UPLOAD_ERROR
  
  # Tell the server we're done uploading
  storeResponse = server.store(fileId, authInfo)
  if isinstance(storeResponse, Error):
    raise storeResponse
