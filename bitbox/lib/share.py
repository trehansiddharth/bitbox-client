from bitbox.common import *
from bitbox.encryption import *
from bitbox.lib.exceptions import *
import bitbox.server as server
from typing import List
import binascii

def share(filename: str, recipients: List[str], authInfo: AuthInfo):
  """
  Share a file with other users.
  
  :param filename: The name of the file to share.
  :param recipients: A list of usernames of the recipients. Should be just the usernames and not `"@" + username`.
  :param authInfo: Authentication information.
  
  :raises FileNotFoundException: If the file doesn't exist.
  :raises UserNotFoundException: If a recipient doesn't exist.
  :raises DecryptionException: If the password to decrypt the private key is incorrect.
  :raises AuthenticationException: If login failed with the server.
  :raises BitboxException: Any other exception indicating an bug in Bitbox.
  """

  # Get the file info
  fileInfo = server.fileInfo(filename, authInfo.keyInfo.username, authInfo)
  if isinstance(fileInfo, server.Error):
    if fileInfo == server.Error.FILE_NOT_FOUND:
      raise FileNotFoundException(fileInfo.name)
    else:
      raise BitboxException(fileInfo)
  fileId = fileInfo.fileId
  encryptedKey = fileInfo.encryptedKey

  # Get the public keys of the recipients
  publicKeys = {}
  for recipient in recipients:
    userInfoResponse = server.userInfo(recipient)
    if isinstance(userInfoResponse, server.Error):
      raise UserNotFoundException(recipient)
    publicKeys[recipient] = RSA.import_key(userInfoResponse.publicKey)
  
  # Decrypt the file key
  privateKey = authInfo.getPrivateKey()
  fileKey = rsaDecrypt(binascii.unhexlify(encryptedKey), privateKey)

  # Re-encrypt the file key for each recipient
  recipientEncryptedKeys = {}
  for recipient, publicKey in publicKeys.items():
    recipientEncryptedFileKey = rsaEncrypt(fileKey, publicKey)
    recipientEncryptedFileKeyHex = binascii.hexlify(recipientEncryptedFileKey).decode("utf-8")
    recipientEncryptedKeys[recipient] = recipientEncryptedFileKeyHex
  
  # Share the file with the recipients
  shareResponse = server.share(fileId, recipientEncryptedKeys, authInfo)
  if isinstance(shareResponse, server.Error):
    if shareResponse == server.Error.FILE_NOT_FOUND:
      raise FileNotFoundException(fileInfo.name)
    else:
      raise BitboxException(shareResponse)
