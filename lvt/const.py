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

VERSION = "0.9.34"

# Voice sampling rate.

VOICE_SAMPLING_RATE = 16000

# TTS Engines supported
TTS_RHVOICE = "RHVoice"
TTS_SAPI = "SAPI"

TTS_ALL = frozenset(TTS_RHVOICE)

# State macnine well-known toipcs:

TOPIC_ALL = '*'
TOPIC_DEFAULT = 'DefaultTopic'

HA_NEGOTIATE_SKILL = 'HomeAssistantNegotiateSkill'
HA_INTENTS_SKILL = 'HomeAssistantIntentsSkill'
HA_LISTENER_SKILL = 'HomeAssistantListenerSkill'

