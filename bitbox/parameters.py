import os

#
# Configurable parameters
#

BITBOX_HOST = os.environ.get("BITBOX_HOST") or "sidtrehan.me:8000"
BITBOX_CONFIG_FOLDER = os.environ.get("BITBOX_CONFIG_FOLDER") or os.path.join(os.path.expanduser("~"), ".bitbox")

#
# Other parameters
#

BITBOX_VERSION = "0.1.0"
BITBOX_STATUS_OK = 200
BITBOX_USERNAME_REGEX = r"^[a-z0-9]+$"
BITBOX_FILENAME_REGEX = r"^@[a-z0-9]+\/[^\/\r\n ]+$"
