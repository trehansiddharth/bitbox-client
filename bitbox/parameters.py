import os
import time

BITBOX_HOST = os.environ.get("BITBOX_HOST") or "sidtrehan.me:8000"
BITBOX_VERSION = "0.1.0"
BITBOX_STATUS_OK = 200

# A unique hex string for each time the program is run, used for logging
CURRENT_CONTEXT = hex(round(time.time() * 1000))[2:]
