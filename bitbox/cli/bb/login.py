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
  otc = console.input("[bold]One-time-code (case-insensitive):[/bold] ").lower().strip()

  # Recover a recovery key
  try:
    recoveryKeyInfo = lib.recover(username)
  except lib.RecoveryNotReadyException:
    error("Could not authenticate. Please run `bb` on a machine you're already logged in on to generate a one-time-code.")
  
  # Try to decrypt the recovery key with a one-time code and password
  tries = 3
  while tries > 0:
    # Try to decrypt the private key
    try:
      keyInfo, privateKey = recoveryKeyInfo.decrypt(otc)
      break
    except lib.InvalidOTCException:
      pass
    except lib.DecryptionException:
      pass
    
    if tries == 1:
      error("Your one-time-code/password combination is invalid. Could not log in.")
    else:
      warning("Your one-time-code/password combination is invalid. Please try again.\n")
      otc = console.input("[bold]One-time-code (case-insensitive):[/bold] ").lower().strip()
    tries -= 1
  
  # Save the user info to disk
  config.setKeyInfo(keyInfo)

  # Authenticate the user and save the session securely
  session = server.establishSession(keyInfo.username, privateKey)
  config.setSession(session)

  # Print a success message
  success(f"\nYou've successfully logged in as '{username}'.")
