from bitbox.commands.common import *
import bitbox.sync as sync

#
# Push command
#

@app.command(short_help="Push changes in a local file to its remote copy")
def update(file: str):
  # Get user info and try to establish a session
  userInfo, session = loginUser()
  authInfo = server.AuthInfo(userInfo, session)
  
  # Check if the file exists and is not a directory
  confirmLocalFileExists(file)

  # Check if the file is in the user's bitbox
  syncRecord = sync.lookupSync(file)
  if syncRecord == None:
    error(f"Local file '{file}' is not known to be synchronized with bitbox.")

  # Get the file information from the server
  fileInfo = server.fileInfoById(syncRecord.fileId, authInfo)
  guard(fileInfo, {
    Error.FILE_NOT_FOUND: f"The remote for local file '{file}' has been deleted from your bitbox. It can no longer be updated."
  })
  owner = fileInfo.owner
  filename = fileInfo.name

  # Make sure this user owns the file
  if (owner != userInfo.username):
    error(f"Only the file owner, @{owner}, has permissions to update remote file '{file}'")
  
  # Get the old file info from the server

  # Read the file and get its hash
  with open(file, "rb") as f:
    fileContents = f.read()
  fileHash = hashlib.sha256(fileContents).hexdigest()

  # Check to see if the file has changed by comparing hashes
  if (fileInfo.hash == fileHash):
    warning(f"Local file '{file}' has not changed. No update will be sent to the server.")
    return
  
  # Get the user's password so we can decrypt the user's private key
  if authInfo.personalKey is None:
    authInfo.personalKey = getPersonalKey()
  
  # Get the user's private key so we can decrypt the file key
  privateKey = getPrivateKey(userInfo, authInfo.personalKey)
  
  # Decrypt the file key
  fileKey = rsaDecrypt(binascii.unhexlify(fileInfo.encryptedKey), privateKey)
  
  # Encrypt the updated file contents
  encryptedFileBytes = Fernet(fileKey).encrypt(fileContents)

  # Send a request to the server to update the file, and grab the upload URL
  prepareUpdateResponse = server.prepareUpdate(fileInfo.fileId, len(encryptedFileBytes), fileHash, authInfo)
  guard(prepareUpdateResponse, {
    Error.FILE_TOO_LARGE: f"File {file} is too large to upload. Run `bitbox` to check how much space you have.",
    Error.FILE_NOT_READY: f"Remote file '@{owner}/{filename}' is being modified elswhere. Try again later."
  })
  
  # Upload the file
  uploadFile(prepareUpdateResponse.uploadURL, encryptedFileBytes)
  
  # Tell the server we're done uploading
  storeResponse = server.store(fileInfo.fileId, authInfo)
  guard(storeResponse)

  # Update the sync record with the new hash
  sync.updateSync(file, fileHash)

  # Tell the user that the file has been pushed
  success(f"Remote file '@{owner}/{filename}' has been updated with local changes.")
