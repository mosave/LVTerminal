#!/usr/bin/env python3
import json
import os
import sys
import time

sys.path.append(os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) ))

from lvt.const import *
from lvt.protocol import *
from lvt.logger import *
import lvt.server.config
from lvt.server.skill import Skill
from lvt.server.skills.yes_no import YesNoParams

config = Config()
config.logFileName = "logs/test2.log"
config.logLevel = logging.DEBUG
config.printLevel = logging.DEBUG
logs = list()
LoggerInit( config )
LoggerCapture(logs)

def onTopicChangeAsync( params:dict={} ):

    print(params)



def a (*args, **kwargs):
    params = kwargs
    if len(args)==1 and isinstance(args[0],dict) : 
        params.update( args[0] )
    elif len(args)>0 : 
        params.update({'params':args})

    await onTopicChangeAsync(params)

p = {'p1' : 'v1'}
print(p['p1'])
if p['p2']=='' : print('blablabla')
print(p['p2'])

a()
await onTopicChangeAsync()

a({'p1' : 'v1', 'p2': 'v2' })
a(p1='v1', p2='v2')

a(YesNoParams("messagggge", 'tYes', 'tNo', 'tCancel'))
await onTopicChangeAsync(YesNoParams("messagggge", 'tYes', 'tNo', 'tCancel'))



