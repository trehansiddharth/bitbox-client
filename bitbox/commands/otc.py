from bitbox.commands.common import *

@app.command(short_help="Generate a one-time-code to setup Bitbox on another machine")
def otc():
  # Get user info and try to establish a session
  authInfo = loginUser()

  # Generate the one-time-code
  otc = server.generateOTC(authInfo)

  # Map the one-time-code to words
  otcWords = [otcDict[otc[i:i+2].upper()].lower() for i in range(0, len(otc), 2)]

  # Print the one-time-code
  console.print(f"[bold]Your one-time-code is:[/bold] [green]{' '.join(otcWords)}[/green]\n")
  console.print("Enter this code on the machine you want to set up a new Bitbox client on.")
