import sys
import time
import os
import pyaudio
from lvt.const import *

config = None

class Animator:
    def setConfig( gConfig ):
        global config
        config = gConfig

    def __init__( this ):
        pass
    def animate( this, animation ):
        print( f'Animationg effect {animation}' )
    