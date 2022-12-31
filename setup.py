from distutils.core import setup
from bitbox import parameters

setup(
  name="bitbox",
  version=parameters.BITBOX_VERSION,
  description="A command-line mailbox for storing and sharing files",
  packages=["bitbox"],
  author="Siddharth Trehan",
  license="MIT",
  long_description=open("README.md").read(),
  entry_points={
    "console_scripts": [
      "bitbox = bitbox.main:run"
    ],
  },
  install_requires=[
    "cryptocode>=0.1",
    "cryptography>=38.0.4",
    "keyring>=23.11.0",
    "mypy>=0.991",
    "pycryptodome>=3.16.0",
    "requests>=2.28.1",
    "rich>=12.6.0",
    "rsa>=4.9",
    "typer>=0.7.0",
  ],
)
