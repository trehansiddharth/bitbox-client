from bitbox.cli.bb.common import *
from bitbox.cli import *
import bitbox.lib as lib

#
# Clip command
#

@app.command(short_help="Send a file to your clipboard")
def clip(
  file: str = typer.Argument(..., help="Name of the file to send to your clipboard.")
):
  # Get user info and try to establish a session
  authInfo = handleLoginUser()

  # Confirm that the local file exists and is not a directory
  confirmLocalFileExists(file)

  # Read the contents of the file
  with open(file, "rb") as f:
    fileContents = f.read()
  
  # Create a blob
  blob = clipToBlob(Clip(filename=file, content=fileContents))
  
  # Upload the file to the server as a file called "clipped"
  try:
    lib.upload(blob, "&clipped", authInfo, overwrite=True)
  except lib.FileTooLargeException:
    error("The file you are trying to send is too large. Remember that you have a 1 GiB storage limit.")

  # Print a success message
  success(f"File '{file}' has been sent to your clipboard.")

  # Save the session
  setSession(authInfo.session)
