from bitbox.cli.bitbox.common import *
from bitbox.cli import *
import bitbox.cli.bitbox.syncinfo as syncinfo
import bitbox.server as server

@app.command(short_help="Delete a file from your bitbox without affecting local files")
def delete(remote: str = typer.Argument(..., help="Name of the remote file to delete.")):
  # Get user info and try to establish a session
  authInfo = config.load()

  # Get file information
  owner = authInfo.keyInfo.username
  filename = remote
  fileInfo = server.fileInfo(remote, authInfo.keyInfo.username, authInfo)
  guard(fileInfo, {
    server.Error.FILE_NOT_FOUND: f"Remote file '@{owner}/{filename}' does not exist.",
  })
  fileId = fileInfo.fileId

  # Delete the file
  deleteResponse = server.delete(fileId, authInfo)
  guard(deleteResponse)

  # Delete the syncs corresponding to the file
  syncinfo.deleteSyncsByRemote(fileId)
  
  # Print a success message
  success(f"Remote file '@{authInfo.keyInfo.username}/{remote}' has been deleted. No local clones have been changed.")

  # Save the session back onto the disk
  config.setSession(authInfo.session)
