from bitbox.common import *
from bitbox.lib.exceptions import *
from bitbox.encryption import getPersonalKeyFromPassword
import bitbox.server as server
from Crypto.PublicKey import RSA
import cryptocode
from typing import Tuple

def register(username: str, password: Optional[str] = None) -> Tuple[KeyInfo, RSA.RsaKey]:
  """
  Register a user on the server and return the key info and a newly created private key.

  :param username: The username to register.
  :param password: The password to encrypt the private key with. If None, the private key will not be encrypted.

  :raises DecryptionException: If the password to decrypt the private key is incorrect.
  :raises AuthenticationException: If login failed with the server.
  :raises InvalidVersionException: If the server no longer supports the current version of Bitbox.
  :raises BitboxException: Any other exception indicating an bug in Bitbox.

  :return: A tuple containing the key info and the private key.
  """
  # Generate a public/private key pair
  privateKey = RSA.generate(2048)
  publicKey = privateKey.publickey()

  # Turn them into strings
  publicKeyStr = publicKey.export_key().decode("utf-8")
  privateKeyStr = privateKey.export_key().decode("utf-8")

  # If there is no password, no encryption is necessary
  if password is None:
    storedPrivateKey = privateKeyStr
    encrypted = False
  else:
    # Otherwise, encrypt the private key with the password
    personalKey = getPersonalKeyFromPassword(password)
    storedPrivateKey = cryptocode.encrypt(privateKeyStr, personalKey)
    encrypted = True
  
  # Create key info object
  keyInfo = KeyInfo(
    username=username,
    publicKey=publicKeyStr,
    privateKey=storedPrivateKey,
    encrypted=encrypted)
  
  # Register the user on the server
  registerUserResponse = server.registerUser(username, publicKeyStr)
  if isinstance(registerUserResponse, server.Error):
    if registerUserResponse == server.Error.USER_EXISTS:
      raise UserExistsException(username)
    elif registerUserResponse == server.Error.INVALID_USERNAME:
      raise InvalidUsernameException()
    else:
      raise InvalidPublicKeyException()
  
  # Return the key info
  return keyInfo, privateKey