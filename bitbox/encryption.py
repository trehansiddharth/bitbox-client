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

class StreamEncryptor:
  key: bytes
  __state: bytes
  __slot = 0

  def __init__(self, key: bytes):
    self.key = hashlib.sha256(key).digest()
    self.__state = self.key
  
  def encrypt(self, data: bytes) -> bytes:
    output = "".encode()
    for i in range(len(data)):
      output += data[i] ^ self.__state[self.__slot]
      self.__state[self.__slot] = data[i]
      self.__state = hashlib.sha256(self.__state).digest()
      self.__slot = (self.__slot + 1) % len(self.__state)
    return output

class StreamDecryptor:
  key: bytes
  __state: bytes
  __slot = 0

  def __init__(self, key: bytes):
    self.key = hashlib.sha256(key).digest()
    self.__state = self.key
  
  def decrypt(self, data: bytes) -> bytes:
    output = "".encode()
    for i in range(len(data)):
      output += data[i] ^ self.__state[self.__slot]
      self.__state[self.__slot] = output[i]
      self.__state = hashlib.sha256(self.__state).digest()
      self.__slot = (self.__slot + 1) % len(self.__state)
    return output
