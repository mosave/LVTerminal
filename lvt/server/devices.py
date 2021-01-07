import sys
import time
import datetime
import json
import threading
from urllib.parse import urljoin, urlencode
import requests
from lvt.const import *
from lvt.logger import *
from lvt.config_parser import ConfigParser
from lvt.server.grammar import *
from lvt.server.mqtt import MQTT
from lvt.server.entities import Entities

config = None
deviceTypes = None
devices = None

### httpGet(), httpPost() action helpers ###############################################
#region
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
#endregion
### Action class: device' method encapsulation #########################################
#region
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
#endregion
### DeviceType class: specific device implementation ###################################
#region
class DeviceType():
    def __init__( this, names, methods ):
        if isinstance( names, str ) : names = [names]
        this.names = names
        this.methods = methods

    @property
    def name( this ) -> str:
        """Основное название типа устройтсв"""
        return this.names[0]

#endregion
### Device() class #####################################################################
#region
class Device():
    def __init__( this, id: str, source: str='config' ):
        global deviceTypes
        if source not in DEVICE_SOURCES :
            raise Exception( f'Invalid device source: {source}. Should be one of {SOURCES}' )

        this.id = id
        this.names = []
        this.source = source
        this.methods = dict()
        this._typeName = ''
        this.type = deviceTypes[0]
        this.location = ''
        this.locationId = None
        this.isDefault = False

    @property
    def name( this ) -> str:
        """Основное название типа устройств"""
        return this.names[0] if len(this.names)>0 else this.id

    @property 
    def typeName( this ) :
        return this._typeName

    @typeName.setter
    def typeName( this, newTypeName ):
        global deviceTypes
        newTypeName = newTypeName.lower()
        this.type = Devices().getTypeByName(newTypeName)
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
#endregion
### Devices() class: list of devices management ########################################
#region
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

    def getTypeByName( this, name: str ) -> DeviceType:
        global deviceTypes
        if name == None : return None
        name = str(name).lower()
        for t in deviceTypes:
            if name in t.names : return t
        return None

#endregion
### initialize(), dispose() ############################################################
#region
    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global deviceTypes
        global devices

        config = gConfig

        deviceTypes = list()
        #deviceTypes.append( DeviceType( \
        #    [''], \
        #    ['on', 'off'] ) )
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
        Devices.loadMajorDoMoDevices()
        Devices.updateDefaultDevices()

    def dispose():
        pass

#endregion
### getMajorDoMoDevices() ##############################################################
#region
    def loadMajorDoMoDevices():
        global config
        global devices
        if not config.mdServer or not config.mdIntegration :
            return

        if config.mdUser!='' and config.mdPassword!='' :
            auth = requests.auth.HTTPBasicAuth( config.mdUser, config.mdPassword )
        else :
            auth = None
        try:
            url = urljoin(os.environ.get("BASE_URL", config.mdServer ), '/lvt.php' )
            md = requests.get( url, auth=auth ).json()
        except Exception as ex:
            logError(f'Error querying MajorDoMo integration script {url}: {ex}')


        entities = Entities()
        try:
            for l in md['locations'] :
                ln = normalizeWords(l['Title'])
                if entities.findLocation( ln ) == None : 
                    entities.locations.append( list([ln]) )
        except Exception as ex:
            logError(f'Error processing MajorDoMo locations: {ex}')

        ids = [id for id in devices if devices[id].source=='majordomo' ]
        for id in ids : devices.pop(id)

        for d in md['devices'] :
            try:
                id = d['Id']
                name = normalizeWords(d['Title'])
                if not name or id in devices : continue
                type = Devices().getTypeByName(d['DeviceType'])
                if type==None : continue

                device = Device( id,'majordomo' )

                if name not in device.names : 
                    device.names.append(name)

                names = prasesToList(normalizePhrases(d['AltTitles']))
                for name in names :
                    if name and name not in device.names : 
                        device.names.append(name)

                device.typeName = d['DeviceType']
                device.locationId = d['LocationId']
                device.location = entities.findLocation( d['Location'] )
                mdMethods = {'on':'turnOn',
                             'off': 'turnOff',
                             'open':'open',
                             'close': 'close'
                    }
                for m in device.methods :
                    if m in mdMethods :
                        device.methods[m].user = config.mdUser
                        device.methods[m].password = config.mdPassword
                        device.methods[m].action = 'get'
                        device.methods[m].url = urljoin( \
                            os.environ.get("BASE_URL", config.mdServer ), \
                            f'/objects/?object={id}&op=m&m={mdMethods[m]}' )
                devices[id] = device
            except Exception as ex:
                logError(f'Error processing MajorDoMo locations: {ex}')

#endregion
### updateDefaultDevices() #############################################################
#region
    def updateDefaultDevices():
        global devices
        #dtypes = set([d.type.name for id,d in devices if d.location!=''])
        dtypes = set()
        for d in devices.values(): dtypes.add( d.type.name )

        # Для каждого типа устройств:
        for type in dtypes :
            devs = [d for d in devices.values() if d.type.name == type]
            locs = dict()
            # Просмотреть location'ы и проверить, есть ли в них устройства "по умолчанию"
            for d in devs :
                if d.location not in locs.keys() : locs[d.location] = False
                if d.isDefault : 
                    ## Оставить isDefault только у одного устройства
                    #if locs[d.location] : d.isDefault = False
                    locs[d.location] = True

            # Если в локации нет устройств "по умолчанию" - делаем таковым первый попавшийся.
            for d in devs :
                if not locs[d.location] :
                    d.isDefault = True
                    locs[d.location] = True
#endregion
