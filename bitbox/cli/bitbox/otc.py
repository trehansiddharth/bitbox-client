from bitbox.cli.bitbox.common import *
from bitbox.cli import *
import bitbox.lib as lib

#
# OTC command
#

@app.command(short_help="Generate a one-time-code to setup Bitbox on another machine")
def otc():
  # Get user info and try to establish a session
  authInfo = config.load()

  # Create a one-time-code
  otc = createOTC()

  # Back up the private key to the server
  lib.backup(otc, authInfo)

  # Print the one-time-code
  console.print(f"[bold]Your one-time-code is:[/bold] [green]{otc}[/green]\n")
  console.print("Enter this code on the machine you want to set up a new Bitbox client on.")

  # Save the session back onto the disk
  config.setSession(authInfo.session)
