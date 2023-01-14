from bitbox.cli.bb.common import *
from bitbox.cli import *
import bitbox.lib as lib
import bitbox.server as server
from random_username.generate import generate_username

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

  # If the keyfile doesn't exist, create a new user
  if keyInfo is None:
    # Create a username that doesn't exist
    while True:
      username : str = generate_username(1)[0].lower()
      if isinstance(server.userInfo(username), Error):
        break
    
    # Create the user
    keyInfo, _ = lib.register(username)
    
    # Save the key info to disk
    setKeyInfo(keyInfo)

    # Print a notification
    console.print(
      f"NOTE: Since this is your first login, you've been assigned the username "
      f"[green]'{username}'[/green]. Please use this username when setting up `bb` "
      f"on a new machine.\n", style="yellow")

  # If a subcommand is invoked, let that subcommand run instead of this routine
  if ctx.invoked_subcommand is not None:
    return

def run():
  try:
    os.makedirs(BITBOX_CONFIG_FOLDER)
  except FileExistsError:
    pass

  try:
    app()
  except lib.DecryptionException:
    error("Incorrect password.")
