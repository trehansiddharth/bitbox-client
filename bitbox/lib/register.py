from bitbox.common import *
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
    raise Exception(registerUserResponse)
  
  # Return the key info
  return keyInfo, privateKey