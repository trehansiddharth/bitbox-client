import time
import typer
import requests
import os
import random
import string
import json
import keyring
from dataclasses import dataclass, asdict
import binascii
from Crypto.PublicKey import RSA
import cryptocode
import re
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from otc import otcDict
from parameters import *
from util import *

app = typer.Typer()
console = Console()

@app.command(short_help="Set up bitbox under a new or existing user")
def setup():
  if os.path.exists(os.path.join(BITBOX_CONFIG_FOLDER, "userinfo.json")):
    console.print(f"You've already set up bitbox on this machine! To reconfigure bitbox, delete {BITBOX_CONFIG_FOLDER} and try again.\n")
    console.print("[bold]WARNING: This will delete your private key. It may be wise to move this folder to a different location.[/bold]", style="red")
    raise typer.Exit(code=1)

  console.print("\n[bold]Welcome to Bitbox![/bold] Bitbox is an end-to-end encrypted file storage, sharing, and synchronization tool for busy developers. Let's get you set up.\n")
  
  newUser = Confirm.ask("Are you a new Bitbox user?")
  if newUser:
    registerUser()
  else:
    registerClient()

def registerUser():
  usernameValid = False
  while not usernameValid:
    username = Prompt.ask("[bold]Pick a username.[/bold] This will identify you to other Bitbox users")
    if re.match(BITBOX_USERNAME_REGEX, username):
      userInfo = requests.post(f"http://{BITBOX_HOST}/api/info/user", json={ "username" : username })
      if userInfo.status_code == BITBOX_STATUS_OK:
        console.print("That username is already taken.", style="red")
      else:
        usernameValid = True
    else:
      console.print("Usernames must be alphanumeric and be at least 3 characters long.", style="red")

  passwordValid = False
  while not passwordValid:
    password = Prompt.ask("[bold]Pick a password.[/bold] This will be used to unlock your private key on configured machines", password=True)
    if len(password) >= 8:
      passwordValid = True
    else:
      console.print("Passwords must be at least 8 characters long.", style="red")

  passwordConfirm = Prompt.ask("Confirm password", password=True)
  if password != passwordConfirm:
    console.print("Passwords do not match!", style="red")
    raise typer.Exit(code=1)
  
  personalKey = getPersonalKeyFromPassword(password)

  privateKey = RSA.generate(2048)
  publicKey = privateKey.publickey()
  publicKeyStr = publicKey.export_key().decode("utf-8")
  privateKeyStr = privateKey.export_key().decode("utf-8")
  encryptedPrivateKey = cryptocode.encrypt(privateKeyStr, personalKey)

  userInfo = UserInfo(
    username=username,
    clientCreated=int(time.time() * 1000),
    publicKeyPath=f"{username}.key.public",
    encryptedPrivateKeyPath=f"{username}.key.private.encrypted")

  registerUserBody = {
    "username": username,
    "publicKey": publicKeyStr,
    "encryptedPrivateKey": encryptedPrivateKey
  }
  registerUserResponse = requests.post(f"http://{BITBOX_HOST}/api/auth/register/user", json=registerUserBody)

  if registerUserResponse.status_code == BITBOX_STATUS_OK:
    # TODO: raise exception if these files exist
    with open(os.path.join(BITBOX_CONFIG_FOLDER, f"{username}.key.public"), "w") as f:
      f.write(publicKeyStr)
    with open(os.path.join(BITBOX_CONFIG_FOLDER, f"{username}.key.private.encrypted"), "w") as f:
      f.write(encryptedPrivateKey)
    with open(os.path.join(BITBOX_CONFIG_FOLDER, f"userinfo.json"), "w") as f:
      userInfoJSON = json.dumps(asdict(userInfo), indent=2)
      f.write(userInfoJSON)
    session = authenticateUser(userInfo, personalKey)
    keyring.set_password("bitbox", "session", session)
    console.print("\n[green]You've been successfully registered on BitBox! You can now use Bitbox to store, share, and sync files.[/green]")
  elif registerUserResponse.text == BITBOX_ERR_USER_EXISTS:
    console.print("That username is already taken. Please try `bitbox setup` again.", style="red")
    raise typer.Exit(code=1)
  elif registerUserResponse.text == BITBOX_ERR_INVALID_USERNAME:
    console.print("That username is invalid. Please try `bitbox setup` again.", style="red")
    raise typer.Exit(code=1)

