from bitbox.common import *
from bitbox.encryption import *
import bitbox.server as server
import cryptocode
from bitbox.lib.exceptions import *

def backup(otc: str, authInfo: AuthInfo) -> None:
  """
  Backup your private key to the server.
  
  :param otc: The one-time code to use to decrypt the backup.

  :raises DecryptionException: If the password to decrypt the private key is incorrect.
  :raises AuthenticationException: If login failed with the server.
  :raises InvalidVersionException: If the server no longer supports the current version of Bitbox.
  :raises BitboxException: Any other exception indicating an bug in Bitbox.
  """

  encryptedPrivateKey = cryptocode.encrypt(authInfo.keyInfo.privateKey, otc)
  
  try:
    server.pushEncryptedKey(encryptedPrivateKey, authInfo)
  except Exception as e:
    raise BitboxException(e)
