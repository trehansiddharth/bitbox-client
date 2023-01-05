from bitbox.commands.common import *
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
  authInfo = loginUser()

  # Print the user's info
  console.print(f"You are logged in as: [bold]{keyInfo.username}[/bold]\n")

  # Get files info
  filesInfo = server.filesInfo(authInfo)

  # Print info
  printFilesInfo(keyInfo.username, filesInfo)
  bytesUsed = sum([file.bytes for file in filesInfo if file.owner == keyInfo.username])
  console.print(f"\nTotal space usage: {humanReadableFilesize(bytesUsed)} / 1 GiB ({bytesUsed / 1073741824 :.0%})")
