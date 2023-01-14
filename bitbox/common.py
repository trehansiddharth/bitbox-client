from bitbox.parameters import *
from dataclasses import dataclass
from typing import Optional, List, Callable
import time
from Crypto.PublicKey import RSA

PersonalKey = str
Session = str

@dataclass
class KeyInfo:
  username: str
  publicKey: str
  privateKey: str
  encrypted: bool

@dataclass
class AuthInfo:
  keyInfo: KeyInfo
  session: Session
  decryptPrivateKey: Callable[[str], RSA.RsaKey]
  cachedPrivateKey: Optional[RSA.RsaKey]

  def getPrivateKey(self) -> RSA.RsaKey:
    """
    Returns the private key, either from the cache or by decrypting it. If the key is encrypted,
    and the password was not provided on login, the password will be prompted for. The private
    key is cached in the AuthInfo object.
    """
    # If we've already cached the private key, return it
    if self.cachedPrivateKey is not None:
      return self.cachedPrivateKey
    
    # Otherwise, get the private key using the decrypt function
    privateKey = self.decryptPrivateKey(self.keyInfo.privateKey)

    # Save it in the cache
    self.cachedPrivateKey = privateKey

    # Return it
    return privateKey

@dataclass
class FileInfo:
  fileId: str
  name: str
  owner: str
  bytes: int
  lastModified: int
  encryptedKey: str
  hash: str
  sharedWith: List[str]
