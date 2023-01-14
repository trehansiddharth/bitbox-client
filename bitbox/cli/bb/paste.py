from bitbox.cli.bb.common import *
from bitbox.cli import *
import bitbox.lib as lib
from rich.prompt import Confirm
import os

#
# Paste command
#

@app.command(short_help="Paste the file currently on your clipboard")
def paste():
  # Get user info and try to establish a session
  authInfo = handleLoginUser()

  # Download the blob
  try:
    blob = lib.download("&clipped", authInfo.keyInfo.username, authInfo)
  except lib.FileNotFoundException:
    console.print("There is nothing on your clipboard.")
    typer.Exit(1)
  except lib.FileNotReadyException:
    error("Your clipped content is not ready to download yet. Please try again later.")

  # Parse the blob
  clip = blobToClip(blob)
  filename = clip.filename
  fileContents = clip.content

  # Check if file already exists
  if os.path.exists(filename):
    overwrite = Confirm.ask(f"File '{filename}' already exists. Overwrite?", default=False)
    if not overwrite:
      typer.Exit(1)

  # Write the file to disk
  with open(filename, "wb") as f:
    f.write(fileContents)
  
  # Print a success message
  success(f"File '{filename}' has been saved to disk.")
