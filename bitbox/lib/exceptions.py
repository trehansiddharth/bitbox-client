from bitbox.server import \
  BitboxException, \
  InvalidVersionException, \
  AuthenticationException, \
  UserNotFoundException

class UserExistsException(Exception):
  def __init__(self, username):
    self.username = username

class InvalidUsernameException(Exception):
  pass

class InvalidPublicKeyException(Exception):
  pass

class FileNotFoundException(Exception):
  def __init__(self, filename):
    self.filename = filename

class FileExistsException(Exception):
  def __init__(self, filename):
    self.filename = filename

class FileNotReadyException(Exception):
  def __init__(self, filename):
    self.filename = filename

class FileTooLargeException(Exception):
  pass

class DownloadException(Exception):
  pass

class UploadException(Exception):
  pass

class RecoveryNotReadyException(Exception):
  pass

class InvalidOTCException(Exception):
  pass

class DecryptionException(Exception):
  pass