from bitbox.common import *
import bitbox.server as server
from bitbox.encryption import getPersonalKey, getPersonalKeyFromPassword
from bitbox.lib.exceptions import *
from Crypto.PublicKey import RSA
import cryptocode
from typing import Tuple

def recover(username: str, otc: str, password: Optional[str] = None) -> Tuple[KeyInfo, RSA.RsaKey]:
  """
  Recover a user on the server and return the key info and a newly created private key.

  :param username: The username to recover.
  :param otc: The one-time code to recover the user with.
  :param password: The password to encrypt the private key with. If None, the private key will not be encrypted.

  :raises UserNotFoundException: If the username does not exist.
  :raises RecoveryNotReadyException: If no encrypted key is stored for the user.
  :raises InvalidOTCException: If the one-time code is invalid or incorrect.
  :raises DecryptionException: If the password to decrypt the private key is incorrect.
  :raises AuthenticationException: If login failed with the server.
  :raises InvalidVersionException: If the server no longer supports the current version of Bitbox.
  :raises BitboxException: Any other exception indicating an bug in Bitbox.

  :return: A tuple containing the key info and the private key.
  """

  # Generate a public/private key pair
  # Recover the encrypted private key from the server
  encryptedPrivateKey = server.recoverKeys(username)
  if isinstance(encryptedPrivateKey, server.Error):
    if encryptedPrivateKey == server.Error.USER_NOT_FOUND:
      raise UserNotFoundException()
    elif encryptedPrivateKey == server.Error.RECOVERY_NOT_READY:
      raise RecoveryNotReadyException()
    else:
      raise BitboxException(encryptedPrivateKey)

  # Decrypt the encrypted private key with the otc
  storedPrivateKeyStr = cryptocode.decrypt(encryptedPrivateKey, otc.lower())

  # If it fails, the otc was invalid
  if storedPrivateKeyStr == False:
    raise InvalidOTCException()
  
  # Check if the key has been decrypted
  if storedPrivateKeyStr.startswith("-----BEGIN RSA PRIVATE KEY-----"):
    # The private key string is already decrypted
    privateKeyStr = storedPrivateKeyStr

    # The private key should be stored unencrypted
    encrypted = False
  else:
    # The private key requires further decryption with a password
    if password is None:
      personalKey = getPersonalKey()
    else:
      personalKey = getPersonalKeyFromPassword(password)

    # Try to decrypt the key
    privateKeyStr = cryptocode.decrypt(encryptedPrivateKey, personalKey)
    if privateKeyStr == False:
      raise DecryptionException()
    else:
      # The key should be stored encrypted on disk
      encrypted = True
  
  # Create the key objects
  privateKey = RSA.import_key(storedPrivateKeyStr)
  publicKey = privateKey.publickey()

  # Create a key info object
  keyInfo = KeyInfo(
    username=username,
    publicKey=publicKey.export_key().decode("utf-8"),
    privateKey=storedPrivateKeyStr,
    encrypted=encrypted)
  
  # Return the key info and the private key
  return keyInfo, privateKey