def registerClient():
  username = Prompt.ask("Username")
  existingUserInfo = requests.post(f"http://{BITBOX_HOST}/api/info/user", json={ "username" : username })
  if existingUserInfo.status_code != BITBOX_STATUS_OK:
    console.print("That username does not exist. Did you mean to set up a new user account?", style="red")
    raise typer.Exit(code=1)

  password = Prompt.ask("Password", password=True)
  personalKey = getPersonalKeyFromPassword(password)

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

  recoverKeysBody = {
    "username": username,
    "otc": otc
  }
  recoverKeysResponse = requests.post(f"http://{BITBOX_HOST}/api/auth/recover/recover-keys", json=recoverKeysBody)

  if (recoverKeysResponse.status_code == BITBOX_STATUS_OK):
    encryptedPrivateKey = recoverKeysResponse.text
    privateKeyStr = cryptocode.decrypt(encryptedPrivateKey, personalKey)
    if privateKeyStr == False:
      console.print("Your password was incorrect. Could not set up Bitbox on this machine.", style="red")
      raise typer.Exit(code=1)
    
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
    session = authenticateUser(userInfo, personalKey)
    keyring.set_password("bitbox", "session", session)
    console.print("\n[green]You've successfully logged into BitBox! You can now use Bitbox to store, share, and sync files on this machine.[/green]")
  else:
    typer.echo("Failed to register client! Check your code again!")
    typer.echo(recoverKeysResponse.text)
    raise typer.Exit(code=1)

@app.command(short_help="Add a file to your bitbox")
def add(file: str, remote_file: str = None):
  if (remote_file == None):
    remote_file = os.path.basename(file)

  try:
    userInfo, session = loginUser()
  except Exception as e:
    if e.args[0] == BITBOX_ERR_CONFIG_PARSE_FAILED:
      console.print("Could not parse your user info. Have you set up bitbox with `bitbox setup`?", style="red")
    else:
      console.print("Authentication failed.", style="red")
    raise typer.Exit(code=1)

  if (not os.path.isfile(file)):
    if (os.path.isdir(file)):
      console.print(f"File {file} is a directory. Please specify a file.", style="red")
    else:
      console.print(f"File {file} does not exist.", style="red")
    raise typer.Exit(code=1)

  with open(file, "r") as f:
    fileContents = f.read()
  
  try:
    publicKey = getPublicKey(userInfo)
  except Exception:
    console.print(f"Could not read your public key from {userInfo.publicKeyPath}.", style="red")
    raise typer.Exit(code=1)
  fileKey = ''.join(random.choices(string.ascii_lowercase, k=BITBOX_FILE_KEY_LENGTH))
  
  encryptedFileBytes = cryptocode.encrypt(fileContents, fileKey).encode("utf-8")

  prepareSendBody = {
    "recipients": [],
    "bytes": len(encryptedFileBytes),
    "filename": remote_file
  }
  prepareSendResponse = attemptWithSession(
    lambda session: requests.post(f"http://{BITBOX_HOST}/api/storage/prepare-send",
      headers={"Cookie": session},
      json=prepareSendBody),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: lambda: console.print("Authentication failed.", style="red"),
      BITBOX_ERR_FILE_TOO_LARGE: lambda: console.print("This file is too large to upload. Run `bitbox` to check how much space you have!", style="red"),
      BITBOX_ERR_FILE_EXISTS: lambda: console.print("This file already exists in your bitbox. Use the `--remote-file` flag to specify a different name.", style="red")
    })
  
  uploadURL = prepareSendResponse.json()["uploadURL"]
  resumableSession = requests.post(uploadURL, "", headers={
      "x-goog-resumable": "start",
      "content-type": "text/plain",
      "x-goog-content-length-range": f"0,{len(encryptedFileBytes)}"
  })
  if resumableSession.status_code != 201:
    console.print("Error while uploading file.", style="red")
    console.print(resumableSession.text)
    raise typer.Exit(code=1)
  
  location = resumableSession.headers["location"]
  uploadResponse = requests.put(location, data=encryptedFileBytes, headers={
    "content-type": "text/plain",
    "content-length": str(len(encryptedFileBytes))
  })
  if uploadResponse.status_code != 200:
    console.print("Error while uploading file.", style="red")
    console.print(uploadResponse.text)
    raise typer.Exit(code=1)
  
  fileId = prepareSendResponse.json()["fileId"]
  personalEncryptedKey = rsaEncrypt(fileKey.encode("utf8"), publicKey)
  personalEncryptedKeyHex = binascii.hexlify(personalEncryptedKey).decode("utf-8")
  sendBody = {
    "fileId": fileId,
    "personalEncryptedKey": personalEncryptedKeyHex,
    "recipientEncryptedKeys": {}
  }
  attemptWithSession(
    lambda session: requests.post(f"http://{BITBOX_HOST}/api/storage/send",
      headers={"Cookie": session},
      json=sendBody),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: lambda: console.print("Authentication failed.", style="red")
    })

  typer.echo(f"{file} has been added to your bitbox as '@{userInfo.username}/{remote_file}'.")

