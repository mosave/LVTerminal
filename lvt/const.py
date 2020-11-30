import os

# Program start directory
ROOT_DIR = os.path.abspath( os.path.join( os.curdir ) )

# Animation effect names
ANIMATION_NONE = "None"
ANIMATION_AWAKE = "Awake"
ANIMATION_LISTEN = "Listen"
ANIMATION_ACCEPTED = "Accepted"
ANIMATION_CANCELLED = "Cancelled"

ANIMATION_ALL = {ANIMATION_NONE, ANIMATION_AWAKE, ANIMATION_LISTEN, ANIMATION_ACCEPTED, ANIMATION_CANCELLED }

# TTS Engines supported

TTS_RHVOICE = "RHVoice"

TTS_ALL = {TTS_RHVOICE}