import os

BITBOX_HOST = "localhost:8000"
BITBOX_CONFIG_FOLDER = os.path.join(os.getcwd(), ".bitbox")
BITBOX_CLIENT_NAME_LENGTH = 10
BITBOX_STATUS_OK = 200
BITBOX_FILE_KEY_LENGTH = 128
BITBOX_USERNAME_REGEX = r"^[a-z0-9]+$"
BITBOX_FILENAME_REGEX = r"^@[a-z0-9]+\/[^\/\r\n ]+$"

BITBOX_ERR_AUTHENTICATION_FAILED = "authentication-failed"
BITBOX_ERR_USER_NOT_FOUND = "user-not-found"
BITBOX_ERR_CONFIG_PARSE_FAILED = "config-parse-failed"
BITBOX_ERR_USER_EXISTS = "user-exists"
BITBOX_ERR_INVALID_USERNAME = "invalid-username"
BITBOX_ERR_FILE_TOO_LARGE = "file-too-large"
BITBOX_ERR_FILE_EXISTS = "file-exists"
BITBOX_ERR_FILE_NOT_FOUND = "file-not-found"
BITBOX_ERR_FILENAME_NOT_SPECIFIC = "filename-not-specific"