@app.command(short_help="Clone a file from your bitbox onto your local machine")
def clone(file: str, local_file: str = None):
  if (local_file == None):
    local_file = os.path.basename(file)
  
  if (os.path.exists(local_file)):
    console.print(f"File {local_file} already exists. Use the `--local-file` flag to specify a different name for the local file.", style="red")
    raise typer.Exit(code=1)

  try:
    userInfo, session = loginUser()
  except Exception as e:
    if e.args[0] == BITBOX_ERR_CONFIG_PARSE_FAILED:
      console.print("Could not parse your user info. Have you set up bitbox with `bitbox setup`?", style="red")
    else:
      console.print("Authentication failed.", style="red")
    raise typer.Exit(code=1)

  if (re.match(BITBOX_FILENAME_REGEX, file)):
    splitFile = file.split("/")
    filename = splitFile[1]
    saveBody = {
      "owner": splitFile[0],
      "filename": filename
    }
  else:
    filename = file
    saveBody = {
      "filename": filename
    }

  saveResponse = attemptWithSession(
    lambda session: requests.post(f"http://{BITBOX_HOST}/api/storage/save",
      headers={"Cookie": session},
      json=saveBody),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: lambda: console.print("Authentication failed.", style="red"),
      BITBOX_ERR_FILE_NOT_FOUND: lambda: console.print("This file does not exist in your bitbox.", style="red"),
      BITBOX_ERR_USER_NOT_FOUND: lambda: console.print(f"User '@{saveBody['owner']}' does not exist.", style="red"),
      BITBOX_ERR_FILENAME_NOT_SPECIFIC: lambda: console.print(f"Filename '{filename}' is ambiguous. Please specify the owner of the file using the '@someuser/somefile' syntax.", style="red")
    })
  downloadURL = saveResponse.json()["downloadURL"]
  encryptedKey = saveResponse.json()["encryptedKey"]

  personalKey = getPersonalKey()

  downloadResponse = requests.get(downloadURL)
  if downloadResponse.status_code != 200:
    console.print("Error while downloading file.", style="red")
    console.print(downloadResponse.text)
    raise typer.Exit(code=1)

  downloadFileContents = downloadResponse.text
  privateKey = getPrivateKey(userInfo, personalKey)
  decryptedFileKey = rsaDecrypt(binascii.unhexlify(encryptedKey), privateKey)
  filekey = decryptedFileKey.decode("utf-8")
  fileContents = cryptocode.decrypt(downloadFileContents, filekey)

  with open(filename, "w") as f:
    f.write(fileContents)

  typer.echo(f"{file} has been cloned to your local machine as {local_file}.")

