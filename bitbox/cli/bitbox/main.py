from bitbox.cli.bitbox.common import *
from bitbox.cli import *
import bitbox.server as server
import sys

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
  # Get the key info
  keyInfo = getKeyInfo()

  # # Log that a command has been invoked
  try:
    server.logCommand(" ".join(sys.argv[1:]), "" if keyInfo is None else keyInfo.username)
  except Exception as e:
    # If it fails, just ignore it
    pass

  # If a subcommand is invoked, let that subcommand run instead of this routine
  if ctx.invoked_subcommand is not None:
    return

  # Get user info and try to establish a session
  authInfo = handleLoginUser()

  # Print the user's info
  console.print(f"You are logged in as: [bold]{keyInfo.username}[/bold]\n")

  # Get files info
  filesInfo = server.filesInfo(authInfo)

  # Print info
  printFilesInfo(keyInfo.username, filesInfo)
  bytesUsed = sum([file.bytes for file in filesInfo if file.owner == keyInfo.username])
  console.print(f"\nTotal space usage: {humanReadableFilesize(bytesUsed)} / 1 GiB ({bytesUsed / 1073741824 :.0%})")

  # Save the session back onto the disk
  setSession(authInfo.session)

def run():
  try:
    os.makedirs(BITBOX_CONFIG_FOLDER)
  except FileExistsError:
    pass

  try:
    os.makedirs(BITBOX_SYNCS_FOLDER)
  except FileExistsError:
    pass

  if not os.path.exists(BITBOX_SYNC_INFO_PATH):
    try:
      with open(BITBOX_SYNC_INFO_PATH, "w") as f:
        f.write("[]")
    except FileExistsError:
      pass

  try:
    app()
  except lib.DecryptionException:
    error("Incorrect password.")
