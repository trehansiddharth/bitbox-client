from bitbox.cli.bitbox.common import *
from bitbox.cli import *
import bitbox.lib as lib
import bitbox.server as server
from bitbox.cli.otc_dict import otcDict
from rich.prompt import Prompt, Confirm

#
# Setup command
#

@app.command(short_help="Set up bitbox under a new or existing user")
def setup():
  # If the config folder already exists, don't let the user set up again
  if os.path.exists(os.path.join(BITBOX_CONFIG_FOLDER, BITBOX_KEYFILE_FILENAME)):
    console.print(f"You've already set up bitbox on this machine! To reconfigure bitbox, delete {BITBOX_CONFIG_FOLDER} and try again.\n")
    console.print("[bold]WARNING: This will delete your private key. It may be wise to move this folder to a different location.[/bold]", style="red")
    raise typer.Exit(code=1)

  # Header text
  console.print("\n[bold]Welcome to Bitbox![/bold] Bitbox is your command-line mailbox for storing and sharing files. Let's get you set up.\n")
  
  # If the user is new, register them. Otherwise, register a new client by recovering the private key
  existingAccount = Confirm.ask("Do you have an existing Bitbox account?", default=False)
  if existingAccount:
    registerClient()
  else:
    registerUser()

#
# Register a new user
#

def registerUser():
  # Have the user pick a username that is valid and available
  username = getValidUsername()
  
  # Have the user pick a password that is valid
  password = getValidPassword()

  # Have the user confirm their password
  passwordConfirm = Prompt.ask("Confirm password", password=True)
  if password != passwordConfirm:
    error("Passwords do not match. Please try `bitbox setup` again.")
  
  # Create the user
  keyInfo, privateKey = lib.register(username, password)
  
  # Save the user info to disk
  config.setKeyInfo(keyInfo)

  # Authenticate the user and save the session securely
  session = server.establishSession(keyInfo.username, privateKey)
  config.setSession(session)

  # Print a success message
  success("\nYou've been successfully registered on BitBox! Get started by running `bitbox --help` to see available commands.")

#
# Register a new client for an existing user
#

def registerClient():
  # Have the user enter their username and confirm that the user exists
  username = Prompt.ask("Username")
  existingUserInfo = server.userInfo(username)
  guard(existingUserInfo, {
    server.Error.USER_NOT_FOUND: "That username does not exist. Did you mean to set up a new user account?"
  })

  # Have the user enter their one-time-code
  console.print("\nFrom a machine that has already been configured with Bitbox, run `bitbox otc` to generate a one-time-code. This is a phrase of 4 words. Enter that code below.")
  otc = Prompt.ask("Code (case-insensitive)").lower().strip()

  # Recover a recovery key
  try:
    recoveryKeyInfo = lib.recover(username)
  except lib.UserNotFoundException:
    error("That username does not exist. Did you mean to set up a new user account?")
  except lib.RecoveryNotReadyException:
    error("Could not authenticate. Please run `bitbox otc` on a machine you're already logged in on to generate a one-time-code.")
  
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
      otc = Prompt.ask("Code (case-insensitive)").lower().strip()
    tries -= 1
  
  # Save the user info to disk
  config.setKeyInfo(keyInfo)
  
  # Authenticate the user and save the session securely
  session = server.establishSession(keyInfo.username, privateKey)
  config.setSession(session)

  # Print a success message
  console.print("\n[green]You've successfully logged into BitBox! You can now use Bitbox to store, share, and sync files on this machine.[/green]")
