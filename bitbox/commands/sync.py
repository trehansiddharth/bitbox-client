from commands.common import *
import sync as syncModule

#
# Utility functions
#

def syncFile(authInfo: AuthInfo, file: str, syncRecord : syncModule.SyncRecord, errMode: PrintMode = PrintMode.WARNING) -> bool:
  # Get the has of the last pull
  lastPullHash = syncRecord.lastHash

  # Get the latest file info from the server
  fileId = syncRecord.fileId
  serverFileInfo = server.fileInfoById(fileId, authInfo)
  if (isinstance(serverFileInfo, Error) and serverFileInfo == Error.FILE_NOT_FOUND):
    syncModule.deleteSyncsByRemote(fileId)
    print(f"The remote for local file '{file}' has been deleted from your bitbox. It can no longer be synchronized.", mode=errMode)
    return False
  guard(serverFileInfo)
  owner = serverFileInfo.owner
  filename = serverFileInfo.name
  serverHash = serverFileInfo.hash

  # Read the file and get its hash
  with open(file, "rb") as f:
    fileContents = f.read()
  currentFileHash = hashlib.sha256(fileContents).hexdigest()

  # If the current hash is the same from the one on the server, the file hasn't changed
  if serverHash == currentFileHash:
    warning(f"Skipping local file '{file}' because there have been no local or remote changes.")
    return False
  
  # If the current hash is different from the one from the last pull, there have been local changes to the file
  if lastPullHash != currentFileHash:
    overwrite = Confirm.ask(f"Local file '{file}' has edits. Synchronize with remote and overwrite changes?", default=False)
    if not overwrite:
      return False
  
  # Get a download link from the server
  saveResponse = server.save(fileId, authInfo)
  if (isinstance(saveResponse, Error) and saveResponse == Error.FILE_NOT_READY):
    warning(f"Skipping local file '{file}' because its remote at '@{owner}/{filename}' is being modified elsewhere. Try synchronizing this file later.")
    return False
  guard(saveResponse)

  # Request the user's password to decrypt the file key
  if authInfo.personalKey is None:
    authInfo.personalKey = getPersonalKey()

  # Download the file
  downloadResponse = requests.get(saveResponse.downloadURL)
  if downloadResponse.status_code != 200:
    print(f"Skipping local file '{file}' because an error occured while downloading its remote at '@{owner}/{filename}'.", mode=errMode)
    return False
  
  # Decrypt the file
  downloadFileContents = downloadResponse.text
  privateKey = getPrivateKey(authInfo.userInfo, authInfo.personalKey)
  fileKey = rsaDecrypt(binascii.unhexlify(saveResponse.encryptedKey), privateKey)
  fileContents = Fernet(fileKey).decrypt(downloadFileContents)

  # As a security measure, make sure the hashes match
  downloadedFileHash = hashlib.sha256(fileContents).hexdigest()
  if (downloadedFileHash != saveResponse.hash):
    print(f"Skipping local file '{file}' because the hash for remote file '@{owner}/{filename}' does not match the downloaded copy. This file may have been tampered with.", mode=errMode)
    return False
  
  # Write the file to the local machine
  with open(file, "wb") as f:
    f.write(fileContents)
  
  # Update the sync record
  syncModule.updateSync(file, saveResponse.hash)

  # Print a success message
  console.print(f"Local file '{file}' synchronized with its remote at '@{owner}/{filename}'.")
  return True

#
# Sync command
#

@app.command(short_help="Synchronize all clones in the current directory or in a given path with their remotes")
def sync(path: str = typer.Argument(".", help="Path to synchronize")):
  # Get user info and try to establish a session
  userInfo, session = loginUser()
  authInfo = AuthInfo(userInfo, session)

  # Keep track of how many files have been modified
  modifiedCount = 0

  # Check if the path refers to a directory
  if os.path.isdir(path):
    # Get a list of all files in the path
    files = []
    for root, dirs, fileNames in os.walk(path):
      for fileName in fileNames:
        # Check if the file is an existing sync point
        file = os.path.join(root, fileName)
        syncRecord = syncModule.lookupSync(file)

        # If it is, add it to the list of files to sync
        if syncRecord is not None:
          files.append((file, syncRecord))
    
    # Pull changes from the server for each file
    for file, syncRecord in files:
      modifiedCount += syncFile(authInfo, file, syncRecord, PrintMode.WARNING)
    
    if len(files) == 0:
      warning(f"No clones found. Nothing to synchronize.")
  else:
    # Otherwise, check if the file exists
    if not os.path.isfile(path):
      error(f"Local path '{path}' does not exist.")

    # Check if the file is an existing sync point
    syncRecord = syncModule.lookupSync(path)

    # Print an error message if the file is not a sync point, otherwise pull changes
    # from the server
    if syncRecord is None:
      error(f"Local file '{path}' is not known to be synchronized with any remote.")
    else:
      modifiedCount += syncFile(authInfo, path, syncRecord, PrintMode.ERROR)

  # Print a success message
  success(f"\nSync successful: {modifiedCount} files modified.")
