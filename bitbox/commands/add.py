from bitbox.commands.common import *
import bitbox.sync as sync

#
# Add command
#

@app.command(short_help="Add a file to your bitbox")
def add(
  local: str = typer.Argument(..., help="Name of the local file to add"),
  remote: str = typer.Option(None, help="Name of the remote file to sync with (defaults to the same name as the local file)")):
  # If remote is not specified, default to the same name as the local file
  if (remote == None):
    remote = os.path.basename(local)

  # Get user info and try to establish a session
  authInfo = loginUser()
  
  # Confirm that the local file exists and is not a directory
  confirmLocalFileExists(local)

  # Confirm that the local file is not already being synced
  existingSyncRecord = sync.lookupSync(local)
  if (existingSyncRecord is not None):
    # Confirm that the remote file still exists
    fileInfo = server.fileInfoById(existingSyncRecord.fileId, authInfo)
    if isinstance(fileInfo, Error):
      # If the remote file no longer exists, delete the sync record
      sync.deleteSyncsByRemote(existingSyncRecord.fileId)
    else:
      # If the remote file still exists, tell the user that the file is already being synced
      error(f"Local file {local} is already being synced with remote file '@{fileInfo.owner}/{fileInfo.name}'.")
  
  # Read the contents of the file
  with open(local, "rb") as f:
    fileContents = f.read()

  # Get the hash of the file
  fileHash = hashlib.sha256(fileContents).hexdigest()
  
  # Encrypt the local file with a random key
  fileKey = Fernet.generate_key()
  encryptedFileBytes = Fernet(fileKey).encrypt(fileContents)
  
  # Get the user's public key
  publicKey = getPublicKey(authInfo.keyInfo)
  
  # Encrypt the file key with the user's public key
  personalEncryptedKey = rsaEncrypt(fileKey, publicKey)
  personalEncryptedKeyHex = binascii.hexlify(personalEncryptedKey).decode("utf-8")

  # Tell the server we want to add this file, and get the file ID and URL to upload to
  prepareStoreResponse = server.prepareStore(remote, len(encryptedFileBytes), fileHash, personalEncryptedKeyHex, authInfo)
  guard(prepareStoreResponse, {
    Error.FILE_TOO_LARGE: f"File {local} is too large to upload. Run `bitbox` to check how much space you have.",
    Error.FILE_EXISTS: f"A remote file named '@{authInfo.keyInfo.username}/{remote}' already exists. Use the `--remote` flag to specify a different name for the remote file."
  })

  # Upload the file
  uploadFile(prepareStoreResponse.uploadURL, encryptedFileBytes)
  
  # Tell the server we're done uploading
  storeResponse = server.store(prepareStoreResponse.fileId, authInfo)
  guard(storeResponse)
  
  # Create a sync record for the file
  sync.createSync(prepareStoreResponse.fileId, fileHash, local)

  # Tell the user that the file has been added
  success(f"Local file {local} has been added to your bitbox as '@{authInfo.keyInfo.username}/{remote}'.")
