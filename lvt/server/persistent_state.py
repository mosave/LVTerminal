import json
import os

from lvt.const import *
from lvt.server.grammar import *
from lvt.protocol import *
from lvt.logger import *
import lvt.server.config as config
import lvt.server.terminal as terminals

api_tts = None

storage = {}
storage_ = ""

def restore():
    global storage
    global storage_
    if bool(config.storageFile) and os.path.isfile(config.storageFile):
        try:
            with open(config.storageFile) as jf:
                storage_ = jf.read()
                storage = json.loads(storage_)
                if 'Terminals' in storage:
                    terminals.states = storage['Terminals']
        except Exception as e:
            logError(f"Error restoring persistent state from {config.storageFile}: {e}")

def save():
    global storage
    global storage_
    if bool(config.storageFile):
        try:
            storage['Terminals'] = terminals.states
            js = json.dumps( storage, indent=4)
            if js != storage_ :
                with open(config.storageFile, 'w') as jf:
                    jf.write(js)
                storage_ = js
        except Exception as e:
            logError(f"Error saving persistent state to {config.storageFile}: {e}")
