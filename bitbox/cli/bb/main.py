from bitbox.cli.bb.common import *
from bitbox.cli.bb.login import login
from bitbox.cli import *
import bitbox.lib as lib
import bitbox.server as server
from rich.prompt import Prompt, Confirm
from random_username.generate import generate_username

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
  # Get the key info
  keyInfo = config.getKeyInfo()

  # # Log that a command has been invoked
  try:
    server.logCommand(" ".join(sys.argv[1:]), "" if keyInfo is None else keyInfo.username)
  except Exception as e:
    # If it fails, just ignore it
    pass

  # If the keyfile doesn't exist, create a new user
  if (keyInfo is None) and (ctx.invoked_subcommand != "login"):
    # Print a welcome message
    console.print(
      "\n[bold]Welcome![/bold] `bb` is a command-line clipboard for machine-to-machine "
      "file transfers. Let's get you set up.\n"
    )
    
    # Ask the user if they have an existing account
    existingAccount = Confirm.ask(
      "Do you have an existing account?",
      default=False
    )

    # If the user has an existing account, direct them to link to their existing clipboard
    if existingAccount:
      console.print("")
      login()
    else:
      # Otherwise, create a new account
      # Let the user choose if they want to pick a username or have one randomly assigned
      chooseUsername = Confirm.ask(
        "Would you like to pick your username? If not, one will be randomly assigned to you.",
        default=False
      )
      console.print("")

      # If the user wants to pick a username, prompt them for one
      if chooseUsername:
        username = getValidUsername()
      else:
        # Otherwise, generate a username
        while True:
          username : str = generate_username(1)[0].lower()
          if isinstance(server.userInfo(username), server.Error):
            break
    
      # Create the user
      keyInfo, _ = lib.register(username)
      
      # Save the key info to disk
      config.setKeyInfo(keyInfo)

      # Print an affirmation of login
      console.print(f"You are logged in as: [bold]{keyInfo.username}[/bold]\n")
  elif ctx.invoked_subcommand is None:
    # Otherwise, jut print the username and exit
    console.print(f"You are logged in as: [bold]{keyInfo.username}[/bold]")

def run():
  try:
    os.makedirs(BB_CONFIG_FOLDER)
  except FileExistsError:
    pass

  try:
    app()
  except lib.DecryptionException:
    error("Incorrect password.")
