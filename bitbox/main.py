import typer
import requests
import os
from rich.table import Table
from parameters import *
from util import *
from commands import *
import sync

def run():
  try:
    os.makedirs(BITBOX_CONFIG_FOLDER)
  except FileExistsError:
    pass

  try:
    os.makedirs(sync.BITBOX_SYNCS_FOLDER)
  except FileExistsError:
    pass

  if not os.path.exists(sync.BITBOX_SYNC_INFO_PATH):
    try:
      with open(sync.BITBOX_SYNC_INFO_PATH, "w") as f:
        f.write("[]")
    except FileExistsError:
      pass

  app()

if __name__ == "__main__":
  run()
