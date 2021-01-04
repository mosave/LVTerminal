import sys
import time
import datetime
import json
import threading
import requests
from lvt.const import *
from lvt.logger import *
from lvt.config_parser import ConfigParser
from lvt.server.mqtt import MQTT
from lvt.server.entities import Entities

config = None
deviceTypes = None
devices = None

def httpGet( url, user, password ):
    try:
        if user and password :
            auth = requests.auth.HTTPBasicAuth( user, password )
        else :
            auth = None
        r = requests.get( url, auth=auth )
    except Exception as e:
        logError( f'HTTP GET("{url}","payload"): {e}' )

def httpPost( url, user, password, data ):
    try:
        if user and password :
            auth = requests.auth.HTTPBasicAuth( user, password )
        else :
            auth = None
        r = requests.post( url, auth=auth,data=data )
    except Exception as e:
        logError( f'HTTP POST("{url}","payload"): {e}' )


class Action():
    def __init__( this ):
        this.action = None
        this.url = None
        this.data = None
        this.user = None
        this.password = None


    def execute( this ):
        if this.action == None or this.action == 'none' :
            pass
        elif this.action == 'mqtt' :
            MQTT.publish( this.url, bytes(this.data,'utf-8') )
        elif this.action == 'get' :
            thread = threading.Thread( target=httpGet, args=[this.url, this.user, this.password] )
            thread.daemon = False
            thread.start()
        elif this.action == 'post' :
            thread = threading.Thread( target=httpPost, args=[this.url, this.user, this.password, this.data] )
            thread.daemon = False
            thread.start()

class DeviceType():
    def __init__( this, names, methods ):
        if isinstance( names, str ) : names = [names]
        this.names = names
        this.methods = methods

    @property
    def name( this ) -> str:
        """Основное название типа устройтсв"""
        return this.names[0]


class Device():
    def __init__( this, id: str, source: str='config' ):
        global deviceTypes
        if source not in DEVICE_SOURCES :
            raise Exception( f'Invalid device source: {source}. Should be one of {SOURCES}' )

        this.id = id
        this.names = [id]
        this.source = source
        this.methods = dict()
        this._typeName = ''
        this.type = deviceTypes[0]
        this.location = ''
        this.isDefault = False
        this.user = None
        this.password = None

    @property
    def name( this ) -> str:
        """Основное название типа устройств"""
        return this.names[0]

    @property 
    def typeName( this ) :
        return this._typeName

    @typeName.setter
    def typeName( this, newTypeName ):
        global deviceTypes
        newTypeName = newTypeName.lower()
        this.type = None
        for t in deviceTypes:
            a = [tn for tn in t.names if tn == newTypeName]
            if len( a ) > 0 : 
                this.type = t
                break
        if this.type == None :
            raise Exception( f'Указан недопустимый тип устройства {newTypeName} ' )

        this._typeName = newTypeName
        methods = dict()
        for m in this.methods.keys() :
            if m in this.type.methods :
                methods[m] = this.methods[m]
        for m in this.type.methods :
            if m not in methods.keys():
                methods[m] = Action()
        this.methods = methods


class Devices():
    """Entities class. Single-instance in-memory world facts
    """
    def __init__( this ):
        pass
    @property
    def deviceTypes( this ) -> dict:
        """Типы устройств"""
        global deviceTypes
        return deviceTypes

    @property
    def devices( this ) -> dict:
        """Список локаций"""
        global devices
        return devices

### Static methods #####################################################################
#region
    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global deviceTypes
        global devices

        config = gConfig

        deviceTypes = list()
        deviceTypes.append( DeviceType( \
            [''], \
            ['on', 'off'] ) )
        deviceTypes.append( DeviceType( \
            ['свет', 'освещение', 'подсветка', 'светильник', 'лампа'], \
            ['on', 'off'] ) )
        deviceTypes.append( DeviceType( \
            ['обогрев','нагреватель','теплый пол','камин'], \
            ['on', 'off'] ) )
        deviceTypes.append( DeviceType( \
            ['дверь','ворота'], \
            ['open', 'close'] ) )
        deviceTypes.append( DeviceType( \
            ['окно','шторы','ставни','рольставни'], \
            ['open', 'close'] ) )
        entities = Entities()
        devices = dict()
        p = ConfigParser( os.path.join( 'lvt','entities', 'devices' ) )
        for section in p.sections:
            id = section.split( '|' )[0]
            device = Device( id )
            names = p.getValue( section,'name',id )
            if isinstance( names,str ) : names = [names]
            device.names = names
            device.typeName = p.getValue( section,'type','' )
            l = p.getValue( section,'Location','' )
            device.location = entities.findLocation( l )
            if l != '' and device.location == None:
                raise Exception( f'Устройство {id}: неверное значение параметра location: "{l}"' )

            device.isDefault = bool( p.getValue( section,'Default','0' ) == '1' )
            user = p.getValue( section,'User',None )
            password = p.getValue( section,'Password',None )
            for m in device.methods :
                device.methods[m].user = user
                device.methods[m].password = password
                action = p.getRawValue( section, m )
                if isinstance( action, list ) and len( action ) > 1 :
                    if action[0].lower() not in DEVICE_ACTIONS:
                        raise Exception( f'Метод {id}.{m} должен быть один из {DEVICE_ACTIONS}' )
                    device.methods[m].action = action[0].lower()
                    device.methods[m].url = action[1]
                    if len( action ) > 2 :
                        device.methods[m].data = action[2]
                        if device.methods[m].action=='post':
                            try:
                                j = dict( json.loads( action[2] ) )
                            except Exception as e:
                                raise Exception( f'Метод {id}.{m}: ошибка в JSON' )
                    else :
                        device.methods[m].params = None
                elif action != None :
                    raise Exception( f'Ошибка в определении метода {id}.{m}' )

            devices[id] = device

        Devices.updateDefaultDevices()

    def updateDefaultDevices():
        global devices
        #dtypes = set([d.type.name for id,d in devices if d.location!=''])
        dtypes = set()
        for d in devices.values(): dtypes.add( d.type.name )

        for type in dtypes :
            devs = [d for d in devices.values() if d.type.name == type]
            locs = dict()
            for d in devs :
                # Оставить isDefault только у одного устройства
                if d.location not in locs.keys() : locs[d.location] = False
                if d.isDefault : 
                    if locs[d.location] : d.isDefault = False
                    locs[d.location] = True
            for d in devs :
                if not locs[d.location] :
                    d.isDefault = True
                    locs[d.location] = True

    def dispose():
        pass

#endregion
