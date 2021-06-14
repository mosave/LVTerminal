import os

# Program start directory
#ROOT_DIR = os.path.abspath( os.curdir )
ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) )

LOGLEVEL_NONE = 0
LOGLEVEL_ERROR = 1
LOGLEVEL_INFO = 2
LOGLEVEL_DEBUG = 3
LOGLEVEL_VERBOSE = 9

VERSION = "0.0.7"

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

TOPIC_MD_ASK = 'MajorDoMoAsk'
TOPIC_MD_YES = 'MajorDoMoYes'
TOPIC_MD_NO  = 'MajorDoMoNo'
TOPIC_MD_CANCEL = 'MajorDoMoCancel'


TOPIC_WAIT_COMMAND = "WaitCommand"

WAIT_COMMAND_TIMEOUT = 5 # время в режиме ожидания команды, секунд


DEVICE_ACTIONS = frozenset({'none','get','post','mqtt'})
DEVICE_SOURCES = frozenset({'config','majordomo'})