@app.command(short_help="Share a file from your bitbox with other users")
def share(file: str, recipients: list[str]):
  try:
    userInfo, session = loginUser()
  except Exception as e:
    if e.args[0] == BITBOX_ERR_CONFIG_PARSE_FAILED:
      console.print("Could not parse your user info. Have you set up bitbox with `bitbox setup`?", style="red")
    else:
      console.print("Authentication failed.", style="red")
    raise typer.Exit(code=1)

  fileInfoResponse = attemptWithSession(
    lambda session: requests.post(f"http://{BITBOX_HOST}/api/info/file",
      headers={"Cookie": session},
      json={"filename": file, "owner": userInfo.username}),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: console.print("Authentication failed.", style="red"),
      BITBOX_ERR_FILE_NOT_FOUND: console.print("This file does not exist in your bitbox.", style="red")
    })
  fileInfo = fileInfoResponse.json()
  encryptedKey = fileInfo["encryptedKey"]
  
  publicKeys = {}
  for recipient in recipients:
    if (not recipient.startswith("@")):
      console.print(f"Invalid username '{recipient}' specified as recipient-- usernames must start with '@'.", style="red")
      raise typer.Exit(code=1)
    recipientInfoResponse = requests.post(f"http://{BITBOX_HOST}/api/info/user",
        json={"username": recipient[1:]})
    publicKeys[recipient[1:]] = RSA.import_key(recipientInfoResponse.json()["publicKey"])
  console.print(publicKeys)

  personalKey = getPersonalKey()
  privateKey = getPrivateKey(userInfo, personalKey)
  decryptedFileKey = rsaDecrypt(binascii.unhexlify(encryptedKey), privateKey)

  recipientEncryptedKeys = {}
  for recipient, publicKey in publicKeys.items():
    recipientEncryptedFileKey = rsaEncrypt(decryptedFileKey, publicKey)
    recipientEncryptedFileKeyHex = binascii.hexlify(recipientEncryptedFileKey).decode("utf-8")
    recipientEncryptedKeys[recipient] = recipientEncryptedFileKeyHex
  
  shareBody = {
    "filename": file,
    "recipientEncryptedKeys": recipientEncryptedKeys
  }
  shareResponse = attemptWithSession(
    lambda session: requests.post(f"http://{BITBOX_HOST}/api/storage/share",
      headers={"Cookie": session},
      json=shareBody),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: lambda: console.print("Authentication failed.", style="red"),
      BITBOX_ERR_FILE_NOT_FOUND: lambda: console.print(f"File {file} does not exist in your bitbox.", style="red"),
      BITBOX_ERR_USER_NOT_FOUND: lambda: console.print(f"One of the recipients you specified does not exist.", style="red"),
    })
  
  if (shareResponse.status_code == BITBOX_STATUS_OK):
    console.print(f"{file} has been shared with: {', '.join(recipients)}")
  else:
    console.print(shareResponse.text)
    raise typer.Exit(1)

@app.command(short_help="Delete a file from your bitbox")
def delete(file: str):
  try:
    userInfo, session = loginUser()
  except Exception as e:
    if e.args[0] == BITBOX_ERR_CONFIG_PARSE_FAILED:
      console.print("Could not parse your user info. Have you set up bitbox with `bitbox setup`?", style="red")
    else:
      console.print("Authentication failed.", style="red")
    raise typer.Exit(code=1)

  deleteBody = {
    "filename": file
  }
  attemptWithSession(
    lambda session: requests.post(f"http://{BITBOX_HOST}/api/storage/delete",
      headers={"Cookie": session},
      json=deleteBody),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: lambda: console.print("Authentication failed.", style="red"),
      BITBOX_ERR_FILE_NOT_FOUND: lambda: console.print(f"File '{file}' does not exist in your bitbox.", style="red")
    })
  typer.echo(f"{file} has been deleted from your bitbox.")

