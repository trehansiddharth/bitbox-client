import os
from errors import *

BITBOX_HOST = "localhost:8000"
BITBOX_CONFIG_FOLDER = os.path.join(os.getcwd(), ".bitbox")
BITBOX_CLIENT_NAME_LENGTH = 10
BITBOX_STATUS_OK = 200
BITBOX_FILE_KEY_LENGTH = 128
BITBOX_USERNAME_REGEX = r"^[a-z0-9]+$"
BITBOX_FILENAME_REGEX = r"^@[a-z0-9]+\/[^\/\r\n ]+$"
