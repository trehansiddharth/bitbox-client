from bitbox.commands.common import *

#
# Share command
#

@app.command(short_help="Share a file from your bitbox with other users")
def share(file: str, recipients: list[str]):
  # Get user info and try to establish a session
  userInfo, session = loginUser()
  authInfo = AuthInfo(userInfo, session)

  # Get the encrypted file key from the server
  fileInfo = server.fileInfo(file, userInfo.username, authInfo)
  guard(fileInfo, {
    Error.FILE_NOT_FOUND: f"Remote file '@{userInfo.username}/{file}' does not exist."
  })
  fileId = fileInfo.fileId
  encryptedKey = fileInfo.encryptedKey
  
  # Get the public keys of the recipients
  publicKeys = {}
  for recipient in recipients:
    # Check if the recipient is a valid username
    if not recipient.startswith("@"):
      console.print(f"Invalid username '{recipient}' specified as recipient-- usernames must start with '@'.", style="red")
      raise typer.Exit(code=1)
    
    # Get the public key of the recipient
    userInfoResponse = server.userInfo(recipient[1:])
    guard(userInfoResponse, {
      Error.USER_NOT_FOUND: f"User {recipient} does not exist."
    })
    publicKeys[recipient[1:]] = RSA.import_key(userInfoResponse.publicKey)

  # Decrypt the file key
  if authInfo.personalKey is None:
    authInfo.personalKey = getPersonalKey()
  privateKey = getPrivateKey(userInfo, authInfo.personalKey)
  decryptedFileKey = rsaDecrypt(binascii.unhexlify(encryptedKey), privateKey)

  # Re-encrypt the file key for each recipient
  recipientEncryptedKeys = {}
  for recipient, publicKey in publicKeys.items():
    recipientEncryptedFileKey = rsaEncrypt(decryptedFileKey, publicKey)
    recipientEncryptedFileKeyHex = binascii.hexlify(recipientEncryptedFileKey).decode("utf-8")
    recipientEncryptedKeys[recipient] = recipientEncryptedFileKeyHex
  
  # Share the file with the recipients
  shareResponse = server.share(fileId, recipientEncryptedKeys, authInfo)
  guard(shareResponse)

  # Print a success message
  success(f"{file} has been shared with: {', '.join(recipients)}")
