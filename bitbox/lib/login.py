from bitbox.common import *
from bitbox.encryption import getPersonalKey, getPersonalKeyFromPassword
from bitbox.lib.exceptions import *
import bitbox.server as server
import cryptocode

def login(keyInfo: KeyInfo, password: Optional[str], session: Optional[Session] = None) -> AuthInfo:
  """
  Login to the server with the given key info and password.
  
  :param keyInfo: The key info to use to login.
  :param password: The password to decrypt the private key with. If None and the key is encrypted,
    the password will be prompted for. If the key is unencrypted, then no password is necessary.
  :param session: The session to use. If None, a new session will be created.

  :raises DecryptionException: If the password to decrypt the private key is incorrect.
  :raises AuthenticationException: If login failed with the server.
  :raises InvalidVersionException: If the server no longer supports the current version of Bitbox.
  :raises BitboxException: Any other exception indicating an bug in Bitbox.

  :return: The auth info.
  """

  # Create a decrypt function depending on whether the key is encrypted and if password is provided
  if keyInfo.encrypted:
    if password is None:
      def decryptKey(keyStr: str) -> RSA.RsaKey:
        decryptedKey = cryptocode.decrypt(keyStr, getPersonalKey())
        if decryptedKey == False:
          raise DecryptionException()
        return RSA.import_key(decryptedKey)
    else:
      def decryptKey(keyStr: str) -> RSA.RsaKey:
        decryptedKey = cryptocode.decrypt(keyStr, getPersonalKeyFromPassword(password))
        if decryptedKey == False:
          raise DecryptionException()
        return RSA.import_key(decryptedKey)
  else:
    decryptKey = RSA.import_key
  
  # If no session is provided, create one, and cache the private key
  privateKey = None
  if session is None:
    privateKey = decryptKey(keyInfo.privateKey)
    session = server.establishSession(keyInfo.username, privateKey)

  # Return the auth info
  return AuthInfo(keyInfo, session, decryptKey, privateKey)