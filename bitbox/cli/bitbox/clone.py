from bitbox.cli.bitbox.common import *
from bitbox.cli import *
import bitbox.cli.bitbox.syncinfo as syncinfo
import bitbox.server as server
from cryptography.fernet import Fernet
import binascii

#
# Clone command
#

@app.command(short_help="Clone a file from your bitbox onto your local machine")
def clone(
  remote: str = typer.Argument(..., help="Name of the remote file to clone. If the file is owned by another user, use the '@someuser/somefile' syntax."),
  local: str = typer.Option(None, help="Name of the local file to sync. If not specified, defaults to the same name as the remote file.")):
  # If local is not specified, default to the same name as the remote file
  if (local == None):
    local = os.path.basename(remote)
  
  # Confirm that the local file does not already exist
  if os.path.exists(local):
    error(f"A local file at '{local}' already exists. Use the `--local` flag to specify a different name for the local file.")

  # Get user info and try to establish a session
  authInfo = config.load()

  # Parse the remote file name and get file information
  owner, filename = parseRemoteFilename(remote, None)

  # Get the file info from the server so that we can see if we already have the latest version of the file
  # We will make use of the file hash to determine if we need to download the file
  fileInfo = server.fileInfo(filename, owner, authInfo)
  renderedRemoteFilename = renderRemoteFilename(filename, owner)
  guard(fileInfo, {
    Error.FILE_NOT_FOUND: f"Remote file '{renderedRemoteFilename}' does not exist.",
    Error.USER_NOT_FOUND: f"User '@{owner}' does not exist.",
    Error.FILENAME_NOT_SPECIFIC: f"There are multiple remote files named '{filename}'. Please specify the file owner using the '@someuser/somefile' syntax."
  })
  fileId = fileInfo.fileId
  owner = fileInfo.owner
  fileHash = fileInfo.hash
  renderedRemoteFilename = renderRemoteFilename(filename, owner)

  # Check the sync record to see if we already have a copy of this file
  syncRecord = syncinfo.lookupSyncByRemote(fileId)
  if (syncRecord != None):
    # If we do, check if it's the latest version by seeing if the hashes match
    if (syncRecord.lastHash == fileHash):
      # If the hashes match, we can just copy the file and create a hardlink to it
      syncinfo.copySync(syncRecord.syncId, remote)

      # Print a success message and exit
      success(f"Remote file '{renderedRemoteFilename}' has been cloned onto your local machine as '{local}'.")
      return
  
  # Otherwise, we need to download the file from the server
  saveResponse = server.save(fileId, authInfo)
  guard(saveResponse, {
    Error.FILE_NOT_FOUND: f"Remote file '{renderedRemoteFilename}' does not exist.",
    Error.FILE_NOT_READY: f"Remote file '{renderedRemoteFilename}' is being modified elsewhere. Please try again later.",
  })

  # Download the file
  downloadResponse = requests.get(saveResponse.downloadURL)
  if downloadResponse.status_code != 200:
    error(f"An error occurred downloading remote file '{renderedRemoteFilename}'.")
  
  # Decrypt the file
  downloadFileContents = downloadResponse.text
  privateKey = authInfo.getPrivateKey()
  fileKey = rsaDecrypt(binascii.unhexlify(saveResponse.encryptedKey), privateKey)
  fileContents = Fernet(fileKey).decrypt(downloadFileContents)

  # As a security measure, make sure the hashes match
  downloadedFileHash = hashlib.sha256(fileContents).hexdigest()
  if (downloadedFileHash != saveResponse.hash):
    error(f"Hash for remote file '{renderedRemoteFilename}' does not match the downloaded copy. This file may have been tampered with.")
  
  # Write the file to the local machine
  with open(local, "wb") as f:
    f.write(fileContents)
  
  # Add a sync record for this file
  syncinfo.createSync(fileId, saveResponse.hash, local)

  # Print a success message
  success(f"Remote file '{renderedRemoteFilename}' has been cloned onto your local machine as '{local}'.")

  # Save the session back onto the disk
  config.setSession(authInfo.session)
  