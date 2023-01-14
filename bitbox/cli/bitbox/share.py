from bitbox.cli.bitbox.common import *
from bitbox.cli import *
import bitbox.server as server
import binascii

#
# Share command
#

@app.command(short_help="Share a file from your bitbox with other users")
def share(
  remote: str = typer.Argument(..., help="Name of the remote file to share"),
  recipients: List[str] = typer.Argument(..., help="Usernames of the users to share the file with")):
  # Get user info and try to establish a session
  authInfo = config.load()

  # Get the encrypted file key from the server
  fileInfo = server.fileInfo(remote, authInfo.keyInfo.username, authInfo)
  guard(fileInfo, {
    Error.FILE_NOT_FOUND: f"Remote file '@{authInfo.keyInfo.username}/{remote}' does not exist."
  })
  fileId = fileInfo.fileId
  encryptedKey = fileInfo.encryptedKey
  
  # Get the public keys of the recipients
  publicKeys = {}
  for recipient in recipients:
    # Check if the recipient is a valid username
    if not recipient.startswith("@"):
      console.print(f"Invalid username '{recipient}' specified as recipient (usernames start with '@').", style="red")
      raise typer.Exit(code=1)
    
    # Get the public key of the recipient
    userInfoResponse = server.userInfo(recipient[1:])
    guard(userInfoResponse, {
      Error.USER_NOT_FOUND: f"User {recipient} does not exist."
    })
    publicKeys[recipient[1:]] = RSA.import_key(userInfoResponse.publicKey)

  # Decrypt the file key
  privateKey = authInfo.getPrivateKey()
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
  success(f"{remote} has been shared with: {', '.join(recipients)}")

  # Save the session back onto the disk
  config.setSession(authInfo.session)
