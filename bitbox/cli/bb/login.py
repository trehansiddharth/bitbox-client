from bitbox.cli.bb.common import *
from bitbox.cli import *
import bitbox.lib as lib
import bitbox.server as server

@app.command(short_help="Log in and share clipboards with an existing account")
def login():
  # Print instructions
  console.print("On a machine you're already logged in on, run [green]`bb authorize`[/green], and enter the information below.\n")

  # Wait to receive information from the other client
  username = console.input("[bold]Username:[/bold] ")
  otc = console.input("[bold]One-time-code:[/bold] ")

  # Recover the key info and private key
  try:
    keyInfo, privateKey = lib.recover(username, otc)
  except lib.UserNotFoundException:
    error("That username does not exist. Did you enter the correct username? It is printed when you run `bb authorize`.")
  except lib.RecoveryNotReadyException:
    error("That one-time-code is invalid. Please try `bb login` again with a new code.")
  except lib.InvalidOTCException:
    error("That one-time-code is invalid. Please try `bb login` again with a new code.")
  except lib.DecryptionException:
    error("Your password is incorrect. Please try `bb login` again with a new code.")
  
  # Save the user info to disk
  config.setKeyInfo(keyInfo)

  # Authenticate the user and save the session securely
  session = server.establishSession(keyInfo.username, privateKey)
  config.setSession(session)

  # Print a success message
  success(f"\nYou've successfully logged in as '{username}'.")
