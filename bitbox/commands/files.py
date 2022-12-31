from bitbox.commands.common import *

@app.command(short_help="List all files in your bitbox")
def files():
  # Get user info and try to establish a session
  userInfo, session = loginUser()
  authInfo = AuthInfo(userInfo, session)

  # Get files info
  filesInfo = server.filesInfo(authInfo)

  # Print info
  printFilesInfo(userInfo, filesInfo)
