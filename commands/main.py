from commands.common import *
import sys

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
  # Get the user info
  userInfo = getUserInfo()

  # Log that a command has been invoked
  server.logEvent(" ".join(sys.argv[1:]), "" if userInfo is None else userInfo.username)

  # If a subcommand is invoked, let that subcommand run instead of this routine
  if ctx.invoked_subcommand is not None:
    return

  # Get user info and try to establish a session
  userInfo, session = loginUser()
  authInfo = AuthInfo(userInfo, session)

  # Print the user's info
  console.print(f"You are logged in as: [bold]{userInfo.username}[/bold]\n")

  # Get files info
  filesInfo = server.filesInfo(authInfo)

  # Print info
  printFilesInfo(userInfo, filesInfo)
  bytesUsed = sum([file.bytes for file in filesInfo if file.owner == userInfo.username])
  console.print(f"\nTotal space usage: {humanReadableFilesize(bytesUsed)} / 1 GiB ({bytesUsed / 1073741824 :.0%})")
