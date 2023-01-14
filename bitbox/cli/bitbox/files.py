from bitbox.cli.bitbox.common import *
from bitbox.cli import *
import bitbox.server as server

@app.command(short_help="List all files in your bitbox")
def files():
  # Get user info and try to establish a session
  authInfo = handleLoginUser()

  # Get files info
  filesInfo = server.filesInfo(authInfo)

  # Print info
  printFilesInfo(authInfo.keyInfo.username, filesInfo)

  # Save the session back onto the disk
  setSession(authInfo.session)
