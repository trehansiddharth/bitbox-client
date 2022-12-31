from bitbox.commands.common import *
import bitbox.sync as sync

@app.command(short_help="Delete a file from your bitbox without affecting local files")
def delete(remote: str = typer.Argument(..., help="Name of the remote file to delete.")):
  # Get user info and try to establish a session
  userInfo, session = loginUser()
  authInfo = AuthInfo(userInfo, session)

  # Get file information
  owner = userInfo.username
  filename = remote
  fileInfo = server.fileInfo(remote, userInfo.username, authInfo)
  guard(fileInfo, {
    Error.FILE_NOT_FOUND: f"Remote file '@{owner}/{filename}' does not exist.",
  })
  fileId = fileInfo.fileId

  # Delete the file
  deleteResponse = server.delete(fileId, authInfo)
  guard(deleteResponse)

  # Delete the syncs corresponding to the file
  sync.deleteSyncsByRemote(fileId)
  
  # Print a success message
  success(f"Remote file '@{userInfo.username}/{remote}' has been deleted. No local clones have been changed.")
