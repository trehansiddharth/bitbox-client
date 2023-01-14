from bitbox.cli.bb.common import *
from bitbox.cli import *
import bitbox.lib as lib

@app.command(short_help="Authorize another client to log in to your account")
def authorize():
  # Get user info and try to establish a session
  authInfo = config.load()

  # Print the username
  console.print(f"[bold]Your username is:[/bold] [green]{authInfo.keyInfo.username}[/green]\n")

  # Print a progress message
  console.print("Creating authorization...")

  # Create a one-time-code
  otc = createOTC()

  # Back up the private key to the server
  lib.backup(otc, authInfo)

  # Print the one-time-code
  console.print(f"[bold]Your one-time-code is:[/bold] [green]{otc}[/green]\n")
  console.print("On the machine you want to log in from, run [green]`bb login`[/green] and enter the above username and code when prompted.")

  # Save the session
  config.setSession(authInfo.session)
