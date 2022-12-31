from bitbox.commands.common import *

#
# Setup command
#
@app.command(short_help="Set up bitbox under a new or existing user")
def setup():
  # If the config folder already exists, don't let the user set up again
  if os.path.exists(os.path.join(BITBOX_CONFIG_FOLDER, "userinfo.json")):
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
  usernameValid = False
  while not usernameValid:
    username = Prompt.ask("[bold]Pick a username.[/bold] This will identify you to other Bitbox users")
    if re.match(BITBOX_USERNAME_REGEX, username):
      userInfo = server.userInfo(username)
      if server.err(userInfo):
        usernameValid = True
      else:
        warning("That username is already taken.")
    else:
      warning("Usernames must be alphanumeric and be at least 3 characters long.")
  
  # Have the user pick a password that is valid
  passwordValid = False
  while not passwordValid:
    password = Prompt.ask("[bold]Pick a password.[/bold] This will be used to unlock your private key on configured machines", password=True)
    if len(password) >= 8:
      passwordValid = True
    else:
      warning("Passwords must be at least 8 characters long.")

  # Have the user confirm their password
  passwordConfirm = Prompt.ask("Confirm password", password=True)
  if password != passwordConfirm:
    error("Passwords do not match. Please try `bitbox setup` again.")
  
  # Turn the password into a personal key to prevent use of common passwords and to make brute force attacks harder
  personalKey = getPersonalKeyFromPassword(password)

  # Generate a public/private key pair
  privateKey = RSA.generate(2048)
  publicKey = privateKey.publickey()

  # Turn them into strings
  publicKeyStr = publicKey.export_key().decode("utf-8")
  privateKeyStr = privateKey.export_key().decode("utf-8")

  # Encrypt the private key with the personal key
  encryptedPrivateKey = cryptocode.encrypt(privateKeyStr, personalKey)

  # Create a user info object that we will save to disk
  userInfo = UserInfo(
    username=username,
    clientCreated=int(time.time() * 1000),
    publicKeyPath=f"{username}.key.public",
    encryptedPrivateKeyPath=f"{username}.key.private.encrypted")

  # Register the user on the server
  registerUserResponse = server.registerUser(username, publicKeyStr, encryptedPrivateKey)
  guard(registerUserResponse, {
    Error.USER_EXISTS: "That username is already taken. Please try `bitbox setup` again.",
    Error.INVALID_USERNAME: "That username is invalid. Please try `bitbox setup` again."
  })
  
  # Save the user info to disk
  with open(os.path.join(BITBOX_CONFIG_FOLDER, f"{username}.key.public"), "w") as f:
    f.write(publicKeyStr)
  with open(os.path.join(BITBOX_CONFIG_FOLDER, f"{username}.key.private.encrypted"), "w") as f:
    f.write(encryptedPrivateKey)
  with open(os.path.join(BITBOX_CONFIG_FOLDER, f"userinfo.json"), "w") as f:
    userInfoJSON = json.dumps(asdict(userInfo), indent=2)
    f.write(userInfoJSON)

  # Authenticate the user and save the session in the keyring
  session = server.authenticateUser(userInfo, personalKey)
  setSession(userInfo, session)

  # Print a success message
  success("\nYou've been successfully registered on BitBox! Get started by running `bitbox --help` to see available commands.")

def registerClient():
  # Have the user enter their username and confirm that the user exists
  username = Prompt.ask("Username")
  existingUserInfo = server.userInfo(username)
  guard(existingUserInfo, {
    Error.USER_NOT_FOUND: "That username does not exist. Did you mean to set up a new user account?"
  })
  
  # Have the user enter their password
  password = Prompt.ask("Password", password=True)
  personalKey = getPersonalKeyFromPassword(password)

  # Have the user enter their one-time-code
  otcValid = False
  console.print("\nFrom a machine that has already been configured with Bitbox, run `bitbox otc` to generate a one-time-code. This is a phrase of 4 words. Enter that code below.")
  while not otcValid:
    otcWords = Prompt.ask("Code (case-insensitive)")
    otcDictInv = {v.lower(): k for k, v in otcDict.items()}
    otc = ""
    for otcWord in otcWords.split():
      if otcWord.lower() in otcDictInv.keys():
        otc += otcDictInv[otcWord.lower()].lower()
      else:
        console.print(f"Your code was invalid. Try again with a new code.", style="red")
        break
    else:
      otcValid = True

  # Recover the encrypted private key from the server
  encryptedPrivateKey = server.recoverKeys(username, otc)
  guard(encryptedPrivateKey, {
    Error.USER_NOT_FOUND: "That username does not exist. Did you mean to set up a new user account?",
    Error.INVALID_OTC: "That one-time-code is incorrect. Try `bitbox setup` again with a new code!",
    Error.OTC_NOT_GENERATED: "That one-time-code is invalid. Try `bitbox setup` again with a new code!"
  })

  # Decrypt the encrypted private key
  privateKeyStr = cryptocode.decrypt(encryptedPrivateKey, personalKey)
  
  if privateKeyStr == False:
    # If the password was incorrect, we will not be able to decrypt the private key-- tell the user and exit
    console.print("Your password was incorrect. Could not set up Bitbox on this machine.", style="red")
    raise typer.Exit(code=1)
  
  # If the password was correct, we can now save the user info to disk
  privateKey = RSA.import_key(privateKeyStr)
  publicKey = privateKey.publickey()
  userInfo = UserInfo(
    username=username,
    clientCreated=int(time.time() * 1000),
    publicKeyPath=f"{username}.key.public",
    encryptedPrivateKeyPath=f"{username}.key.private.encrypted")
  with open(os.path.join(BITBOX_CONFIG_FOLDER, f"{username}.key.public"), "w") as f:
    f.write(publicKey.export_key().decode("utf-8"))
  with open(os.path.join(BITBOX_CONFIG_FOLDER, f"{username}.key.private.encrypted"), "w") as f:
    f.write(encryptedPrivateKey)
  with open(os.path.join(BITBOX_CONFIG_FOLDER, f"userinfo.json"), "w") as f:
    userInfoJSON = json.dumps(asdict(userInfo), indent=2)
    f.write(userInfoJSON)
  
  # Authenticate the user and save the session in the keyring
  session = server.authenticateUser(userInfo, personalKey)
  setSession(userInfo, session)

  # Print a success message
  console.print("\n[green]You've successfully logged into BitBox! You can now use Bitbox to store, share, and sync files on this machine.[/green]")
