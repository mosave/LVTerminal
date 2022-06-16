import os

# Program start directory
#ROOT_DIR = os.path.abspath( os.curdir )
ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) )
CONFIG_DIR = os.path.join( ROOT_DIR,'config' )

LOGLEVEL_NONE = 0
LOGLEVEL_ERROR = 1
LOGLEVEL_INFO = 2
LOGLEVEL_DEBUG = 3
LOGLEVEL_VERBOSE = 9

VERSION = "1.0.0"

# Voice sampling rate.

VOICE_SAMPLING_RATE = 16000


# Animation effect names
ANIMATION_NONE = "None"
ANIMATION_AWAKE = "Awake"
ANIMATION_THINK = "Think"
ANIMATION_ACCEPT = "Accept"
ANIMATION_CANCEL = "Cancel"

ANIMATION_ALL = frozenset({ANIMATION_NONE, ANIMATION_AWAKE, ANIMATION_THINK, ANIMATION_ACCEPT, ANIMATION_CANCEL})

ANIMATION_STICKY = frozenset({ANIMATION_NONE, ANIMATION_AWAKE, ANIMATION_THINK})

# TTS Engines supported
TTS_RHVOICE = "RHVoice"
TTS_SAPI = "SAPI"

TTS_ALL = frozenset(TTS_RHVOICE)

# State macnine well-known toipcs:

TOPIC_ALL = '*'
TOPIC_DEFAULT = 'DefaultTopic'
TOPIC_HA_NEGOTIATE = "HomeAssistantNegotiate"

LMS_MODE_PAUSE = 0
LMS_MODE_MUTE = 1

HA_NEGOTIATE_SKILL = 'HomeAssistantNegotiateSkill'
HA_INTENTS_SKILL = 'HomeAssistantIntentsSkill'

