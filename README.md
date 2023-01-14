# Bitbox

This is a Python library for communication with the Bitbox Storage API, providing a simple encrypted file storage & sharing interface built on top of Google Cloud. It also contains two user-space command-line programs, `bitbox` and `bb`, for demo purposes. `bitbox` is a command-line file storage and sharing tool which allows users to easily synchronize local files scatttered across different directories with remotes, and share files with others. `bb` is a command-line clipboard which allows users to easily transfer files between different machines.

## Installation

To install the Python package and create the `bitbox` and `bb` executables, first create a virtual environment to contain the libraries and executables. This can be in whichever directory you choose.

```bash
python3 -m venv .venv
```

Then, activate the environment:

```bash
source .venv/bin/activate
```

Finally, `cd` into the root of this repository and install the libraries and executables:

```bash
pip3 install .
```

The `bitbox` and `bb` executables should be in your path as long as the virtual environment is activated. To permanently add these executables to your `$PATH`, add the following to your shell startup file (`.bashrc`, `.zshrc`, etc.):

```bash
export BITBOX_VENV_PATH=<absolute-path-of-venv>
export PATH=$PATH:$BITBOX_VENV_PATH/bin
```

## CLI Documentation

### Using Bitbox CLI

Documentation on `bitbox` is coming. Run `bitbox setup` to get started!

### Using BB Clipboard Manager

`bb` can copy and paste files from one location to another. It will work across machines and, in the future, between different users. To add a file to your clipboard, run:

```bash
bb clip myfile.txt
```

Then, to paste it somewhere else, you can go to that machine and run:

```bash
bb paste
```

And `myfile.txt` will appear in the current directory.

To set up `bb` across multiple machines, there is an authorization process. You need to obtain a one-time-code from one of the machines that you wish to link your clipboard to and paste it into the new machine. On the new machine you want to set up, run:

```bash
bb link
```

This will ask you to run the following command on an existing machine:

```bash
bb authorize
```

And copy the username and one-time-code you see there into the prompts in the new machine. Once you've completed this process successfully, the two clipboards will be linked, and you can copy content with one and paste with the other!
