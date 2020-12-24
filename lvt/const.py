import os

# Program start directory
#ROOT_DIR = os.path.abspath( os.curdir )
ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) )

LOGLEVEL_NONE = 0
LOGLEVEL_ERROR = 1
LOGLEVEL_INFO = 2
LOGLEVEL_DEBUG = 3
LOGLEVEL_VERBOSE = 9

VERSION = "0.0.4"

# Animation effect names
ANIMATION_NONE = "None"
ANIMATION_AWAKE = "Awake"
ANIMATION_MUTE = "Mute"
ANIMATION_THINK = "Think"
ANIMATION_ACCEPT = "Accept"
ANIMATION_CANCEL = "Cancel"

ANIMATION_ALL = {ANIMATION_NONE, ANIMATION_AWAKE, ANIMATION_MUTE, ANIMATION_THINK, ANIMATION_ACCEPT, ANIMATION_CANCEL }

# TTS Engines supported
TTS_RHVOICE = "RHVoice"

TTS_ALL = {TTS_RHVOICE}

# State macnine well-known toipcs:

TOPIC_ALL = '*'
TOPIC_DEFAULT = ''
