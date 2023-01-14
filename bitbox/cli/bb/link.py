from bitbox.cli.bb.common import *
from bitbox.cli import *
import bitbox.lib as lib
import bitbox.server as server

@app.command(short_help="Permanently link this clipboard to another client")
def link():
  # Print instructions
  console.print("On the machine you want to link to, run [green]`bb authorize`[/green], and enter the information below.\n")

  # Wait to receive information from the other client
  username = console.input("Username: ")
  otc = console.input("One-time-code: ")

  # Recover the key info and private key
  try:
    keyInfo, privateKey = lib.recover(username, otc)
  except lib.UserNotFoundException:
    error("That username does not exist. Did you enter the correct username? It is printed when you run `bb authorize`.")
  except lib.RecoveryNotReadyException:
    error("That one-time-code is invalid. Please try `bb link` again with a new code.")
  except lib.InvalidOTCException:
    error("That one-time-code is invalid. Please try `bb link` again with a new code.")
  except lib.DecryptionException:
    error("Your password is incorrect. Please try `bb link` again with a new code.")
  
  # Save the user info to disk
  setKeyInfo(keyInfo)

  # Authenticate the user and save the session securely
  session = server.establishSession(keyInfo.username, privateKey)
  setSession(session)

  # Print a success message
  success(f"\nThis clipboard has been successfully linked to '{username}'.")
