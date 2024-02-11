#!/usr/bin/env python3
import json
import os
import sys
import time

sys.path.append(os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) ))

from lvt.const import *
from lvt.protocol import *
from lvt.logger import *
from lvt.server.skill import Skill

# PJProject
# https://github.com/pjsip/pjproject
# https://docs.pjsip.org/en/2.13/api/generated/pjmedia/group/group__PJMEDIA__Echo__Cancel.html


# Альтернативный:
# https://pypi.org/project/adaptfilt/