@app.command(short_help="List all files in your bitbox")
def files():
  try:
    userInfo, session = loginUser()
  except Exception as e:
    if e.args[0] == BITBOX_ERR_CONFIG_PARSE_FAILED:
      console.print("Could not parse your user info. Have you set up bitbox with `bitbox setup`?", style="red")
    else:
      console.print("Authentication failed.", style="red")
    raise typer.Exit(code=1)

  filesResponse = attemptWithSession(
    lambda session: requests.get(f"http://{BITBOX_HOST}/api/info/files",
      headers={"Cookie": session},
      json={}),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: lambda: console.print("Authentication failed.", style="red")
    })
  filesInfo : list[FileInfo] = [FileInfo(**fileInfo) for fileInfo in filesResponse.json()]

  table = Table()
  table.add_column("Filename")
  table.add_column("Size")
  table.add_column("Last Modified (GMT)")
  for fileInfo in filesInfo:
    if fileInfo.owner != userInfo.username:
      filename = f"@{fileInfo.owner}/{fileInfo.name}"
    else:
      filename = fileInfo.name
    table.add_row(filename, humanReadableFilesize(fileInfo.bytes), humanReadableJSTimestamp(fileInfo.lastModified))
  console.print(table)

@app.command(short_help="Generate a one-time-code to setup Bitbox on another machine")
def otc():
  try:
    userInfo, session = loginUser()
  except Exception as e:
    if e.args[0] == BITBOX_ERR_CONFIG_PARSE_FAILED:
      console.print("Could not parse your user info. Have you set up bitbox with `bitbox setup`?", style="red")
    else:
      console.print("Authentication failed.", style="red")
    raise typer.Exit(code=1)

  otcResponse = attemptWithSession(
    lambda session: requests.get(f"http://{BITBOX_HOST}/api/auth/recover/generate-otc",
      headers={"Cookie": session}),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: lambda: console.print("Authentication failed.", style="red")
    })
  otc = otcResponse.text
  otcWords = [otcDict[otc[i:i+2].upper()].lower() for i in range(0, len(otc), 2)]
  console.print(f"[bold]Your one-time-code is:[/bold] [green]{' '.join(otcWords)}[/green]\n")
  console.print("Enter this code on the machine you want to set up a new Bitbox client on.")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
  if ctx.invoked_subcommand is not None:
    return

  try:
    userInfo, session = loginUser()
  except Exception as e:
    if e.args[0] == BITBOX_ERR_CONFIG_PARSE_FAILED:
      console.print("Could not parse your user info. Have you set up bitbox with `bitbox setup`?", style="red")
    else:
      console.print("Authentication failed.", style="red")
    raise typer.Exit(code=1)

  console.print(f"You are logged in as: {userInfo.username}")
  console.print(f"")
  filesResponse = attemptWithSession(
    lambda session: requests.get(f"http://{BITBOX_HOST}/api/info/files",
      headers={"Cookie": session},
      json={}),
    session, userInfo, exceptions={
      BITBOX_ERR_AUTHENTICATION_FAILED: lambda: console.print("Authentication failed.", style="red")
    })
  filesInfo : list[FileInfo] = [FileInfo(**fileInfo) for fileInfo in filesResponse.json()]

  table = Table()
  table.add_column("Filename")
  table.add_column("Size")
  table.add_column("Last Modified (GMT)")
  for fileInfo in filesInfo:
    if fileInfo.owner != userInfo.username:
      filename = f"@{fileInfo.owner}/{fileInfo.name}"
    else:
      filename = fileInfo.name
    table.add_row(filename, humanReadableFilesize(fileInfo.bytes), humanReadableJSTimestamp(fileInfo.lastModified))
  console.print(table)
  console.print("")
  bytesUsed = sum([fileInfo.bytes for fileInfo in filesInfo])
  console.print(f"Total space usage: {humanReadableFilesize(bytesUsed)} / 1 GiB ({bytesUsed / 1073741824 :.0%})")