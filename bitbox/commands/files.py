from bitbox.commands.common import *

@app.command(short_help="List all files in your bitbox")
def files():
  # Get user info and try to establish a session
  authInfo = loginUser()

  # Get files info
  filesInfo = server.filesInfo(authInfo)

  # Print info
  printFilesInfo(authInfo.keyInfo.username, filesInfo)
