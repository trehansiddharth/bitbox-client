from bitbox.common import *
import bitbox.server as server
from bitbox.encryption import getPersonalKey, getPersonalKeyFromPassword
from bitbox.lib.exceptions import *
from Crypto.PublicKey import RSA
import cryptocode
from typing import Tuple
from dataclasses import dataclass

@dataclass
class RecoveryKeyInfo:
  username: str
  encryptedPrivateKey: str

  def decrypt(self, otc: str, password: Optional[str] = None) -> Tuple[KeyInfo, RSA.RsaKey]:
    """
    Decrypts the encrypted private key and returns the key info and the private key.
    
    :param otc: The one-time-code used to encrypt the recovery key.
    :param password: A password, if required to decrypt the underlying private key.
    
    :raises InvalidOTCException: If the one-time code is invalid or incorrect.
    :raises DecryptionException: If the password to decrypt the private key is incorrect.
    
    :returns A tuple containing the key info and the private key."""

    # Decrypt the encrypted private key with the otc
    storedPrivateKeyStr = cryptocode.decrypt(self.encryptedPrivateKey, otc.lower())

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
      # TODO: move password prompting outside this function
      if password is None:
        personalKey = getPersonalKey()
      else:
        personalKey = getPersonalKeyFromPassword(password)

      # Try to decrypt the key
      privateKeyStr = cryptocode.decrypt(self.encryptedPrivateKey, personalKey)
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
      username=self.username,
      publicKey=publicKey.export_key().decode("utf-8"),
      privateKey=storedPrivateKeyStr,
      encrypted=encrypted)
    
    # Return the key info and the private key
    return keyInfo, privateKey

def recover(username: str) -> RecoveryKeyInfo:
  """
  Recover a password-protected recovery key from the server. A one-time-code is required to decrypt
  the key.

  :param username: The username to recover.

  :raises UserNotFoundException: If the username does not exist.
  :raises RecoveryNotReadyException: If no encrypted key is stored for the user.
  :raises InvalidVersionException: If the server no longer supports the current version of Bitbox.
  :raises BitboxException: Any other exception indicating an bug in Bitbox.

  :returns A RecoveryKeyInfo object containing the encrypted private key.
  """

  # Generate a public/private key pair
  # Recover the encrypted private key from the server
  encryptedPrivateKey = server.recoverKeys(username)
  if isinstance(encryptedPrivateKey, server.Error):
    if encryptedPrivateKey == server.Error.USER_NOT_FOUND:
      raise UserNotFoundException(username)
    elif encryptedPrivateKey == server.Error.RECOVERY_NOT_READY:
      raise RecoveryNotReadyException()
    else:
      raise BitboxException(encryptedPrivateKey)
  
  # Create a RecoveryKeyInfo object
  recoveryKeyInfo = RecoveryKeyInfo(
    username=username,
    encryptedPrivateKey=encryptedPrivateKey)
  
  # Return the recovery key info
  return recoveryKeyInfo