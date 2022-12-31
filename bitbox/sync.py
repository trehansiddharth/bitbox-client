from dataclasses import dataclass
from typing import Optional
from bitbox.parameters import *
import json
import os
import shutil

BITBOX_SYNCS_FOLDER = os.path.join(BITBOX_CONFIG_FOLDER, "syncs")
BITBOX_SYNC_INFO_PATH = os.path.join(BITBOX_CONFIG_FOLDER, "syncinfo.json")

Inode = int

@dataclass
class SyncRecord:
  syncId: int
  fileId: str
  lastHash: str
  inode: Inode

SyncInfo = list[SyncRecord]

#
# Utility functions
#

# Raises: ConfigParseFailed
def readSyncInfo() -> SyncInfo:
  try:
    with open(BITBOX_SYNC_INFO_PATH, "r") as f:
      syncInfoJSON = json.load(f)
  except Exception as e:
    raise Exception(Error.CONFIG_PARSE_FAILED)
  return [SyncRecord(**syncRecord) for syncRecord in syncInfoJSON]

# Raises: ConfigParseFailed
def writeSyncInfo(syncInfo: SyncInfo) -> None:
  syncInfoJSON = [syncRecord.__dict__ for syncRecord in syncInfo]
  try:
    with open(BITBOX_SYNC_INFO_PATH, "w") as f:
      json.dump(syncInfoJSON, f, indent=2)
  except Exception as e:
    raise Exception(Error.CONFIG_PARSE_FAILED)

def findInSyncByInode(syncInfo: SyncInfo, inode: Inode) -> Optional[SyncRecord]:
  for syncRecord in syncInfo:
    if syncRecord.inode == inode:
      return syncRecord

def getSyncRecord(syncInfo: SyncInfo, id: int) -> Optional[SyncRecord]:
  for syncRecord in syncInfo:
    if syncRecord.syncId == id:
      return syncRecord

def getNewSyncId(syncInfo: SyncInfo) -> int:
  return max([syncRecord.syncId for syncRecord in syncInfo] + [0]) + 1

def getLinkName(syncRecord: SyncRecord) -> str:
  return os.path.join(BITBOX_SYNCS_FOLDER, f"{syncRecord.fileId}_{syncRecord.syncId}")

#
# Exports
#

# Raises: ConfigParseFailed, SyncExists
def createSync(fileId: str, hash: str, localFile: str):
  # Get inode of file
  inode = os.stat(localFile).st_ino

  # Read sync info
  syncInfo = readSyncInfo()

  # Check if sync already exists
  syncRecord = findInSyncByInode(syncInfo, inode)
  if syncRecord != None:
    raise Exception(Error.SYNC_EXISTS)
  
  # Create an id for the sync that doesn't exist yet
  syncId = getNewSyncId(syncInfo)
  
  # Add record to sync info
  newSyncRecord = SyncRecord(
    syncId=syncId,
    fileId=fileId,
    lastHash=hash,
    inode=inode
  )
  syncInfo.append(newSyncRecord)

  # Create hard link to local file
  os.link(localFile, getLinkName(newSyncRecord))

  # Write sync info
  writeSyncInfo(syncInfo)

# Raises: ConfigParseFailed
def lookupSync(localFile: str) -> Optional[SyncRecord]:
  # Get inode of file
  inode = os.stat(localFile).st_ino

  # Read sync info
  syncInfo = readSyncInfo()

  # Find sync record by inode
  syncRecord = findInSyncByInode(syncInfo, inode)

  # Return sync record
  return syncRecord

# Raises: ConfigParseFailed
def lookupSyncByRemote(fileId: str) -> Optional[SyncRecord]:
  # Read sync info
  syncInfo = readSyncInfo()

  # Find sync record by owner and filename
  for syncRecord in syncInfo:
    if syncRecord.fileId == fileId:
      return syncRecord

# Raises: ConfigParseFailed
def updateSync(localFile: str, hash: str):
  # Get inode of file
  inode = os.stat(localFile).st_ino

  # Read sync info
  syncInfo = readSyncInfo()

  # Find sync record by inode
  syncRecord = findInSyncByInode(syncInfo, inode)
  if syncRecord == None:
    raise Exception(Error.SYNC_NOT_FOUND)
  
  # Update sync record
  syncRecord.lastHash = hash

  # Write sync info
  writeSyncInfo(syncInfo)

# Raises: ConfigParseFailed, Exception
def copySync(id: int, localFile: str):
  # Read sync info
  syncInfo = readSyncInfo()

  # Find sync record by id
  syncRecord = getSyncRecord(syncInfo, id)
  if syncRecord == None:
    raise Exception
  
  # Get the inode of the old hard link
  oldLinkName = getLinkName(syncRecord)
  inode = os.stat(oldLinkName).st_ino
  
  # Create new sync id
  newSyncId = getNewSyncId(syncInfo)
  
  # Create new sync record
  newSyncRecord = SyncRecord(
    syncId=newSyncId,
    fileId=syncRecord.fileId,
    lastHash=syncRecord.lastHash,
    inode=inode
  )

  # Add new sync record to sync info
  syncInfo.append(newSyncRecord)

  # Copy the hard link
  newLinkName = getLinkName(newSyncRecord)
  shutil.copyfile(oldLinkName, newLinkName)

  # Create hard link to local file
  os.link(newLinkName, localFile)

  # Write sync info
  writeSyncInfo(syncInfo)

# Raises: ConfigParseFailed, Exception
def deleteSyncsByRemote(fileId: str):
  # Read sync info
  syncInfo = readSyncInfo()

  # Create a variable for the updated sync info
  newSyncInfo = []

  # Remove syncs corresponding to the file that is to be deleted
  for syncRecord in syncInfo:
    if syncRecord.fileId == fileId:
      # Remove hard link
      os.unlink(getLinkName(syncRecord))
    else:
      newSyncInfo.append(syncRecord)
  
  # Write sync info
  writeSyncInfo(newSyncInfo)
