from bitbox.common import *
from typing import Optional
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
import cryptocode
import hashlib
import getpass

def getPersonalKey() -> PersonalKey:
  password = getpass.getpass("Password: ")
  return getPersonalKeyFromPassword(password)

def getPersonalKeyFromPassword(password: str) -> PersonalKey:
  return hashlib.sha256(password.encode("utf-8")).hexdigest()

def getPublicKey(keyInfo: KeyInfo) -> RSA.RsaKey:
  return RSA.import_key(keyInfo.publicKey)

def getPrivateKey(keyInfo: KeyInfo, personalKey: Optional[PersonalKey] = None) -> RSA.RsaKey:
  if keyInfo.encrypted:
    if personalKey == None:
      raise Exception
    else:
      privateKeyStr = cryptocode.decrypt(keyInfo.privateKey, personalKey)
  else:
    privateKeyStr = keyInfo.privateKey
  return RSA.import_key(privateKeyStr)

def rsaEncrypt(data: bytes, publicKey: RSA.RsaKey) -> bytes:
  cipher = PKCS1_OAEP.new(publicKey)
  return cipher.encrypt(data)

def rsaDecrypt(data: bytes, privateKey: RSA.RsaKey) -> bytes:
  cipher = PKCS1_OAEP.new(privateKey)
  return cipher.decrypt(data)

class StreamOperator:
  key: bytes
  __state: bytes
  __slot = 0

  def __init__(self, key: bytes):
    self.key = hashlib.sha256(key).digest()
    self.__state = self.key
  
  def _getState(self) -> int:
    return self.__state[self.__slot]
  
  def _rotateState(self, data: int) -> None:
    self.__state = self.__state[:self.__slot] + bytes([data]) + self.__state[self.__slot + 1:]
    self.__state = hashlib.sha256(self.__state).digest()
    self.__slot = (self.__slot + 1) % len(self.__state)

class StreamEncryptor(StreamOperator):
  def encrypt(self, decrypted: bytes) -> bytes:
    encrypted = []
    for i in range(len(decrypted)):
      encrypted.append(decrypted[i] ^ self._getState())
      self._rotateState(decrypted[i])
    return bytes(encrypted)

class StreamDecryptor(StreamOperator):
  def decrypt(self, encrypted: bytes) -> bytes:
    decrypted = []
    for i in range(len(encrypted)):
      decrypted.append(encrypted[i] ^ self._getState())
      self._rotateState(decrypted[i])
    return bytes(decrypted)
