#! /usr/bin/env python2.6
# -*- coding: utf-8 -*-

"""
Author: GlennNZ

"""

from datetime import datetime
from zoneinfo import ZoneInfo

import time as t
import os
import shutil
import logging
import sys
import requests
import traceback
from os import path
from collections import namedtuple
from collections import OrderedDict
import json
from functools import reduce

from queue import *
import threading

try:
    import indigo
except:
    pass

################################################################################
kHvacModeEnumToStrMap = {
	indigo.kHvacMode.Cool				: u"COOL",
	indigo.kHvacMode.Heat				: u"HEAT",
	indigo.kHvacMode.HeatCool			: u"AUTO",
	indigo.kHvacMode.Off				: u"OFF"
}

kFanModeEnumToStrMap = {
	indigo.kFanMode.AlwaysOn			: u"always on",
	indigo.kFanMode.Auto				: u"auto"
}

def _lookupActionStrFromHvacMode(hvacMode):
	return kHvacModeEnumToStrMap.get(hvacMode, u"OFF")

def _lookupActionStrFromFanMode(fanMode):
	return kFanModeEnumToStrMap.get(fanMode, u"unknown")
# update to python3 changes
################################################################################
class IndigoLogHandler(logging.Handler):
    def __init__(self, display_name, level=logging.NOTSET):
        super().__init__(level)
        self.displayName = display_name

    def emit(self, record):
        """ not used by this class; must be called independently by indigo """
        logmessage = ""
        try:
            levelno = int(record.levelno)
            is_error = False
            is_exception = False
            if self.level <= levelno:  ## should display this..
                if record.exc_info !=None:
                    is_exception = True
                if levelno == 5:	# 5
                    logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
                elif levelno == logging.DEBUG:	# 10
                    logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
                elif levelno == logging.INFO:		# 20
                    logmessage = record.getMessage()
                elif levelno == logging.WARNING:	# 30
                    logmessage = record.getMessage()
                elif levelno == logging.ERROR:		# 40
                    logmessage = '({}: Function: {}  line: {}):    Error :  Message : {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
                    is_error = True
                if is_exception:
                    logmessage = '({}: Function: {}  line: {}):    Exception :  Message : {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
                    indigo.server.log(message=logmessage, type=self.displayName, isError=is_error, level=levelno)
                    if record.exc_info !=None:
                        etype,value,tb = record.exc_info
                        tb_string = "".join(traceback.format_tb(tb))
                        indigo.server.log(f"Traceback:\n{tb_string}", type=self.displayName, isError=is_error, level=levelno)
                        indigo.server.log(f"Error in plugin execution:\n\n{traceback.format_exc(30)}", type=self.displayName, isError=is_error, level=levelno)
                    indigo.server.log(f"\nExc_info: {record.exc_info} \nExc_Text: {record.exc_text} \nStack_info: {record.stack_info}",type=self.displayName, isError=is_error, level=levelno)
                    return
                indigo.server.log(message=logmessage, type=self.displayName, isError=is_error, level=levelno)
        except Exception as ex:
            indigo.server.log(f"Error in Logging: {ex}",type=self.displayName, isError=is_error, level=levelno)
################################################################################
class QueCommand:
    def __init__(self, accessToken, serialNo, commandtype, commandbody, commandrepeats,
                 deviceid=None, hvacOperationMode=None, setpointCool=None, setpointHeat=None, zoneActive=None):
        self.commandaccessToken = accessToken
        self.commandSerialNo = serialNo
        self.commandtype = commandtype
        self.commandbody = commandbody
        self.commandrepeats = commandrepeats

        self.deviceid = deviceid
        self.hvacOperationMode = hvacOperationMode
        self.setpointCool = setpointCool
        self.setpointHeat = setpointHeat
        self.zoneActive = zoneActive

class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)s\t%(name)s.%(funcName)s:%(filename)s:%(lineno)s:\t%(message)s', datefmt='%d-%m-%Y %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)
        ################################################################################
        # Setup Logging
        ################################################################################
        self.logger.setLevel(logging.DEBUG)
        try:
            self.logLevel = int(self.pluginPrefs["showDebugLevel"])
            self.fileloglevel = int(self.pluginPrefs["showDebugFileLevel"])
        except:
            self.logLevel = logging.INFO
            self.fileloglevel = logging.DEBUG

        self.logger.removeHandler(self.indigo_log_handler)
        self.indigo_log_handler = IndigoLogHandler(pluginDisplayName, logging.INFO)
        ifmt = logging.Formatter("%(message)s")
        self.indigo_log_handler.setFormatter(ifmt)
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.addHandler(self.indigo_log_handler)

        self.prefsUpdated = False
        self.logger.info(u"")
        self.logger.info(u"{0:=^130}".format(" Initializing New Plugin Session "))
        self.logger.info(u"{0:<30} {1}".format("Plugin name:", pluginDisplayName))
        self.logger.info(u"{0:<30} {1}".format("Plugin version:", pluginVersion))
        self.logger.info(u"{0:<30} {1}".format("Plugin ID:", pluginId))
        self.logger.info(u"{0:<30} {1}".format("Indigo version:", indigo.server.version))
        self.logger.info(u"{0:<30} {1}".format("Python version:", sys.version.replace('\n', '')))
        self.logger.info(u"{0:<30} {1}".format("Python Directory:", sys.prefix.replace('\n', '')))

        # Change to logging
        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        self.sendingCommand = False
        self.sentCommand = False
        self.que = Queue()
        self.connected = False
        self.deviceUpdate = False
        self.devicetobeUpdated =''

        self.latestEventsConnectionError = False

        self.ipaddress = self.pluginPrefs.get('ipaddress', '')
        self.port = self.pluginPrefs.get('port', 10000)
        self.ip150password = self.pluginPrefs.get('ip150password', 'paradox')
        self.pcpassword = self.pluginPrefs.get('pcpassword', 1234)


        self.command_just_run = False

        self.labelsdueupdate = True
        self.debug1 = self.pluginPrefs.get('debug1', False)
        self.debug2 = self.pluginPrefs.get('debug2', False)
        self.debug3 = self.pluginPrefs.get('debug3', False)
        self.debug4 = self.pluginPrefs.get('debug4',False)
        self.debug5 = self.pluginPrefs.get('debug5', False)
        self.latestevents = {}  ## dict devid and lastest event id
        # main device to be updated as needed
        self.paneldate = ""
        self.battery = float(0)
        self.batteryvdc = float(0)
        self.batterydc = float(0)
        self.area1Arm = "Disarmed"
        self.area2Arm = "Disarmed"
        self.producttype = ""
        self.firmware = ""
        self.panelID = ""
        self.zoneNames = {}

        self.triggers = {}

        for dev in indigo.devices.itervalues(filter="self"):
            if dev.deviceTypeId == "ActronQueMain":
                if dev.enabled:
                    localPropscopy = dev.pluginProps
                    localPropscopy['accessToken']= ""
                    localPropscopy['serialNo']= ""
                    self.logger.debug("Resetting device pluginProps Serial/Access Token:")
                    dev.replacePluginPropsOnServer(localPropscopy)

        self.logger.info(u"{0:=^130}".format(" End Initializing New Plugin  "))

    def __del__(self):

        self.debugLog(u"__del__ method called.")
        indigo.PluginBase.__del__(self)

    def closedPrefsConfigUi(self, valuesDict, userCancelled):

        self.debugLog(u"closedPrefsConfigUi() method called.")

        if userCancelled:
            self.debugLog(u"User prefs dialog cancelled.")

        if not userCancelled:
            self.logLevel = int(valuesDict.get("showDebugLevel", '5'))
            self.fileloglevel = int(valuesDict.get("showDebugFileLevel", '5'))
            self.ipaddress = valuesDict.get('ipaddress', '')
            # self.logger.error(str(valuesDict))
            self.port = valuesDict.get('port', False)
            self.ip150password = valuesDict.get('ip150password', 'paradox')
            self.pcpassword = valuesDict.get('superCharge', 1234)
            self.debugLog(u"User prefs saved.")
            self.debug1 = valuesDict.get('debug1', False)
            self.debug2 = valuesDict.get('debug2', False)
            self.debug3 = valuesDict.get('debug3', False)
            self.debug4 = valuesDict.get('debug4', False)
            self.debug5 = valuesDict.get('debug5', False)
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"logLevel = " + str(self.logLevel))
            self.logger.debug(u"User prefs saved.")

            self.indigo_log_handler.setLevel(self.logLevel)
            self.plugin_file_handler.setLevel(self.fileloglevel)

            self.logger.debug(u"Debugging on (Level: {0})".format(self.logLevel))

        return True

    # Start 'em up.

    # Shut 'em down.
    def deviceStopComm(self, dev):

        self.debugLog(u"deviceStopComm() method called.")
        #indigo.server.log(u"Stopping  device: " + dev.name)
        if dev.deviceTypeId == 'ActronQueMain':
            dev.updateStateOnServer('deviceIsOnline', value=False)

    ## return list of temperature options
    # remembering can only set to a temperature within range of main set point
    # these settings are...

    def returnHeatSetPointList(self, filter='', valuesDict=None, typeId="", targetId=0):
        endArray = []

        self.logger.debug(str(valuesDict))

        try:
            deviceid = valuesDict.get('deviceID',0)
            if deviceid != 0:
                zonedevice = indigo.devices[int(deviceid)]
                maxheatsp = float(zonedevice.states["MaxHeatSetpoint"])
                minheatsp = float(zonedevice.states["MinHeatSetpoint"])

                self.logger.debug("Using device "+str(deviceid)+ " and maxheatsp:"+str(maxheatsp)+" and minheatsp:"+str(minheatsp))

                setpoint = float(minheatsp)
                while (setpoint != maxheatsp):
                    endArray.append((setpoint, setpoint) )
                    setpoint = setpoint + 0.5
                ## and finally add max
                endArray.append((maxheatsp, maxheatsp))
        except:
            self.logger.exception("in zone temp list creation")


        return endArray

    def returnCoolSetPointList(self, filter='', valuesDict=None, typeId="", targetId=0):
        endArray = []

        self.logger.debug(str(valuesDict))

        try:
            deviceid = valuesDict.get('deviceID',0)
            if deviceid != 0:
                zonedevice = indigo.devices[int(deviceid)]
                maxheatsp = float(zonedevice.states["MaxCoolSetpoint"])
                minheatsp = float(zonedevice.states["MinCoolSetpoint"])

                self.logger.debug("Using device "+str(deviceid)+ " and maxcoolsp:"+str(maxheatsp)+" and mincoolsp:"+str(minheatsp))

                setpoint = float(minheatsp)
                while (setpoint != maxheatsp):
                    endArray.append((setpoint, setpoint) )
                    setpoint = setpoint + 0.5
                ## and finally add max
                endArray.append((maxheatsp, maxheatsp))
        except:
            self.logger.exception("in zone temp list creation")


        return endArray

    def runConcurrentThread(self):

        startingUp = True
        updateAccessToken = t.time() + 60*60*70
        getfullSystemStatus = t.time()  ## on startup always pull full system
        getlatestEventsTime = t.time() +5

          ## use dicts for this internally as will be fast moving and no need to report to Indigo
        ## Also move to pulling everything 10 seconds or so, if full-system-broadcast - send to system, if status - send to status

        try:
            # check once on statup
            # also check zones
            self.checkMainDevices()  #
            self.sleep(10)
            while True:
                for dev in indigo.devices.itervalues(filter="self"):
                    if dev.deviceTypeId == "ActronQueMain":
                        accessToken = dev.pluginProps['accessToken']
                        nimbus_accessToken = dev.pluginProps['nimbus_accessToken']
                        serialNo = dev.pluginProps['serialNo']
                        systemcheckonly = dev.pluginProps.get('systemcheckonly', False)
                        if accessToken == "" or accessToken == None:
                            self.logger.info("Failed to get Access Token.  ")
                            self.logger.info("May be expired token, or Actron API system issues.")
                            self.sleep(10)
                            updateAccessToken = t.time() + 2
                            continue
                        elif serialNo == None or serialNo == "":
                            self.logger.debug("Blank Serial No.  Rechecking for Serial")
                            self.checkMainDevices()
                            self.sleep(5)
                        if dev.states['deviceIsOnline']== False:
                            # if device offline need full systemcheck...
                            if t.time() > getfullSystemStatus:
                                self.getSystemStatus(dev, accessToken, serialNo)
                                getfullSystemStatus = t.time() + 300
                        if dev.states['deviceIsOnline']:
                            if systemcheckonly :  ## don't use status updates..
                                if t.time()> getfullSystemStatus:
                                    self.getSystemStatus(dev, accessToken, serialNo)
                                    getfullSystemStatus = t.time()+ 300
                            else:  ## disabled use latest Events..
                                if t.time() > getlatestEventsTime and self.latestEventsConnectionError==False and self.sendingCommand==False:
                                    # Move to Nimbus server token and events given Que has failed.
                                    #self.get_nimbuslatestEvents(dev, nimbus_accessToken, serialNo)
                                    #self.getlatestEvents(dev, accessToken,serialNo)
                                    getlatestEventsTime = t.time() + 30
                                    self.getSystemStatus(dev, accessToken, serialNo)
                                ## Add full system status check every 15 as getEvent incorrect.
                                if t.time() > getfullSystemStatus:
                                    self.getSystemStatus(dev, accessToken, serialNo)
                                    getfullSystemStatus = t.time() + 305

                self.sleep(2)
                if t.time() > updateAccessToken:
                    self.logger.info("Updating Access Token as Failed to connect or 24 hours has passed")
                    self.checkMainDevices()
                    updateAccessToken = t.time() + 60 * 60 * 24

                if self.latestEventsConnectionError:
                    ## obvious connection error
                    self.logger.debug(u"latestEventsConnectionError is True, resetting and trying again")
                    getlatestEventsTime = t.time() +60
                    self.latestEventsConnectionError = False  ## reset connection error here.
                    self.sendingCommand= False

                if self.sentCommand:
                    self.logger.debug(f"Command Successfully sent, running full System Update to update devices.")
                    getfullSystemStatus = t.time() - 300  ## eg in past so run now!
                    self.sentCommand = False

                startingUp = False

        except self.StopThread:
            self.debugLog(u'Restarting/or error. Stopping thread.')
            pass

        except Exception  as e:
            self.logger.exception("Main RunConcurrent error Caught:")
            self.sleep(5)

    def checkMainDevices(self):
        self.logger.debug("Check Main QUE Devices Run")
        for dev in indigo.devices.itervalues(filter="self"):
            if dev.deviceTypeId == "ActronQueMain":
                if dev.enabled:
                    ## check have access_token, bearer_token, not expired etc.
                    username = dev.pluginProps['username']
                    password = dev.pluginProps['password']
                    localPropscopy = dev.pluginProps
                    accessToken = self.getPairingToken(username,password)
                    if accessToken != "" and accessToken != None:
                        localPropscopy['accessToken']=accessToken
                        self.logger.debug("Updated device pluginProps with Access Token:")
                    else:
                        self.logger.info("Unable to get Access Token, check username, Password")
                        return

                    dev.replacePluginPropsOnServer(localPropscopy)
                    # add login to nimbus given que endopoint issues
                   # nimbus_accessToken = self.get_nimbusPairingToken(username,password)
                   # if nimbus_accessToken != "" and nimbus_accessToken != None:
                   #     localPropscopy['nimbus_accessToken'] = nimbus_accessToken
                   #     self.logger.debug("Updated device pluginProps with Access Token:")
                   # else:
                   #     self.logger.info("Unable to get Nimbus Access Token, check username, Password")
                   #     return
                   # dev.replacePluginPropsOnServer(localPropscopy)

                    serialNo = self.getACsystems(accessToken)
                    if serialNo != "":
                        localPropscopy['serialNo']=serialNo
                        self.logger.debug("Updated device pluginProps with Serial Number:")
                        self.logger.debug("Device :"+dev.name+" PluginProps:")
                        dev.updateStateOnServer('serialNumber', value=serialNo )
                        dev.replacePluginPropsOnServer(localPropscopy)
                    else:
                        self.logger.info("Unable to get Serial Number, check username, Password")
                        return
                    ## update system status

                    zonenames = self.getSystemStatus(dev, accessToken, serialNo)

                    if zonenames !="blank":
                        localPropscopy['zoneNames'] = zonenames
                        dev.replacePluginPropsOnServer(localPropscopy)

                    self.logger.debug("Device :" + dev.name + " PluginProps:")
                    self.logger.debug(str(dev.pluginProps))

    def getACsystems(self,accessToken):

        try:
            if accessToken == None or accessToken=="":
                self.logger.debug("Access token nil.  Aborting")
                return "blank"

            self.logger.debug( "Trying to use access Token %s" % accessToken )
            #self.logger.info("Connecting to %s" % address)
            url = 'https://que.actronair.com.au/api/v0/client/ac-systems'
            headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au','User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0',
                       'Authorization':'Bearer '+accessToken                       }
           # payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}

            r = requests.get(url, headers=headers, timeout=15, verify=False)
            if r.status_code == 200:
                self.logger.debug(str(r.text))
                jsonResponse = r.json()
                if '_embedded' in jsonResponse:
                    if 'ac-system' in jsonResponse['_embedded']:
                        if 'serial' in jsonResponse['_embedded']['ac-system'][0]:
                            self.logger.debug(jsonResponse['_embedded']['ac-system'][0])
                            serialNumber = jsonResponse['_embedded']['ac-system'][0]['serial']
                            self.logger.debug("Serial Number:"+str(serialNumber))
                            self.connected = True
                            return serialNumber
            else:
                self.logger.error(str(r.text))
                self.sleep(30)
                return "blank"

        except requests.ReadTimeout as e:
            self.logger.info("ReadTimeout connecting to Actron.  Retrying.")
            self.logger.debug("ReadTimeout connecting to Actron. Retrying."+str(e))
            return "blank"

        except Exception as e:
            self.logger.exception("Error getting AC systems : " + repr(e))
            self.logger.debug("Error connecting" + str(e.message))
            self.connected = False
            return "blank"
    ###########################
    # find a valid device name
    ###########################
    def getName(self, curName):
        if curName in indigo.devices:
            try:
                curNameParts = curName.split(" ")
                if len(curNameParts) == 1:
                    curNameParts.append("1")
                else:
                    versionNum = int(curNameParts[-1])
                    curNameParts[-1] = str(versionNum + 1)
            except:
                curNameParts[-1] = str(versionNum + 1)
            curName = " ".join(curNameParts)
            return self.getName(curName)
        return curName

    def generateZoneDevices(self, valuesDict, typeId, devId):

        self.logger.debug(u'Generate Zone Devices Called.')
        self.logger.debug(str(valuesDict))
        accessToken = valuesDict.get('accessToken', "")
        zoneNames = valuesDict.get('zoneNames', '')
        serialNo = valuesDict.get('serialNo', '')

        folderId = indigo.devices[devId].folderId

        if accessToken=="" or zoneNames == "" or serialNo == "":
            self.logger.info("Try again later, once Main device setup and connected")
        try:
            x = 0
            for zones in zoneNames.split(','):
                x= x +1
                if zones =="":
                    ## skip blank name
                    continue
                zoneDeviceExists = False
                ## check every queZone device for same name
                for dev in indigo.devices.itervalues('self.queZone'):
                    if dev.states["zoneName"] == zones:
                        ## device for this zone already exists
                        zoneDeviceExists = True

                if zoneDeviceExists:
                    ## continue
                    continue

                deviceName= self.getName('Que Zone:'+str(x)+":"+str(zones))

                zonedev = indigo.device.create(address=deviceName, deviceTypeId='queZone', name=deviceName,  protocol=indigo.kProtocol.Plugin, folder=folderId)
                zonedev.updateStateOnServer(key="zoneName", value=zones)
                zonedev.updateStateOnServer(key="zoneNumber", value=x)
                zonedev.updateStateOnServer(key="deviceMasterController", value=devId)

        except:
            self.logger.exception(u'Caught Exception creating Que Zone Devices')
            return

    def updateTemps(self, valuesDict, typeId, devId):

        self.logger.debug(u'updateTemps Called.')
        ## really just a dummy button to cause temp list to be updated...
        self.logger.debug(str(valuesDict))
        return

    def get_nimbuslatestEvents(self, device, accessToken, serialNo):
        try:
            if accessToken == None or accessToken == "":
                self.logger.debug("Access token nil.  Aborting")
                return
            if serialNo == None or serialNo == "":
                self.logger.debug("Blank Serial No. still Empty skipping getLatestEvents currently")
                return
            skippingparsing = False
            lasteventid = self.latestevents.get(device.id, "A")
            # if no last event or device is Offline pull all events.

            # will give KeyError if blank, use get to avoid, use A pulls all
            #  if self.debug4:
            #       self.logger.debug("Getting Latest Events for System Serial No %s" % serialNo)
            #       self.logger.debug(u"LastEventID: " + str(lasteventid))
            # self.logger.info("Connecting to %s" % address)
            # url = 'https://que.actronair.com.au/api/v0/client/ac-systems/events/latest?serial=' + str(serialNo)
            if lasteventid == "A":
                url = 'https://nimbus.actronair.com.au/api/v0/client/ac-systems/events/latest?serial=' + str(serialNo)
                # don't parse this info - just re-do the system state already received.
                # skip.
                skippingparsing = True
            else:
                url = 'https://nimbus.actronair.com.au/api/v0/client/ac-systems/events/newer?serial=' + str(
                    serialNo) + '&newerThanEventId=' + str(lasteventid)
            #     self.logger.debug(str(url))
            headers = {'Host': 'nimbus.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au',
                       'User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0',
                       'Authorization': 'Bearer ' + accessToken}
            # payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}
            r = requests.get(url, headers=headers, timeout=20, verify=False)
            if r.status_code != 200:
                self.logger.info("Error Message from get Latest Events")
                self.logger.debug(str(r.text))
                if 'Authorization has been denied' in r.text:
                    self.logger.info("Failed authentication for Events, likely expired, or multiple log ins.")
                    self.logger.info("Regenerating Token for access.")
                    self.sleep(3)
                    self.checkMainDevices()
                return
            # serialNumber = jsonResponse['_embedded']['ac-system'][0]['serial']
            # self.logger.debug(str(r.text))

            jsonResponse = json.loads(r.text, object_pairs_hook=OrderedDict)

            # jsonResponse = r.json(object_pairs_hook=OrderedDict)
            if "events" in jsonResponse:
                eventslist = jsonResponse['events']
                if len(eventslist) > 0:
                    self.latestevents[device.id] = eventslist[0]['id']
                    # self.logger.error(str(eventslist[0]))

            if skippingparsing:
                self.logger.info("First Run of Latest Events: Skipping updating once.")
                return
            timestamp = ""
            if self.debug4:
                self.logger.debug(f"Full Events:{self.safe_json_dumps(eventslist)}")
            for events in reversed(eventslist):
                if self.debug4:
                    self.logger.debug(f'event:\n{self.safe_json_dumps(events)}')
                if events['type'] == 'full-status-broadcast':
                    if self.debug4:
                        self.logger.debug(
                            "*** Full Status BroadCast Found  ***  Checking Whether this is recent or old..")
                    if self.is_event_timestamp_close(events['timestamp'], 15):
                        self.parseFullStatusBroadcast(device, serialNo, events)
                    else:
                        self.logger.debug("Full Status BroadCast Found - However old.  Ignored. ")
                elif events['type'] == "status-change-broadcast":
                    # if self.debug4:
                    # self.logger.debug("Status Change Broadcast")
                    if self.is_event_timestamp_close(events['timestamp'], 5):
                        self.parsestatusChangeBroadcast(device, serialNo, events['data'])
                    else:
                        self.logger.debug(f"Ignoring parsed Event as more than 15 minutes old.")
                # self.logger.debug(u'event id:'+events['id'])
                # timestamp = events['timestamp']
            # self.logger.error(str(timestamp))
            return
        except requests.exceptions.ReadTimeout as e:
            self.logger.debug("ReadTimeout with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.Timeout as e:
            self.logger.debug("Timeout with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.ConnectionError as e:
            self.logger.debug("ConnectionError with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.ConnectTimeout as e:
            self.logger.debug("Connect Timeout with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.HTTPError as e:
            self.logger.debug("HttpError with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.SSLError as e:
            self.logger.debug("SSL with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return

        except Exception as e:
            self.logger.exception("Error getting Latest Events from Actron API : " + repr(e))
            self.logger.debug("Error Latest Events from Actron API" + str(e.message))
            self.latestEventsConnectionError = True

    def getlatestEvents(self, device, accessToken, serialNo):
        try:
            if accessToken == None or accessToken == "":
                self.logger.debug("Access token nil.  Aborting")
                return
            if serialNo == None or serialNo == "":
                self.logger.debug("Blank Serial No. still Empty skipping getLatestEvents currently")
                return
            skippingparsing = False
            lasteventid = self.latestevents.get(device.id,"A")
                # if no last event or device is Offline pull all events.

            # will give KeyError if blank, use get to avoid, use A pulls all
            #  if self.debug4:
            #       self.logger.debug("Getting Latest Events for System Serial No %s" % serialNo)
            #       self.logger.debug(u"LastEventID: " + str(lasteventid))
            # self.logger.info("Connecting to %s" % address)
            # url = 'https://que.actronair.com.au/api/v0/client/ac-systems/events/latest?serial=' + str(serialNo)
            if lasteventid=="A":
                url = 'https://que.actronair.com.au/api/v0/client/ac-systems/events/latest?serial=' + str(serialNo)
                # don't parse this info - just re-do the system state already received.
                # skip.
                skippingparsing=True
            else:
                url = 'https://que.actronair.com.au/api/v0/client/ac-systems/events/newer?serial=' + str(serialNo)+ '&newerThanEventId='+str(lasteventid)
           #     self.logger.debug(str(url))
            headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au',
                       'User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0',
                       'Authorization': 'Bearer ' + accessToken}
            # payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}
            r = requests.get(url, headers=headers, timeout=20,verify=False)
            if r.status_code != 200:
                self.logger.info("Error Message from get Latest Events")
                self.logger.debug(str(r.text))
                if 'Authorization has been denied' in r.text:
                    self.logger.info("Failed authentication for Events, likely expired, or multiple log ins.")
                    self.logger.info("Regenerating Token for access.")
                    self.sleep(3)
                    self.checkMainDevices()
                return
            # serialNumber = jsonResponse['_embedded']['ac-system'][0]['serial']
            #self.logger.debug(str(r.text))

            jsonResponse = json.loads(r.text, object_pairs_hook=OrderedDict)

           # jsonResponse = r.json(object_pairs_hook=OrderedDict)
            if "events" in jsonResponse:
                eventslist = jsonResponse['events']
                if len(eventslist)>0:
                    self.latestevents[device.id]= eventslist[0]['id']
                    #self.logger.error(str(eventslist[0]))

            if skippingparsing:
                self.logger.info("First Run of Latest Events: Skipping updating once.")
                return
            timestamp = ""
            if self.debug4:
                self.logger.debug(f"Full Events:{self.safe_json_dumps(eventslist)}")
            for events in reversed(eventslist):
                if self.debug4:
                    self.logger.debug(f'event:\n{self.safe_json_dumps(events)}')
                if events['type']=='full-status-broadcast':
                    if self.debug4:
                        self.logger.debug("*** Full Status BroadCast Found  ***  Checking Whether this is recent or old..")
                    if self.is_event_timestamp_close(events['timestamp'], 15):
                        self.parseFullStatusBroadcast(device, serialNo, events)
                    else:
                        self.logger.debug("Full Status BroadCast Found - However old.  Ignored. ")
                elif events['type']=="status-change-broadcast":
                    #if self.debug4:
                        #self.logger.debug("Status Change Broadcast")
                    if self.is_event_timestamp_close(events['timestamp'], 5):
                        self.parsestatusChangeBroadcast(device,serialNo,events['data'])
                    else:
                        self.logger.debug(f"Ignoring parsed Event as more than 15 minutes old.")
                #self.logger.debug(u'event id:'+events['id'])
                #timestamp = events['timestamp']
           # self.logger.error(str(timestamp))
            return
        except requests.exceptions.ReadTimeout as e:
            self.logger.debug("ReadTimeout with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.Timeout as e:
            self.logger.debug("Timeout with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.ConnectionError as e:
            self.logger.debug("ConnectionError with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.ConnectTimeout as e:
            self.logger.debug("Connect Timeout with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.HTTPError as e:
            self.logger.debug("HttpError with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return
        except requests.exceptions.SSLError as e:
            self.logger.debug("SSL with get Latest Events from Actron API:" + str(e))
            self.latestEventsConnectionError = True
            return

        except Exception as e:
            self.logger.exception("Error getting Latest Events from Actron API : " + repr(e))
            self.logger.debug("Error Latest Events from Actron API" + str(e.message))
            self.latestEventsConnectionError = True

    def is_event_timestamp_close(self, event_timestamp: str, allowed_diff_minutes: float) -> bool:
        """
        Check if the event's broadcast timestamp is within allowed_diff_minutes of the current system time
        in System local time.
        :param event_timestamp: The ISO-formatted timestamp from the event.
        :param allowed_diff_minutes: Allowed time difference in minutes.
        :return: True if the event timestamp is within the allowed difference from current time, else False.
        """
        try:
            # Attempt to fix the timestamp if microseconds have more than 6 digits.
            ts_fixed = event_timestamp
            dot_index = event_timestamp.find('.')
            if dot_index != -1:
                # Determine the index where the timezone info starts.
                tz_index = event_timestamp.find('+', dot_index)
                if tz_index == -1:
                    tz_index = event_timestamp.find('-', dot_index)
                if tz_index == -1:
                    tz_index = len(event_timestamp)
                microseconds = event_timestamp[dot_index + 1:tz_index]
                if len(microseconds) > 6:
                    microseconds = microseconds[:6]
                    ts_fixed = event_timestamp[:dot_index + 1] + microseconds + event_timestamp[tz_index:]

           # Parse the (possibly corrected) timestamp into a datetime object.
            dt = datetime.fromisoformat(ts_fixed)
            # Convert the event timestamp to the system's local timezone.
            dt_local = dt.astimezone()
            # Get the current system time as a timezone-aware datetime.
            current_local = datetime.now().astimezone()
            # Log both the broadcast timestamp (converted to local) and the current system time.
            self.logger.debug(f"Broadcast timestamp (local): {dt_local}, Current system time: {current_local}")
            # Compute the absolute difference in minutes.
            diff_minutes = abs((current_local - dt_local).total_seconds() / 60.0)
            self.logger.debug(f"Difference in minutes: {diff_minutes}")
            # Return True if the time difference is within the allowed limit.
            return diff_minutes <= allowed_diff_minutes
        except Exception as e:
            self.logger.error("Error in is_event_timestamp_close: %s", e)
            return False
## JSON logging
    def safe_json_dumps(self, obj, fallback=str, **kwargs):
        """
        Convert an object to a JSON string using json.dumps.
        If conversion fails, log the error and return a fallback representation.

        :param obj: The object to convert.
        :param fallback: Fallback function (defaults to str) if conversion fails.
        :param kwargs: Additional arguments for json.dumps.
        :return: A JSON string or a fallback representation.
        """
        try:
            return json.dumps(obj, **kwargs)
        except Exception as e:
            self.logger.error("Error converting to JSON: %s", e)
            return fallback(obj)



    def parsestatusChangeBroadcast(self,device, serialNo,fullstatus):
       # if self.debug4:
        #    self.logger.debug('parsing status change broadcast')
        try:
            for events in fullstatus:
                eventactioned = False
                if self.debug4:
                    self.logger.debug(f"events:\n{events} result:\n{self.safe_json_dumps(fullstatus[events])}")
                results = fullstatus[events]

                if 'SystemStatus_Local.LastScreenTouch_UTC' in events:
                    if self.debug4:
                        self.logger.debug(u"Ignoring Last Screen Touch UTC update")
                    eventactioned = True
                ## Zone Info
                elif "@metadata" in events:
                    eventactioned = True
                elif 'RemoteZoneInfo' in events:  #zone info update
                    ## parse the Zone Number
                    zonenumber = int(events.split('[', 1)[1].split(']')[0])
                    #self.logger.error(u"ZoneNumber split to be:"+str(zonenumber))
                    for zones in indigo.devices.itervalues('self.queZone'):
                        # iter through all zones finding correct Zone.  Do it once here.  use Found zone everywhere down stream.
                        if int(zones.states["zoneNumber"]) - 1 == int(zonenumber):
                            foundzone = zones
                    if 'ZonePosition' in events:
                        if int(results) == 0:
                            zoneOpen = False
                            percentageOpen = 0
                        else:
                            zoneOpen = True
                            percentageOpen = int(results) * 5
                        if self.debug4:
                            self.logger.debug(u"Updating Zone:" + str(foundzone.states['zoneName']) +" with new Event:"+str(events)+u" and data:"+str(results))
                        foundzone.updateStateOnServer("zonePosition", int(results))
                        foundzone.updateStateOnServer("zonePercentageOpen", percentageOpen)
                        foundzone.updateStateOnServer("zoneisOpen", zoneOpen)
                        eventactioned = True
                    elif 'MinHeatSetpoint' in events:
                        if self.debug4:
                            self.logger.debug(u"Updating Zone:"  + str(foundzone.states['zoneName']) +" with new Event:" + str(events) + u" and data:" + str(results))
                        foundzone.updateStateOnServer("MinHeatSetpoint", float(results))
                        eventactioned = True
                    elif 'MinCoolSetpoint' in events:
                        if self.debug4:
                            self.logger.debug(u"Updating Zone:"  + str(foundzone.states['zoneName']) +" with new Event:" + str(events) + u" and data:" + str(results))
                        foundzone.updateStateOnServer("MinCoolSetpoint", float(results))
                        eventactioned = True
                    elif 'MaxHeatSetpoint' in events:
                        if self.debug4:
                            self.logger.debug(u"Updating Zone:"  + str(foundzone.states['zoneName']) +" with new Event:" + str(events) + u" and data:" + str(results) )
                        foundzone.updateStateOnServer("MaxHeatSetpoint", float(results))
                        eventactioned = True
                    elif 'MaxCoolSetpoint' in events:
                        if self.debug4:
                            self.logger.debug(u"Updating Zone:"  + str(foundzone.states['zoneName']) +" with new Event:" + str(events) + u" and data:" + str(results))
                        foundzone.updateStateOnServer("MaxCoolSetpoint", float(results))
                        eventactioned = True
                    elif 'CanOperate' in events:
                        if self.debug4:
                            self.logger.debug(u"Updating Zone:"  + str(foundzone.states['zoneName']) +" with new Event:" + str(events) + u" and data:" + str(results))
                        if str(results) == "True":
                            foundzone.updateStateOnServer("canOperate", True)
                        elif str(results) == "False":
                            foundzone.updateStateOnServer("canOperate", False)
                        eventactioned = True
                    elif 'TemperatureSetpoint_Cool_oC' in events:
                        if self.debug4:
                            self.logger.debug(u"Updating Zone:"  + str(foundzone.states['zoneName']) + " with new Event:" + str(events) + u" and data:" + str(results))
                        foundzone.updateStateOnServer("TempSetPointCool", float(results))
                        foundzone.updateStateOnServer("setpointCool", float(results))
                        eventactioned = True
                    elif 'TemperatureSetpoint_Heat_oC' in events:
                        if self.debug4:
                            self.logger.debug(u"Updating Zone:" + str(foundzone.states['zoneName']) +" with new Event:" + str(events) + u" and data:" + str(results))
                        foundzone.updateStateOnServer("TempSetPointHeat", float(results))
                        foundzone.updateStateOnServer("setpointHeat", float(results))
                        eventactioned = True
                    elif 'LiveTemp_oC' in events:
                        if self.debug4:
                            self.logger.debug( u"Updating Zone:" + str(foundzone.states['zoneName']) + u" with new Event:" + str( events) + u" and data:" + str(results))
                        foundzone.updateStateOnServer("temperatureInput1", float(results))
                        foundzone.updateStateOnServer("currentTemp", float(results))
                        eventactioned = True
                    elif 'LiveTempHysteresis_oC' in events:
                        if self.debug4:
                            self.logger.debug( u"Updating Zone:" + str(foundzone.states['zoneName']) + u" with new Event:" + str( events) + u" and data:" + str(results))
                        foundzone.updateStateOnServer("currentTempHystersis", float(results))
                        eventactioned = True
                    elif 'LiveHumidity_pc' in events:
                        if self.debug4:
                            self.logger.debug(
                                u"Updating Zone: Humidity" + str(foundzone.states['zoneName']) + u" with new Event:" + str(
                                    events) + u" and data:" + str(results))
                        foundzone.updateStateOnServer("HumidityInput1", round(float(results),3))
                        foundzone.updateStateOnServer("currentHumidity", round(float(results),3))
                        eventactioned = True
                ## System Data
                elif 'MasterInfo' in events:  ## system data
                    if 'LiveOutdoorTemp_oC' in events:
                        OutdoorUnitTemp = float(results)
                        OutdoorUnitTemp = round(OutdoorUnitTemp, 3)
                        if self.debug4:
                            self.logger.debug(u"Updating Master Device with new Event:" + str(  events) + u" and data:" + str(results))
                        device.updateStateOnServer("outdoorUnitTemp", OutdoorUnitTemp)
                        eventactioned = True
                    elif 'LiveTemp_oC' in events:
                        LiveTemp = float(results)
                        LiveTemp = round(LiveTemp, 3)
                        if self.debug4:
                            self.logger.debug(
                                u"Skipping this event, as Plugin reports average across all zones Master Device with new Event:" + str(events) + u" and data:" + str(
                                    results))
                        #device.updateStateOnServer("outdoorUnitTemp", LiveTemp)
                        eventactioned = True
                    elif 'LiveHumidity_pc' in events:
                        LiveHumidity = float(results)
                        LiveHumidity = round(LiveHumidity, 3)
                        if self.debug4:
                            self.logger.debug(
                                u"Updating Master Device with new Event:" + str(events) + u" and data:" + str(
                                    results))
                        device.updateStateOnServer("humidityInput1", LiveHumidity)
                        eventactioned = True
                    elif 'LiveTempHysteresis_oC' in events:
                        if self.debug4:
                            self.logger.debug(u"Ignored Temp Hystersis Zone report")
                        eventactioned = True
                    elif 'CloudConnected' in events:
                        if self.debug4:
                            self.logger.debug(u"Ignored reported Cloud Connected event")
                        eventactioned = True
                    elif 'CloudReachable' in events:
                        if self.debug4:
                            self.logger.debug(u"Ignored reported Cloud Reachable event")
                        eventactioned = True
                elif 'LiveAircon' in events:  ## system data as well
                    if 'CompressorCapacity' in events:
                        compCapacity = float(results)
                        if self.debug4:
                            self.logger.debug(  u"Updating Master Device with new Event:" + str(events) + u" and data:" + str(results))
                        device.updateStateOnServer("compressorCapacity", compCapacity)
                        eventactioned = True
                    elif 'CompressorMode' in events:
                        mode = str(results)
                        if self.debug4:
                            self.logger.debug(  u"Updating Master Device with new Event:" + str(events) + u" and data:" + str(results))
                        if mode == "AUTO":
                            MainStatus = indigo.kHvacMode.HeatCool
                        elif mode == "HEAT":
                            MainStatus = indigo.kHvacMode.Heat
                        elif mode == "COOL":
                            MainStatus = indigo.kHvacMode.Cool
                        else:
                            MainStatus = indigo.kHvacMode.HeatCool
                        device.updateStateOnServer("hvacOperationMode", MainStatus)
                        eventactioned = True
                    elif "LiveAircon.AmRunningFan" in events:
                        device.updateStateOnServer("fanOn", results)
                        eventactioned= True
                elif 'UserAirconSettings' in events: ## system data
                    if 'QuietMode' in events:
                        if self.debug4:
                            self.logger.debug(  u"Updating Master Device with new Event:" + str(events) + u" and data:" + str(results))
                        if str(results) == "True":
                            device.updateStateOnServer("quietMode", True)
                        elif str(results) == "False":
                            device.updateStateOnServer("quietMode", False)
                        eventactioned = True
                    elif 'UserAirconSettings.Mode' in events:  ## use whole thing as Mode in few things
                        mode = str(results)
                        if self.debug4:
                            self.logger.debug(  u"Updating Master Device with new Event:" + str(events) + u" and data:" + str( results))
                        if mode == "AUTO":
                            MainStatus = indigo.kHvacMode.HeatCool
                        elif mode == "HEAT":
                            MainStatus = indigo.kHvacMode.Heat
                        elif mode == "COOL":
                            MainStatus = indigo.kHvacMode.Cool
                        else:
                            MainStatus = indigo.kHvacMode.HeatCool
                        device.updateStateOnServer("hvacOperationMode", MainStatus)
                        eventactioned = True
                    elif "UserAirconSettings.isOn" in events:
                        status = results
                        if results:
                            self.logger.debug(f"AirConditioning is running")
                        else:
                            self.logger.debug(f"AirConditioning is Off")
                        eventactioned = True

                    elif 'TemperatureSetpoint_Cool_oC' in events:
                        if self.debug4:
                            self.logger.debug(  u"Updating Master Device with new Event:" + str(events) + u" and data:" + str(results))
                        setpointTemp = float(results)
                        device.updateStateOnServer("setpointCool", setpointTemp)
                        eventactioned = True
                    elif 'TemperatureSetpoint_Heat_oC' in events:
                        if self.debug4:
                            self.logger.debug(  u"Updating Master Device with new Event:" + str(events) + u" and data:" + str(results))
                        setpointTemp = float(results)
                        device.updateStateOnServer("setpointHeat", setpointTemp)
                        eventactioned = True
                    elif 'FanMode' in events:
                        if self.debug4:
                            self.logger.debug(  u"Updating Master Device with new Event:" + str(events) + u" and data:" + str(results))
                        fanMode = str(results)
                        device.updateStateOnServer("fanSpeed", fanMode)
                        eventactioned = True
                    elif 'EnabledZones' in events:
                        zonenumber = int(events.split('[', 1)[1].split(']')[0])
                        for zones in indigo.devices.itervalues('self.queZone'):
                            if int(zones.states["zoneNumber"]) - 1 == int(zonenumber):
                                if self.debug4:
                                    self.logger.debug(u"Updating Zone:" + str(zones.states['zoneName']) + " with new Event:" + str(events) + u" and data:" + str(results))
                                if str(results) == "True":
                                    zones.updateStateOnServer("zoneisEnabled", True)
                                    currentMode = device.states['hvacOperationMode']
                                    zones.updateStateOnServer('hvacOperationMode', currentMode)
                                    eventactioned = True
                                elif str(results) == "False":
                                    zones.updateStateOnServer("zoneisEnabled", False)
                                    zones.updateStateOnServer('hvacOperationMode', indigo.kHvacMode.Off)
                                    eventactioned = True

                if eventactioned == False:
                    if self.debug5:  ## this is unknown events
                        self.logger.info(f"Event but not recognised: {events} & fullstatus: {fullstatus}")

        except:
            self.logger.debug(u"Exception in parseStateChange Broadcast")
            self.logger.exception(u'this one:')


## currently the full status broadcast information from Actron is completely wrong
    # temp/zones etc.. wrong
    # not sure what is what
    # obviously don't use for now, instead get full system status
    def parseFullStatusBroadcast(self, device, serialNo, fullstatus):
        if self.debug4:
            self.logger.debug("Parsing Full Status Broadcast")

            #self.logger.info(str(fullstatus))

        jsonResponse =fullstatus
        listzonetemps = []
        listzonehumidity = []
        listzonesopen = [False, False, False, False, False, False, False, False]
        indoorModel = ""
        alertCF = False
        alertDRED = False
        alertDefrosting = False
        fanPWM = float(0)
        fanRPM = float(0)
        amRunningFan = False
        IndoorUnitTemp = float(0)
        OutdoorUnitTemp = float(0)
        CompPower = float(0)
        CompRunningPWM = float(0)
        CompSpeed = float(0)
        outdoorFanSpeed = float(0)
        main_humidity = float(0)
        compCapacity = float(0)
        CompressorMode = ""
        FanMode = ""
        quietMode = ""
        WorkingMode = ""
        errorCode = "None"
        SystemSetpoint_Cool = float(0)
        SystemSetpoint_Heat = float(0)
        MainStatus = indigo.kHvacMode.Off
        zonenames = ""
        lastContact =""

        if 'data' in jsonResponse:
            if "<" + serialNo.upper() + ">" in jsonResponse['data']:
                self.logger.debug(str(jsonResponse['data']["<" + serialNo.upper() + ">"]))
            if 'isOnline' in jsonResponse['data']:  ## check system online
                self.logger.debug(u'isOnline Returned:' + str(jsonResponse['data']['isOnline']))
                if str(jsonResponse['data']['isOnline'])=='False':
                    self.logger.info(u'System is reporting that it is Offline.')
                    #self.logger.info(u'Last Contact '+str(jsonResponse['data']['timeSinceLastContact'])+u' hours/minutes/seconds ago')
                    device.updateStateOnServer('deviceIsOnline', value=False)
                    if 'timeSinceLastContact' in jsonResponse['data']:
                        self.logger.info(u'Last Contact ' + str(jsonResponse['data']['timeSinceLastContact']) + u' days/hours/minutes/seconds ago')
                        lastContact = str(jsonResponse['data']['timeSinceLastContact'])
                        device.updateStateOnServer('lastContact',lastContact)
                    return
                else:
                    device.updateStateOnServer('deviceIsOnline', value=True)
                    if 'timeSinceLastContact' in jsonResponse['data']:
                        self.logger.info(u'Last Contact ' + str(jsonResponse['data']['timeSinceLastContact']) + u' hours/minutes/seconds ago')
                        lastContact = str(jsonResponse['data']['timeSinceLastContact'])
                        device.updateStateOnServer('lastContact',lastContact)

            if "AirconSystem" in jsonResponse['data']:
                if 'IndoorUnit' in jsonResponse['data']['AirconSystem']:
                    if "NV_DeviceID" in jsonResponse['data']['AirconSystem']['IndoorUnit']:
                        indoorModel = jsonResponse['data']['AirconSystem']['IndoorUnit']["NV_DeviceID"]
            if 'Alerts' in jsonResponse['data']:
                alertCF = jsonResponse['data']['Alerts']['CleanFilter']
                alertDRED = jsonResponse['data']['Alerts']['DRED']
                alertDefrosting = jsonResponse['data']['Alerts']['Defrosting']
            if 'LiveAircon' in jsonResponse['data']:
                if 'ErrCode' in jsonResponse['data']['LiveAircon']:
                    errorCode = "Error Code:" + str(jsonResponse['data']['LiveAircon']['ErrCode'])
                if 'AmRunningFan' in jsonResponse['data']['LiveAircon']:
                    amRunningFan = jsonResponse['data']['LiveAircon']['AmRunningFan']
                if 'FanPWM' in jsonResponse['data']['LiveAircon']:
                    fanPWM = jsonResponse['data']['LiveAircon']['FanPWM']
                if 'CompressorCapacity' in jsonResponse['data']['LiveAircon']:
                    compCapacity = jsonResponse['data']['LiveAircon']['CompressorCapacity']
                if 'FanRPM' in jsonResponse['data']['LiveAircon']:
                    fanRPM = jsonResponse['data']['LiveAircon']['FanRPM']
                if 'IndoorUnitTemp' in jsonResponse['data']['LiveAircon']:
                    IndoorUnitTemp = float(jsonResponse['data']['LiveAircon']['IndoorUnitTemp'])
                    IndoorUnitTemp = round(IndoorUnitTemp, 3)
                if 'OutdoorUnit' in jsonResponse['data']['LiveAircon']:
                    if 'AmbTemp' in jsonResponse['data']['LiveAircon']['OutdoorUnit']:
                        OutdoorUnitTemp = jsonResponse['data']['LiveAircon']['OutdoorUnit']['AmbTemp']
                        OutdoorUnitTemp = round(OutdoorUnitTemp, 3)
                    if 'CompPower' in jsonResponse['data']['LiveAircon']['OutdoorUnit']:
                        CompPower = jsonResponse['data']['LiveAircon']['OutdoorUnit']['CompPower']
                    if 'CompRunningPWM' in jsonResponse['data']['LiveAircon']['OutdoorUnit']:
                        CompRunningPWM = jsonResponse['data']['LiveAircon']['OutdoorUnit']['CompRunningPWM']
                    if 'CompSpeed' in jsonResponse['data']['LiveAircon']['OutdoorUnit']:
                        CompSpeed = jsonResponse['data']['LiveAircon']['OutdoorUnit']['CompSpeed']
                        CompSpeed = round(CompSpeed, 3)
                    if 'FanSpeed' in jsonResponse['data']['LiveAircon']['OutdoorUnit']:
                        outdoorFanSpeed = jsonResponse['data']['LiveAircon']['OutdoorUnit']['FanSpeed']
                if 'CompressorMode' in jsonResponse['data']['LiveAircon']:
                    CompressorMode = jsonResponse['data']['LiveAircon']['CompressorMode']
                self.logger.debug("Live Air Con Summary:----")
                self.logger.debug(jsonResponse['data']['LiveAircon'])
            if 'UserAirconSettings' in jsonResponse['data']:
                if 'FanMode' in jsonResponse['data']['UserAirconSettings']:
                    FanMode = jsonResponse['data']['UserAirconSettings']['FanMode']
                if 'Mode' in jsonResponse['data']['UserAirconSettings']:
                    WorkingMode = jsonResponse['data']['UserAirconSettings']['Mode']
                    userACmode = jsonResponse['data']['UserAirconSettings']['Mode']
                    self.logger.debug(u"userACMode:" + str(userACmode))
                if 'QuietMode' in jsonResponse['data']['UserAirconSettings']:
                    quietMode = jsonResponse['data']['UserAirconSettings']['QuietMode']
                if 'TemperatureSetpoint_Cool_oC' in jsonResponse['data']['UserAirconSettings']:
                    SystemSetpoint_Cool = jsonResponse['data']['UserAirconSettings'][
                        'TemperatureSetpoint_Cool_oC']
                if 'TemperatureSetpoint_Heat_oC' in jsonResponse['data']['UserAirconSettings']:
                    SystemSetpoint_Heat = jsonResponse['data']['UserAirconSettings'][
                        'TemperatureSetpoint_Heat_oC']
                if 'EnabledZones' in jsonResponse['data']['UserAirconSettings']:
                    # self.logger.error(str(jsonResponse['data']['UserAirconSettings']['EnabledZones']))
                    listzonesopen = jsonResponse['data']['UserAirconSettings']['EnabledZones']
                    self.logger.debug(u"List of Zone Status:" + str(listzonesopen))
                if 'isOn' in jsonResponse['data']['UserAirconSettings']:
                    isACturnedOn = jsonResponse['data']['UserAirconSettings']['isOn']
                    self.logger.debug(u"acTurnedOn:" + str(isACturnedOn))
            # 0.1.3 Add MasterInfo Data
            if 'MasterInfo' in jsonResponse['data']:
                if 'RemoteHumidity_pc' in jsonResponse['data']['MasterInfo']:
                    if serialNo.upper() in jsonResponse['data']['MasterInfo']['RemoteHumidity_pc']:
                        main_humidity = jsonResponse['data']['MasterInfo']['RemoteHumidity_pc'][
                            serialNo.upper()]

            try:
                if bool(isACturnedOn):
                    ## AC is on, may or may not be running
                    self.logger.debug("ACturnedOn True:")
                    # userACmode OFF,HEAT,COOL,AUTO - however OFF just means not running now
                    if userACmode == "AUTO":
                        MainStatus = indigo.kHvacMode.HeatCool
                    elif userACmode == "HEAT":
                        MainStatus = indigo.kHvacMode.Heat
                    elif userACmode == "COOL":
                        MainStatus = indigo.kHvacMode.Cool
                    # if CompressorMode == "HEAT":
                    #     MainStatus = indigo.kHvacMode.Heat
                    # elif CompressorMode =="COOL" :
                    #    MainStatus = indigo.kHvacMode.Cool
                    else:
                        MainStatus = indigo.kHvacMode.HeatCool
                else:
                    MainStatus = indigo.kHvacMode.Off
            except UnboundLocalError:
                self.logger.debug("isACturnedOn doesn't exit... skipping On/Off/Mode update.")

            if 'RemoteZoneInfo' in jsonResponse['data']:
                for x in range(0, 8):
                    ## go through all zones
                    self.logger.debug("Zone Number:" + str(x))
                    self.logger.debug(jsonResponse['data']['RemoteZoneInfo'][x])
                    if 'NV_Title' in jsonResponse['data']['RemoteZoneInfo'][x]:
                        zonenames = zonenames + jsonResponse['data']['RemoteZoneInfo'][x]['NV_Title'] + ","
                    self.logger.debug(str(zonenames))

                    for dev in indigo.devices.itervalues('self.queZone'):
                        # go through all devices, and compare to 8 zones returned.
                        if int(dev.states["deviceMasterController"]) != int(device.id):
                            self.logger.debug("This Device has a new/different master Controller skipping")
                            continue  ## skip, next zone device

                        if int(dev.states["zoneNumber"]) - 1 == int(x):
                            # if dev.states["zoneName"] == jsonResponse['data']['RemoteZoneInfo'][x]['NV_Title']:
                            canoperate = False
                            livehumidity = float(0)
                            liveTemphys = float(0)
                            livetemp = float(0)
                            tempsetpointcool = float(0)
                            tempsetpointheat = float(0)
                            ZonePosition = int(0)
                            sensorbattery = int(0)

                            maxcoolsp = int(0)
                            maxheatsp = int(0)
                            mincoolsp = int(0)
                            minheatsp = int(0)

                            sensorid = ""
                            ZoneStatus = indigo.kHvacMode.Off  ## Cool, HeatCool, Heat, Off
                            zoneOpen = False
                            if 'MaxCoolSetpoint' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                maxcoolsp = jsonResponse['data']['RemoteZoneInfo'][x]['MaxCoolSetpoint']
                            if 'MaxHeatSetpoint' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                maxheatsp = jsonResponse['data']['RemoteZoneInfo'][x]['MaxHeatSetpoint']
                            if 'MinCoolSetpoint' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                mincoolsp = jsonResponse['data']['RemoteZoneInfo'][x]['MinCoolSetpoint']
                            if 'MinHeatSetpoint' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                minheatsp = jsonResponse['data']['RemoteZoneInfo'][x]['MinHeatSetpoint']
                            if 'CanOperate' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                canoperate = jsonResponse['data']['RemoteZoneInfo'][x]['CanOperate']
                            if 'LiveHumidity_pc' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                 livehumidity = jsonResponse['data']['RemoteZoneInfo'][x]['LiveHumidity_pc']
                            if 'LiveTemp_oC' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                livetemp = jsonResponse['data']['RemoteZoneInfo'][x]['LiveTemp_oC']
                            if 'LiveTempHysteresis_oC' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                liveTemphys = jsonResponse['data']['RemoteZoneInfo'][x][
                                    'LiveTempHysteresis_oC']
                            if 'TemperatureSetpoint_Cool_oC' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                tempsetpointcool = jsonResponse['data']['RemoteZoneInfo'][x][
                                    'TemperatureSetpoint_Cool_oC']
                            if 'TemperatureSetpoint_Heat_oC' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                tempsetpointheat = jsonResponse['data']['RemoteZoneInfo'][x][
                                    'TemperatureSetpoint_Heat_oC']
                            if 'Sensors' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                # self.logger.error(jsonResponse['data']['RemoteZoneInfo'][x]['Sensors'])
                                for key, value in jsonResponse['data']['RemoteZoneInfo'][x][
                                    'Sensors'].items():
                                    sensorid = key
                                if 'Battery_pc' in jsonResponse['data']['RemoteZoneInfo'][x]['Sensors'][key]:
                                    sensorbattery = jsonResponse['data']['RemoteZoneInfo'][x]['Sensors'][key][
                                        'Battery_pc']
                            # correct - as when zoneposition is 0 the zone is turned off, but! zone may in need be enabled
                            # so not corrrect
                            # saver to user the enabled zone to set Mode.off and report Zoneposition for use
                            if 'ZonePosition' in jsonResponse['data']['RemoteZoneInfo'][x]:
                                ZonePosition = jsonResponse['data']['RemoteZoneInfo'][x]['ZonePosition']

                            if listzonesopen[x] == True:
                                if bool(isACturnedOn):  ## AC Turned On may not be running
                                    ZoneStatus = MainStatus
                                #             if CompressorMode=="HEAT":
                                #                 ZoneStatus = indigo.kHvacMode.Heat
                                #             elif CompressorMode == "COOL":
                                #                 ZoneStatus = indigo.kHvacMode.Cool
                                #             else:
                                #                 ZoneStatus = indigo.kHvacMode.HeatCool  ## not running so don'tknow
                                else:
                                    ZoneStatus = indigo.kHvacMode.Off
                            else:
                                ZoneStatus = indigo.kHvacMode.Off

                            if int(ZonePosition) == 0:
                                zoneOpen = False
                                percentageOpen = 0
                            else:
                                zoneOpen = True
                                percentageOpen = int(ZonePosition) * 5

                            listzonetemps.append(livetemp)
                            # if livehumidity > 0:
                            #    listzonehumidity.append(livehumidity)

                            zoneStatelist = [
                                {'key': 'canOperate', 'value': canoperate},
                                {'key': 'currentTemp', 'value': livetemp},
                                {'key': 'temperatureInput1', 'value': livetemp},
                                {'key': 'humidityInput1', 'value': livehumidity},
                                {'key': 'currentHumidity', 'value': livehumidity},
                                {'key': 'currentTempHystersis', 'value': liveTemphys},
                                {'key': 'zonePercentageOpen', 'value': percentageOpen},
                                {'key': 'sensorBattery', 'value': sensorbattery},
                                {'key': 'sensorId', 'value': sensorid},
                                {'key': 'zoneisEnabled', 'value': listzonesopen[x]},
                                {'key': 'zoneisOpen', 'value': zoneOpen},
                                {'key': 'hvacOperationMode', 'value': ZoneStatus},
                                {'key': 'TempSetPointCool', 'value': tempsetpointcool},
                                {'key': 'TempSetPointHeat', 'value': tempsetpointheat},
                                {'key': 'zonePosition', 'value': ZonePosition},
                                {'key': 'MinHeatSetpoint', 'value': minheatsp},
                                {'key': 'MinCoolSetpoint', 'value': mincoolsp},
                                {'key': 'MaxHeatSetpoint', 'value': maxheatsp},
                                {'key': 'MaxCoolSetpoint', 'value': maxcoolsp},
                                {'key': 'deviceMasterController', 'value': device.id},
                                {'key': 'setpointHeat', 'value': tempsetpointheat},
                                {'key': 'setpointCool', 'value': tempsetpointcool}
                                #    {'key': 'setpointHeat', 'value': tempsetpointheat}
                            ]
                            dev.updateStatesOnServer(zoneStatelist)

        averageTemp = 0
        averageHum = 0
        tempInputsAll = []
        humdInputAll = []
        if len(listzonetemps) > 1:
            tempInputsAll = str(','.join(map(str, listzonetemps)))
            averageTemp = reduce(lambda a, b: a + b, listzonetemps) / len(listzonetemps)
        # if len(listzonehumidity) >1:
        #     humdInputsAll = str(','.join(map(str, listzonehumidity)))
        #      averageHum = reduce(lambda a, b: a + b, listzonehumidity) / len(listzonehumidity)

        self.logger.debug(str(tempInputsAll))
        stateList = [
            {'key': 'indoorModel', 'value': indoorModel},
            {'key': 'setpointHeat', 'value': SystemSetpoint_Heat},
            {'key': 'setpointCool', 'value': SystemSetpoint_Cool},
            {'key': 'alertCleanFilter', 'value': alertCF},
            {'key': 'alertDRED', 'value': alertDRED},
            {'key': 'alertDefrosting', 'value': alertDefrosting},
            {'key': 'indoorFanRPM', 'value': fanRPM},
            {'key': 'indoorFanPWM', 'value': fanPWM},
            {'key': 'fanOn', 'value': amRunningFan},
            {'key': 'indoorUnitTemp', 'value': IndoorUnitTemp},
            {'key': 'outdoorUnitTemp', 'value': OutdoorUnitTemp},
            {'key': 'outdoorUnitPower', 'value': CompPower},
            {'key': 'outdoorUnitPWM', 'value': CompRunningPWM},
            {'key': 'outdoorUnitCompSpeed', 'value': CompSpeed},
            {'key': 'compressorCapacity', 'value': compCapacity},
            {'key': 'outdoorUnitCompMode', 'value': CompressorMode},
            {'key': 'hvacOperationMode', 'value': MainStatus},
            {'key': 'temperatureInput1', 'value': averageTemp},
            {'key': 'humidityInput1', 'value': main_humidity},
            {'key': 'quietMode', 'value': quietMode},
            {'key': 'fanSpeed', 'value': FanMode},
            {'key': 'errorCode', 'value': errorCode},
            {'key': 'outdoorUnitFanSpeed', 'value': outdoorFanSpeed},
        ]

        device.updateStatesOnServer(stateList)
        return zonenames

    def getSystemStatus(self, device, accessToken, serialNo):

        try:
            if accessToken == None or accessToken=="":
                self.logger.debug("Access token nil.  Aborting")
                return "blank"
            if serialNo == None or serialNo=="":
                self.logger.debug("Blank Serial No. still  Skipping getSystemStatus for now")
                return "blank"
            self.logger.debug("Getting System Status for System Serial No %s" % serialNo)
            # self.logger.info("Connecting to %s" % address)
            url = 'https://que.actronair.com.au/api/v0/client/ac-systems/status/latest?serial='+str(serialNo)
            headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au',
                       'User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0',
                       'Authorization': 'Bearer ' + accessToken}
            # payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}
            r = requests.get(url, headers=headers, timeout=15, verify=False)
            if r.status_code != 200:
                self.logger.info("Error Message from get System Status")
                self.logger.debug(str(r.text))
                self.sleep(5)
                self.checkMainDevices()
                return "blank"
# serialNumber = jsonResponse['_embedded']['ac-system'][0]['serial']
            self.logger.debug(str(r.text))

            jsonResponse = r.json()
            listzonetemps = []
            listzonehumidity = []
            listzonesopen = [False,False,False,False,False,False,False,False]
            indoorModel = ""
            alertCF = False
            alertDRED = False
            alertDefrosting = False
            fanPWM = float(0)
            fanRPM = float(0)
            IndoorUnitTemp = float(0)
            OutdoorUnitTemp = float(0)
            CompPower = float(0)
            CompRunningPWM= float(0)
            CompSpeed = float(0)
            outdoorFanSpeed = float(0)
            main_humidity = float(0)
            compCapacity = float(0)
            CompressorMode =""
            FanMode = ""
            quietMode = ""
            WorkingMode = ""
            SystemSetpoint_Cool = float(0)
            SystemSetpoint_Heat = float(0)
            MainStatus = indigo.kHvacMode.Off
            zonenames = ""

            if 'isOnline' in jsonResponse:  ## check system online
                self.logger.debug(str(jsonResponse['isOnline']))
                if str(jsonResponse['isOnline'])=='False':
                    self.logger.info(u'System is reporting that it is Offline.')
                    device.updateStateOnServer('deviceIsOnline', value=False)
                    if 'timeSinceLastContact' in jsonResponse:
                        self.logger.info(u'Last Contact ' + str(jsonResponse['timeSinceLastContact']) + u' hours/minutes/seconds ago')
                        lastContact = str(jsonResponse['timeSinceLastContact'])
                        device.updateStateOnServer('lastContact', lastContact)
                    return "blank"
                else:  #online true
                    device.updateStateOnServer('deviceIsOnline', value=True)
                    if 'timeSinceLastContact' in jsonResponse:
                        lastContact = str(jsonResponse['timeSinceLastContact'])
                        device.updateStateOnServer('lastContact', lastContact)

            if 'lastKnownState' in jsonResponse:
                if "<"+serialNo.upper()+">" in jsonResponse['lastKnownState']:
                    self.logger.debug(str(jsonResponse['lastKnownState']["<"+serialNo.upper()+">"]))
                if "AirconSystem" in jsonResponse['lastKnownState']:
                    if 'IndoorUnit' in jsonResponse['lastKnownState']['AirconSystem']:
                        if "NV_DeviceID" in jsonResponse['lastKnownState']['AirconSystem']["IndoorUnit"]:
                            indoorModel = jsonResponse['lastKnownState']['AirconSystem']['IndoorUnit']["NV_DeviceID"]
                if 'Alerts' in jsonResponse['lastKnownState']:
                    alertCF = jsonResponse['lastKnownState']['Alerts']['CleanFilter']
                    alertDRED = jsonResponse['lastKnownState']['Alerts']['DRED']
                    alertDefrosting = jsonResponse['lastKnownState']['Alerts']['Defrosting']
                if 'LiveAircon' in jsonResponse['lastKnownState']:
                    if 'CompressorCapacity' in jsonResponse['lastKnownState']['LiveAircon']:
                        compCapacity = jsonResponse['lastKnownState']['LiveAircon']['CompressorCapacity']
                    if 'FanPWM' in jsonResponse['lastKnownState']['LiveAircon']:
                        fanPWM = jsonResponse['lastKnownState']['LiveAircon']['FanPWM']
                    if 'FanRPM' in jsonResponse['lastKnownState']['LiveAircon']:
                        fanRPM = jsonResponse['lastKnownState']['LiveAircon']['FanRPM']
                    if 'IndoorUnitTemp' in jsonResponse['lastKnownState']['LiveAircon']:
                        IndoorUnitTemp = float(jsonResponse['lastKnownState']['LiveAircon']['IndoorUnitTemp'])
                        IndoorUnitTemp = round(IndoorUnitTemp,3)
                    if 'OutdoorUnit' in jsonResponse['lastKnownState']['LiveAircon']:
                        if 'AmbTemp' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            OutdoorUnitTemp = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['AmbTemp']
                            OutdoorUnitTemp = round(OutdoorUnitTemp,3)
                        if 'CompPower' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            CompPower = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['CompPower']
                        if 'CompRunningPWM' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            CompRunningPWM = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['CompRunningPWM']
                        if 'CompSpeed' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            CompSpeed = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['CompSpeed']
                            CompSpeed = round(CompSpeed,3)
                        if 'FanSpeed' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            outdoorFanSpeed = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['FanSpeed']
                    if 'CompressorMode' in jsonResponse['lastKnownState']['LiveAircon']:
                        CompressorMode = jsonResponse['lastKnownState']['LiveAircon']['CompressorMode']
                    self.logger.debug("Live Air Con Summary:----")
                    self.logger.debug(jsonResponse['lastKnownState']['LiveAircon'])
                if 'UserAirconSettings' in jsonResponse['lastKnownState']:
                    if 'FanMode' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        FanMode = jsonResponse['lastKnownState']['UserAirconSettings']['FanMode']
                    if 'Mode' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        WorkingMode = jsonResponse['lastKnownState']['UserAirconSettings']['Mode']
                        userACmode = jsonResponse['lastKnownState']['UserAirconSettings']['Mode']
                        self.logger.debug(u"userACMode:" + str(userACmode))
                    if 'QuietMode' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        quietMode = jsonResponse['lastKnownState']['UserAirconSettings']['QuietMode']
                    if 'TemperatureSetpoint_Cool_oC' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        SystemSetpoint_Cool = jsonResponse['lastKnownState']['UserAirconSettings']['TemperatureSetpoint_Cool_oC']
                    if 'TemperatureSetpoint_Heat_oC' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        SystemSetpoint_Heat = jsonResponse['lastKnownState']['UserAirconSettings']['TemperatureSetpoint_Heat_oC']
                    if 'EnabledZones' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        #self.logger.error(str(jsonResponse['lastKnownState']['UserAirconSettings']['EnabledZones']))
                        listzonesopen = jsonResponse['lastKnownState']['UserAirconSettings']['EnabledZones']
                        self.logger.debug(u"List of Zone Status:"+str(listzonesopen))
                    if 'isOn' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        isACturnedOn = jsonResponse['lastKnownState']['UserAirconSettings']['isOn']
                        self.logger.debug(u"acTurnedOn:" + str(isACturnedOn))
   #0.1.3 Add MasterInfo Data
                if 'MasterInfo' in jsonResponse['lastKnownState']:
                    if 'RemoteHumidity_pc' in jsonResponse['lastKnownState']['MasterInfo']:
                        if serialNo.upper() in jsonResponse['lastKnownState']['MasterInfo']['RemoteHumidity_pc']:
                            main_humidity = jsonResponse['lastKnownState']['MasterInfo']['RemoteHumidity_pc'][serialNo.upper()]

                try:
                    if bool(isACturnedOn):
                        ## AC is on, may or may not be running
                        self.logger.debug("ACturnedOn True:")
                        # userACmode OFF,HEAT,COOL,AUTO - however OFF just means not running now
                        if userACmode == "AUTO":
                            MainStatus = indigo.kHvacMode.HeatCool
                        elif userACmode == "HEAT":
                            MainStatus = indigo.kHvacMode.Heat
                        elif userACmode == "COOL":
                            MainStatus = indigo.kHvacMode.Cool
                        # if CompressorMode == "HEAT":
                        #     MainStatus = indigo.kHvacMode.Heat
                        # elif CompressorMode =="COOL" :
                        #    MainStatus = indigo.kHvacMode.Cool
                        else:
                            MainStatus = indigo.kHvacMode.HeatCool
                    else:
                        MainStatus = indigo.kHvacMode.Off
                except UnboundLocalError:
                    self.logger.debug("isACturnedOn doesn't exit... skipping On/Off/Mode update.")

                if 'RemoteZoneInfo' in jsonResponse['lastKnownState']:
                    for x in range (0,8):
                        ## go through all zones
                        self.logger.debug("Zone Number:"+str(x))
                        self.logger.debug(jsonResponse['lastKnownState']['RemoteZoneInfo'][x])
                        if 'NV_Title' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                            zonenames = zonenames +jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['NV_Title'] + ","
                        self.logger.debug(str(zonenames))

                        for dev in indigo.devices.itervalues('self.queZone'):
                            # go through all devices, and compare to 8 zones returned.
                            if int(dev.states["deviceMasterController"]) != int(device.id):
                                self.logger.debug("This Device has a new/different master Controller skipping")
                                continue  ## skip, next zone device

                            if int(dev.states["zoneNumber"])-1 == int(x):
                            #if dev.states["zoneName"] == jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['NV_Title']:
                                canoperate = False
                                livehumidity = float(0)
                                liveTemphys = float(0)
                                livetemp = float(0)
                                tempsetpointcool = float(0)
                                tempsetpointheat = float(0)
                                ZonePosition = int(0)
                                sensorbattery = int(0)

                                maxcoolsp = int(0)
                                maxheatsp = int(0)
                                mincoolsp = int(0)
                                minheatsp = int(0)
                                sensorid =""
                                ZoneStatus = indigo.kHvacMode.Off  ## Cool, HeatCool, Heat, Off
                                zoneOpen = False

                                if 'MaxCoolSetpoint' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    maxcoolsp = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['MaxCoolSetpoint']
                                if 'MaxHeatSetpoint' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    maxheatsp = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['MaxHeatSetpoint']
                                if 'MinCoolSetpoint' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    mincoolsp = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['MinCoolSetpoint']
                                if 'MinHeatSetpoint' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    minheatsp = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['MinHeatSetpoint']
                                if 'CanOperate' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    canoperate = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['CanOperate']
                                if 'LiveHumidity_pc' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    livehumidity = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['LiveHumidity_pc']
                                    livehumidity = round(float(livehumidity),3)
                                if 'LiveTemp_oC' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    livetemp = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['LiveTemp_oC']
                                if 'LiveTempHysteresis_oC' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    liveTemphys = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['LiveTempHysteresis_oC']
                                if 'TemperatureSetpoint_Cool_oC' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    tempsetpointcool = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['TemperatureSetpoint_Cool_oC']
                                if 'TemperatureSetpoint_Heat_oC' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    tempsetpointheat = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['TemperatureSetpoint_Heat_oC']
                                if 'Sensors' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    #self.logger.error(jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['Sensors'])
                                    for key,value in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['Sensors'].items():
                                        sensorid = key
                                    if 'Battery_pc' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['Sensors'][key]:
                                        sensorbattery = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['Sensors'][key]['Battery_pc']
                                # correct - as when zoneposition is 0 the zone is turned off, but! zone may in need be enabled
                                # so not corrrect
                                # saver to user the enabled zone to set Mode.off and report Zoneposition for use
                                if 'ZonePosition' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    ZonePosition = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['ZonePosition']
                                    self.logger.debug(f"ZonePosition:{ZonePosition}")
                                if listzonesopen[x]==True:
                                    if bool(isACturnedOn): ## AC Turned On may not be running
                                        ZoneStatus = MainStatus
                           #             if CompressorMode=="HEAT":
                           #                 ZoneStatus = indigo.kHvacMode.Heat
                           #             elif CompressorMode == "COOL":
                           #                 ZoneStatus = indigo.kHvacMode.Cool
                           #             else:
                           #                 ZoneStatus = indigo.kHvacMode.HeatCool  ## not running so don'tknow
                                    else:
                                        ZoneStatus = indigo.kHvacMode.Off
                                else:
                                    ZoneStatus = indigo.kHvacMode.Off

                                if int(ZonePosition) == 0 or listzonesopen[x] == False:
                                    zoneOpen = False
                                    percentageOpen = 0
                                    ZonePosition = 0
                                    self.logger.debug(f"{zoneOpen=} and {percentageOpen=}")
                                else:
                                    zoneOpen = True
                                    percentageOpen = int(ZonePosition)*5
                                    self.logger.debug(f"{zoneOpen=} and {percentageOpen=}")

                                listzonetemps.append(livetemp)
                                #if livehumidity > 0:
                                #    listzonehumidity.append(livehumidity)

                                zoneStatelist =[
                                    {'key': 'canOperate', 'value': canoperate},
                                    {'key': 'currentTemp', 'value': livetemp},
                                    {'key': 'temperatureInput1', 'value': livetemp},
                                    {'key': 'humidityInput1', 'value': livehumidity},
                                    {'key': 'currentHumidity', 'value': livehumidity},
                                    {'key': 'currentTempHystersis', 'value': liveTemphys},
                                    {'key': 'zonePercentageOpen', 'value': percentageOpen},
                                    {'key': 'sensorBattery', 'value': sensorbattery},
                                    {'key': 'sensorId', 'value': sensorid},
                                    {'key': 'zoneisEnabled', 'value': listzonesopen[x]},
                                    {'key': 'zoneisOpen', 'value': zoneOpen},
                                    {'key': 'hvacOperationMode', 'value': ZoneStatus},
                                    {'key': 'TempSetPointCool', 'value': tempsetpointcool},
                                    {'key': 'TempSetPointHeat', 'value': tempsetpointheat},
                                    {'key': 'zonePosition', 'value': ZonePosition},
                                    {'key': 'MinHeatSetpoint', 'value': minheatsp},
                                    {'key': 'MinCoolSetpoint', 'value': mincoolsp},
                                    {'key': 'MaxHeatSetpoint', 'value': maxheatsp},
                                    {'key': 'MaxCoolSetpoint', 'value': maxcoolsp},
                                    {'key': 'deviceMasterController', 'value': device.id},
                                    {'key': 'setpointHeat', 'value': tempsetpointheat},
                                    {'key': 'setpointCool', 'value': tempsetpointcool}
                                ]
                                dev.updateStatesOnServer(zoneStatelist)

            averageTemp = 0
            averageHum = 0
            tempInputsAll = []
            humdInputAll = []
            if len(listzonetemps) > 1:
                tempInputsAll = str(','.join(map(str, listzonetemps)) )
                averageTemp = reduce(lambda a,b:a+b, listzonetemps) / len(listzonetemps)
           # if len(listzonehumidity) >1:
           #     humdInputsAll = str(','.join(map(str, listzonehumidity)))
          #      averageHum = reduce(lambda a, b: a + b, listzonehumidity) / len(listzonehumidity)

            self.logger.debug(str(tempInputsAll))
            stateList = [
                {'key': 'indoorModel', 'value': indoorModel},
                {'key': 'setpointHeat', 'value': SystemSetpoint_Heat},
                {'key': 'setpointCool', 'value': SystemSetpoint_Cool},
                {'key': 'alertCleanFilter', 'value': alertCF},
                {'key': 'alertDRED', 'value': alertDRED},
                {'key': 'alertDefrosting', 'value': alertDefrosting},
                {'key': 'indoorFanRPM', 'value': fanRPM},
                {'key': 'indoorFanPWM', 'value': fanPWM},
                {'key': 'indoorUnitTemp', 'value': IndoorUnitTemp},
                {'key': 'outdoorUnitTemp', 'value': OutdoorUnitTemp},
                {'key': 'outdoorUnitPower', 'value': CompPower},
                {'key': 'outdoorUnitPWM', 'value': CompRunningPWM},
                {'key': 'compressorCapacity', 'value': compCapacity},
                {'key': 'outdoorUnitCompSpeed', 'value': CompSpeed},
                {'key': 'outdoorUnitCompMode', 'value': CompressorMode},
                {'key': 'hvacOperationMode', 'value': MainStatus},
                {'key': 'temperatureInput1', 'value': averageTemp},
                {'key': 'humidityInput1', 'value': main_humidity},
                {'key': 'quietMode', 'value': quietMode},
                {'key': 'fanSpeed', 'value': FanMode},
                {'key': 'outdoorUnitFanSpeed', 'value': outdoorFanSpeed},
            ]

            device.updateStatesOnServer(stateList)
            return zonenames

        except requests.exceptions.ReadTimeout as e:
            self.logger.debug("ReadTimeout with get System Actron Air:"+str(e))
            self.sleep(30)
            return "blank"
        except requests.exceptions.Timeout as e:
            self.logger.debug("Timeout with get System Actron Air:"+str(e))
            self.sleep(30)
            return "blank"
        except requests.exceptions.ConnectionError as e:
            self.logger.debug("ConnectionError with get System Actron Air:"+str(e))
            self.sleep(30)
            return "blank"
        except requests.exceptions.ConnectTimeout as e:
            self.logger.debug("Connect Timeout with get System Actron Air:"+str(e))
            self.sleep(30)
            return "blank"
        except requests.exceptions.HTTPError as e:
            self.logger.debug("HttpError with get System Actron Air:"+str(e))
            self.sleep(30)
            return "blank"
        except requests.exceptions.SSLError as e:
            self.logger.debug("SSL with get System Actron Air:"+str(e))
            self.sleep(30)
            return "blank"

        except Exception as e:
            self.logger.exception("Error getting System Status : " + repr(e))
            self.logger.debug("Error connecting" + str(e))
            self.sleep(15)
            return "blank"

# Get Nimbus end point token


    def get_nimbusPairingToken(self,username, password):

        try:
            self.logger.info( "Connecting using account username: %s" % username )
            #self.logger.info("Connecting to %s" % address)
            url = 'https://nimbus.actronair.com.au/api/v0/client/user-devices'
            headers = {'Host': 'nimbus.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au','User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0'}
            payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}

            r = requests.post(url, data=payload, headers=headers, timeout=20, verify=False)
            pairingToken =""

            if r.status_code==200:
                self.logger.debug(str(r.text))
                jsonResponse = r.json()
                if 'pairingToken' in jsonResponse:
                    self.logger.debug(jsonResponse['pairingToken'])
                    pairingToken = jsonResponse['pairingToken']
                    self.logger.info("Sucessfully connected and pairing Token received")

            else:
                self.logger.debug(str(r.text))
                self.logger.info(f"Error attempting to contect.  Given Error:{r.text}")
                return ""

            ## pairingToken should exists
            if pairingToken=="":
                self.logger.info("No pairing Token received?  Ending.")
                return ""

            ## now get bearer token
            ## will need to save these for each main device

            payload2 = {'grant_type':'refresh_token', 'refresh_token':pairingToken, 'client_id':'app'}
            url2 = 'https://nimbus.actronair.com.au/api/v0/oauth/token'

            newr = requests.post(url2, data=payload2, headers=headers, timeout=20, verify=False)

            accessToken = ""
            if newr.status_code==200:
                self.logger.debug(str(newr.text))
                jsonResponse = newr.json()
                if 'access_token' in jsonResponse:
                    self.logger.debug(jsonResponse['access_token'])
                    accessToken = jsonResponse['access_token']
            ## pairingToken should exists
            if accessToken=="":
                self.logger.info("No Access Token received?  Ending.")
                return ""
            self.connected = True
            return accessToken

        except Exception as e:
            self.logger.debug("Error getting Pairing Token : ",exc_info=True)
            self.sleep(30)
            self.connected = False
            return ""


    def getPairingToken(self,username, password):

        try:
            self.logger.info( "Connecting using account username: %s" % username )
            #self.logger.info("Connecting to %s" % address)
            url = 'https://que.actronair.com.au/api/v0/client/user-devices'
            headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au','User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0'}
            payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}

            r = requests.post(url, data=payload, headers=headers, timeout=20, verify=False)
            pairingToken =""

            if r.status_code==200:
                self.logger.debug(str(r.text))
                jsonResponse = r.json()
                if 'pairingToken' in jsonResponse:
                    self.logger.debug(jsonResponse['pairingToken'])
                    pairingToken = jsonResponse['pairingToken']
                    self.logger.info("Sucessfully connected and pairing Token received")

            else:
                self.logger.debug(str(r.text))
                self.logger.info(f"Error attempting to contect.  Given Error:{r.text}")
                return ""

            ## pairingToken should exists
            if pairingToken=="":
                self.logger.info("No pairing Token received?  Ending.")
                return ""

            ## now get bearer token
            ## will need to save these for each main device

            payload2 = {'grant_type':'refresh_token', 'refresh_token':pairingToken, 'client_id':'app'}
            url2 = 'https://que.actronair.com.au/api/v0/oauth/token'

            newr = requests.post(url2, data=payload2, headers=headers, timeout=20, verify=False)

            accessToken = ""
            if newr.status_code==200:
                self.logger.debug(str(newr.text))
                jsonResponse = newr.json()
                if 'access_token' in jsonResponse:
                    self.logger.debug(jsonResponse['access_token'])
                    accessToken = jsonResponse['access_token']
            ## pairingToken should exists
            if accessToken=="":
                self.logger.info("No Access Token received?  Ending.")
                return ""
            self.connected = True
            return accessToken

        except Exception as e:
            self.logger.debug("Error getting Pairing Token : ",exc_info=True)
            self.sleep(30)
            self.connected = False
            return ""

    ########################################
    # Thermostat Action callback
    ######################
    # Main thermostat action bottleneck called by Indigo Server.
    def actionControlThermostat(self, action, dev):

        self.logger.debug("actionControlThermostat called")

        ###### SET HVAC MODE ######
        if action.thermostatAction == indigo.kThermostatAction.SetHvacMode:
            self._handleChangeHvacModeAction(dev, action.actionMode)

        ###### SET FAN MODE ######
        elif action.thermostatAction == indigo.kThermostatAction.SetFanMode:
            self._handleChangeFanModeAction(dev, action.actionMode)

        ###### SET COOL SETPOINT ######
        elif action.thermostatAction == indigo.kThermostatAction.SetCoolSetpoint:
            newSetpoint = action.actionValue
            self._handleChangeSetpointAction(dev, newSetpoint, u"change cool setpoint", u"setpointCool")

        ###### SET HEAT SETPOINT ######
        elif action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint:
            newSetpoint = action.actionValue
            self._handleChangeSetpointAction(dev, newSetpoint, u"change heat setpoint", u"setpointHeat")

        ###### DECREASE/INCREASE COOL SETPOINT ######
        elif action.thermostatAction == indigo.kThermostatAction.DecreaseCoolSetpoint:
            newSetpoint = dev.coolSetpoint - action.actionValue
            self._handleChangeSetpointAction(dev, newSetpoint, u"decrease cool setpoint", u"setpointCool")

        elif action.thermostatAction == indigo.kThermostatAction.IncreaseCoolSetpoint:
            newSetpoint = dev.coolSetpoint + action.actionValue
            self._handleChangeSetpointAction(dev, newSetpoint, u"increase cool setpoint", u"setpointCool")

        ###### DECREASE/INCREASE HEAT SETPOINT ######
        elif action.thermostatAction == indigo.kThermostatAction.DecreaseHeatSetpoint:
            newSetpoint = dev.heatSetpoint - action.actionValue
            self._handleChangeSetpointAction(dev, newSetpoint, u"decrease heat setpoint", u"setpointHeat")

        elif action.thermostatAction == indigo.kThermostatAction.IncreaseHeatSetpoint:
            newSetpoint = dev.heatSetpoint + action.actionValue
            self._handleChangeSetpointAction(dev, newSetpoint, u"increase heat setpoint", u"setpointHeat")

        ###### REQUEST STATE UPDATES ######
        elif action.thermostatAction in [indigo.kThermostatAction.RequestStatusAll,
                                         indigo.kThermostatAction.RequestMode,
                                         indigo.kThermostatAction.RequestEquipmentState,
                                         indigo.kThermostatAction.RequestTemperatures,
                                         indigo.kThermostatAction.RequestHumidities,
                                         indigo.kThermostatAction.RequestDeadbands,
                                         indigo.kThermostatAction.RequestSetpoints]:
            self._refreshStatesFromHardware(dev)

    ########################################
    # General Action callback
    ######################
    def actionControlUniversal(self, action, dev):
        ###### BEEP ######
        if action.deviceAction == indigo.kUniversalAction.Beep:
            # Beep the hardware module (dev) here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

        ###### ENERGY UPDATE ######
        elif action.deviceAction == indigo.kUniversalAction.EnergyUpdate:
            # Request hardware module (dev) for its most recent meter data here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy update request"))

        ###### ENERGY RESET ######
        elif action.deviceAction == indigo.kUniversalAction.EnergyReset:
            # Request that the hardware module (dev) reset its accumulative energy usage data here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy reset request"))

        ###### STATUS REQUEST ######
        elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
            # Query hardware module (dev) for its current status here. This differs from the
            # indigo.kThermostatAction.RequestStatusAll action - for instance, if your thermo
            # is battery powered you might only want to update it only when the user uses
            # this status request (and not from the RequestStatusAll). This action would
            # get all possible information from the thermostat and the other call
            # would only get thermostat-specific information:
            # ** GET BATTERY INFO **
            # and call the common function to update the thermo-specific data
            self._refreshStatesFromHardware(dev)
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))

## Actions ###########################################################################################

    def setFanSpeed(self, action):
        self.logger.debug(u"setFanSpeed Called as Action.")
        fanspeed = action.props.get('Speed',"LOW")
        deviceID = action.props.get("deviceID","")

        if deviceID =="":
            self.logger.info("Details not correct.")
            return

        maindevice = indigo.devices[int(deviceID)]
        accessToken, serialNo, maindevice = self.returnmainAccessSerial(maindevice)
        if accessToken == "error" or serialNo=="error":
            self.logger.info("Unable to complete accessToken or Serial No issue")
            return
        self.sendCommand(accessToken, serialNo, "UserAirconSettings.FanMode", str(fanspeed), 0)
        return


    def setZone(self, action):
        self.logger.debug(u"setZone Called as Action.")
        zoneonoroff = action.props.get('setting',"OFF")  #add TOGGLE
        deviceID = action.props.get("deviceID","")

        if deviceID =="":
            self.logger.info("Details not correct.")
            return
        zonedevice = indigo.devices[int(deviceID)]
        accessToken, serialNo, maindevice = self.returnmainAccessSerial(zonedevice)
        mainDevicehvacMode = maindevice.states['hvacOperationMode']
        if mainDevicehvacMode == indigo.kHvacMode.Off:
            self.logger.info("Main Que Device is Off.  System needs to be running to open/close Zones.")
            return
        if accessToken == "error" or serialNo=="error":
            self.logger.info("Unable to complete accessToken or Serial No issue")
            return
        if zonedevice.deviceTypeId == "queZone":
            ## if a zone device needs different command
            ## probably best to be OFF or anything else
            zoneNumber = str(int(zonedevice.states['zoneNumber'])-1)  # counts zones from zero
            if zonedevice.states['hvacOperationMode'] == indigo.kHvacMode.Off and (zoneonoroff == "ON" or zoneonoroff=="TOGGLE"):
                ## need to turn on Zone
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", True, 0)
                self.logger.info("Turning on Zone number "+str(zoneNumber))
                zonedevice.updateStateOnServer("zoneisEnabled", True)
                zonedevice.updateStateOnServer('hvacOperationMode', mainDevicehvacMode)
            elif zoneonoroff == "OFF":  ## need to turn AC off
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", False, 0)
                self.logger.info("Turning off Zone number "+str(int(zoneNumber)+1))
                zonedevice.updateStateOnServer("zoneisEnabled", True)
                zonedevice.updateStateOnServer('hvacOperationMode', mainDevicehvacMode)
            elif zonedevice.states['hvacOperationMode'] != indigo.kHvacMode.Off and (zoneonoroff == "OFF" or zoneonoroff=="TOGGLE"):
                ## DEVICE IS ON - COOL or Heat and wants to go off or toggle
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", False, 0)
                self.logger.info("Turning off Zone number "+str(int(zoneNumber)+1))
                zonedevice.updateStateOnServer("zoneisEnabled", False)
                zonedevice.updateStateOnServer('hvacOperationMode', mainDevicehvacMode)

        return

    def increaseZoneHeatPoint(self,action):  # increase by 0.5 degrees
        self.logger.debug(u'Increase zone heat point called as Action.')
        try:
            deviceID = action.props.get("deviceID", "")

            if deviceID == ""  :
                self.logger.info("Action details not correct.")
                return
            zonedevice = indigo.devices[int(deviceID)]
            accessToken, serialNo, maindevice = self.returnmainAccessSerial(zonedevice)

            maxheatsp = float(zonedevice.states['MaxHeatSetpoint'])
            minheatsp = float(zonedevice.states['MinHeatSetpoint'])
            tempsp = float(zonedevice.states['TempSetPointHeat'])

            if tempsp >= maxheatsp or (tempsp+0.5)> maxheatsp:  # shouldn't ever be greater..
                self.logger.info("Max Heat Set point reached for zone.  Increase Master limit to go higher with the zones.")
                return

            targetsp = float(tempsp + 0.5)
            if zonedevice.deviceTypeId == "queZone":
                ## if a zone device needs different command
                ## probably best to be OFF or anything else
                zoneNumber = str(int(zonedevice.states['zoneNumber']) - 1)  # counts zones from zero
                # update device here, so if command sent and then re-sent will reflect new temp wanted
                zonedevice.updateStateOnServer("TempSetPointHeat", float(targetsp))
                zonedevice.updateStateOnServer("setpointHeat", float(targetsp))
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Heat_oC", float(targetsp), 0)
                self.logger.info("Heat SetPoint of Zone " + str( int(zoneNumber)+ 1) + " updated to " + str(targetsp) + " degrees")
        except:
            self.logger.exception("Caught Exception in increaseZoneHP")

    def decreaseZoneHeatPoint(self,action):  # deccrease by 0.5 degrees
        self.logger.debug(u'Decrease zone heat point called as Action.')
        try:
            deviceID = action.props.get("deviceID", "")

            if deviceID == ""  :
                self.logger.info("Action details not correct.")
                return
            zonedevice = indigo.devices[int(deviceID)]
            accessToken, serialNo, maindevice = self.returnmainAccessSerial(zonedevice)

            maxheatsp = float(zonedevice.states['MaxHeatSetpoint'])
            minheatsp = float(zonedevice.states['MinHeatSetpoint'])
            tempsp = float(zonedevice.states['TempSetPointHeat'])

            if tempsp <= minheatsp or (tempsp-0.5)< minheatsp:  # shouldn't ever be greater..
                self.logger.info("Minimum Heat Set point reached for zone.  Decrease Master limit to go lower with the zones.")
                return

            targetsp = float(tempsp - 0.5)
            if zonedevice.deviceTypeId == "queZone":
                ## if a zone device needs different command
                ## probably best to be OFF or anything else
                zoneNumber = str(int(zonedevice.states['zoneNumber']) - 1)  # counts zones from
                zonedevice.updateStateOnServer("TempSetPointHeat", float(targetsp))
                zonedevice.updateStateOnServer("setpointHeat", float(targetsp))
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Heat_oC", float(targetsp), 0)
                self.logger.info("Heat SetPoint of Zone " + str(int(zoneNumber) + 1) + " updated to " + str(targetsp) + " degrees")
        except:
            self.logger.exception("Caught Exception in decrease Zone Heat Point")

    def increaseZoneCoolPoint(self, action):  # deccrease by 0.5 degrees
        self.logger.debug(u'Increase zone Cool point called as Action.')
        try:
            deviceID = action.props.get("deviceID", "")

            if deviceID == "":
                self.logger.info("Action details not correct.")
                return
            zonedevice = indigo.devices[int(deviceID)]
            accessToken, serialNo, maindevice = self.returnmainAccessSerial(zonedevice)

            maxcoolsp = float(zonedevice.states['MaxCoolSetpoint'])
            mincoolsp = float(zonedevice.states['MinCoolSetpoint'])
            tempsp = float(zonedevice.states['TempSetPointCool'])

            if tempsp >= maxcoolsp or (tempsp + 0.5) > maxcoolsp:  # shouldn't ever be greater..
                self.logger.info(
                    "Maximum Cool Set point reached for zone.  Increase Master limit to go higher within the zones.")
                return

            targetsp = float(tempsp + 0.5)
            if zonedevice.deviceTypeId == "queZone":
                ## if a zone device needs different command
                ## probably best to be OFF or anything else
                zoneNumber = str(int(zonedevice.states['zoneNumber']) - 1)  # counts zones from zero
                zonedevice.updateStateOnServer("TempSetPointCool", float(targetsp))
                zonedevice.updateStateOnServer("setpointCool", float(targetsp))
                self.sendCommand(accessToken, serialNo,  "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Cool_oC", float(targetsp), 0)
                self.logger.info("Cool SetPoint of Zone " + str(int(zoneNumber) + 1) + " updated to " + str(targetsp) + " degrees")
        except:
            self.logger.exception("Caught Exception in decrease Zone Cool set Point")

    def decreaseZoneCoolPoint(self, action):  # deccrease by 0.5 degrees
        self.logger.debug(u'Decrease zone Cool point called as Action.')
        try:
            deviceID = action.props.get("deviceID", "")

            if deviceID == "":
                self.logger.info("Action details not correct.")
                return
            zonedevice = indigo.devices[int(deviceID)]
            accessToken, serialNo, maindevice = self.returnmainAccessSerial(zonedevice)

            maxcoolsp = float(zonedevice.states['MaxCoolSetpoint'])
            mincoolsp = float(zonedevice.states['MinCoolSetpoint'])
            tempsp = float(zonedevice.states['TempSetPointCool'])

            if tempsp <= mincoolsp or (tempsp - 0.5) < mincoolsp:  # shouldn't ever be greater..
                self.logger.info(
                    "Minimum Cool Set point reached for zone.  Decrease Master limit to go lower with the zones.")
                return

            targetsp = float(tempsp - 0.5)
            if zonedevice.deviceTypeId == "queZone":
                ## if a zone device needs different command
                ## probably best to be OFF or anything else
                zoneNumber = str(int(zonedevice.states['zoneNumber']) - 1)  # counts zones from zero
                zonedevice.updateStateOnServer("TempSetPointCool", float(targetsp))
                zonedevice.updateStateOnServer("setpointCool", float(targetsp))
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Cool_oC", float(targetsp),  0)
                self.logger.info(u"Cool SetPoint of Zone " + str( int(zoneNumber)+ 1 ) + u" updated to " + str(targetsp) + u" degrees")

        except:
            self.logger.exception("Caught Exception in decrease Zone Cool set Point")

    def setZoneCoolPoint(self, action):
        self.logger.debug(u"setZoneCoolsetpoint Called as Action.")
        settemp = action.props.get('tempoptions', "")  # add TOGGLE
        deviceID = action.props.get("deviceID", "")

        if deviceID == "" or settemp=="" :
            self.logger.info("Action details not correct.")
            return
        zonedevice = indigo.devices[int(deviceID)]
        accessToken, serialNo, maindevice = self.returnmainAccessSerial(zonedevice)

        mainDevicehvacMode = maindevice.states['hvacOperationMode']
        if accessToken == "error" or serialNo == "error":
            self.logger.info("Unable to complete accessToken or Serial No issue")
            return
        if zonedevice.deviceTypeId == "queZone":
            ## if a zone device needs different command
            ## probably best to be OFF or anything else
            zoneNumber = str(int(zonedevice.states['zoneNumber']) - 1)  # counts zones from zero
            if zonedevice.states['hvacOperationMode'] == indigo.kHvacMode.Off:
                ## need to turn on Zone
                self.logger.info("Zone is disabled/off currently, not sure can set SetPoint temperature.. happy to try...")
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Cool_oC", float(settemp),0)
            elif zonedevice.states['hvacOperationMode'] != indigo.kHvacMode.Off:
                self.logger.debug("Checking: Zone appears on:")
                ## DEVICE IS ON - COOL or Heat and wants to go off or toggle
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Cool_oC", float(settemp),0)
        return

    def setZoneHeatPoint(self, action):
        self.logger.debug(u"setZoneHeatsetpoint Called as Action.")
        settemp = action.props.get('tempoptions', "")  # add TOGGLE
        deviceID = action.props.get("deviceID", "")

        if deviceID == "" or settemp=="" :
            self.logger.info("Action details not correct.")
            return
        zonedevice = indigo.devices[int(deviceID)]
        accessToken, serialNo, maindevice = self.returnmainAccessSerial(zonedevice)

        mainDevicehvacMode = maindevice.states['hvacOperationMode']
        if accessToken == "error" or serialNo == "error":
            self.logger.info("Unable to complete accessToken or Serial No issue")
            return
        if zonedevice.deviceTypeId == "queZone":
            ## if a zone device needs different command
            ## probably best to be OFF or anything else
            zoneNumber = str(int(zonedevice.states['zoneNumber']) - 1)  # counts zones from zero
            if zonedevice.states['hvacOperationMode'] == indigo.kHvacMode.Off:
                ## need to turn on Zone
                self.logger.info("Zone is disabled/off currently, not sure can set SetPoint temperature.. happy to try...")
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Heat_oC", float(settemp),0)


            elif zonedevice.states['hvacOperationMode'] != indigo.kHvacMode.Off:
                self.logger.debug("Checking: Zone appears on:")
                ## DEVICE IS ON - COOL or Heat and wants to go off or toggle
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Heat_oC", float(settemp),0)

        return

    def setMain(self, action):
        self.logger.debug(u"setMain Device Called as Action.")
        onoroff = action.props.get('setting',"OFF")  #add TOGGLE
        deviceID = action.props.get("deviceID","")
        sendSuccess= False

        if deviceID =="":
            self.logger.info("Details not correct.")
            return

        maindevicegiven = indigo.devices[int(deviceID)]
        accessToken, serialNo, maindevice = self.returnmainAccessSerial(maindevicegiven)
        mainDevicehvacMode = maindevice.states['hvacOperationMode']

        if accessToken == "error" or serialNo=="error":
            self.logger.info("Unable to complete accessToken or Serial No issue")
            return

        if maindevice.deviceTypeId == "ActronQueMain":
            ## if a zone device needs different command
            ## probably best to be OFF or anything else
            if mainDevicehvacMode == indigo.kHvacMode.Off and (onoroff == "ON" or onoroff=="TOGGLE"):
                ## need to turn on and change mode
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.isOn", True, 0)
                self.logger.info("Turning on AC System.")
            elif onoroff == "OFF":  ## need to turn AC off
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.isOn", False, 0)
                self.logger.info("Turning off AC System")
                ## only for main device
            elif mainDevicehvacMode != indigo.kHvacMode.Off and (onoroff == "OFF" or onoroff=="TOGGLE"):
                ## DEVICE IS ON - COOL or Heat and wants to go off or toggle
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.isOn", False, 0)
                self.logger.info("Turning off AC System.")

        if sendSuccess:
            # If success then log that the command was successfully sent.
            indigo.server.log(u"Sent \"%s\" mode change to %s" % (maindevice.name, onoroff))
            if "hvacOperationMode" in maindevice.states:
                if onoroff == "OFF":
                    maindevice.updateStateOnServer("hvacOperationMode", indigo.kHvacMode.Off)
            ## Update status as zones open now, devices on etc.
            self.sleep(2)
            accessToken = maindevice.pluginProps['accessToken']
            serialNo = maindevice.pluginProps['serialNo']
            if accessToken == "" or serialNo == "":
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                self.checkMainDevices()
            else:
                self.getSystemStatus(maindevice, accessToken, serialNo)
        return

    def setQuiet(self, action):
        self.logger.debug(u"setQuiet Device Called as Action.")
        onoroff = action.props.get('setting',"OFF")  #add TOGGLE
        deviceID = action.props.get("deviceID","")
        sendSuccess= False

        if deviceID =="":
            self.logger.info("Details not correct.")
            return

        maindevicegiven = indigo.devices[int(deviceID)]
        accessToken, serialNo, maindevice = self.returnmainAccessSerial(maindevicegiven)
      #  mainDevicehvacMode = maindevice.states['hvacOperationMode']

        if accessToken == "error" or serialNo=="error":
            self.logger.info("Unable to complete accessToken or Serial No issue")
            return

        crtquietMode = maindevicegiven.states['quietMode']
        targetquietMode = False

        if onoroff == "ON":
            targetquietMode = True
        elif onoroff == "OFF":
            targetquietMode = False
        elif onoroff == "TOGGLE":
            if crtquietMode == True:
                targetquietMode = False
            elif crtquietMode == False:
                targetquietMode = True

        self.logger.info("setQuiet Mode Action called.  Current Mode:"+str(crtquietMode)+" and target Mode:"+str(targetquietMode))

        if maindevice.deviceTypeId == "ActronQueMain":
            ## if a zone device needs different command
            ## probably best to be OFF or anything else
            if crtquietMode == targetquietMode:
                self.logger.info("Quiet Mode already set to the target mode.  No command therefore sent.")
                return
            else:
                ## need to turn on and change mode
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.QuietMode", bool(targetquietMode), 0)
                self.logger.info("Setting Quiet Mode to "+str(targetquietMode))

        return
    ########################################
    def _refreshStatesFromHardware(self, dev):
        self.logger.debug("refreshing States from Hardware")
        if dev.deviceTypeId == "ActronQueMain":
            accessToken = dev.pluginProps['accessToken']
            serialNo = dev.pluginProps['serialNo']
            if accessToken == "" or serialNo == "":
                self.logger.debug("Try again later, once Main device setup and connected")
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                self.checkMainDevices()
            else:
                self.getSystemStatus(dev, accessToken, serialNo)
        else: ## if zonenames - need to get device of Main
            maindevice = indigo.devices[int(dev.states["deviceMasterController"])]
            accessToken = maindevice.pluginProps['accessToken']
            serialNo = maindevice.pluginProps['serialNo']
            if accessToken == "" or serialNo == "":
                self.logger.debug("Try again later, once Main device setup and connected")
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                self.checkMainDevices()
            else:
                self.getSystemStatus(maindevice, accessToken, serialNo)
    ######################
    def returnmainAccessSerial(self,dev):
        self.logger.debug("Figuring out Access Token from Hardware")
        if dev.deviceTypeId == "ActronQueMain":
            accessToken = dev.pluginProps['accessToken']
            serialNo = dev.pluginProps['serialNo']
            if accessToken == "" or serialNo == "":
                self.logger.debug("Try again later, once Main device setup and connected")
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                return "error","error","error"
            else:
                return accessToken,serialNo,dev

        else: ## if zonenames - need to get device of Main
            maindevice = indigo.devices[int(dev.states["deviceMasterController"])]
            accessToken = maindevice.pluginProps['accessToken']
            serialNo = maindevice.pluginProps['serialNo']
            if accessToken == "" or serialNo == "":
                self.logger.debug("Try again later, once Main device setup and connected")
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                return "error","error","error"
            else:
                return accessToken, serialNo, maindevice

    # Process action request from Indigo Server to change main thermostat's main mode.
    def _handleChangeHvacModeAction(self, dev, newHvacMode):
        # Command hardware module (dev) to change the thermostat mode here:
        self.logger.debug(f"_handleChangeHVAC Mode Called.  {newHvacMode=}")
        sendSuccess = False  # Set to False if it failed.
        actionStr = _lookupActionStrFromHvacMode(newHvacMode)

        accessToken, serialNo, maindevice = self.returnmainAccessSerial(dev)
        if accessToken == "error" or serialNo=="error":
            self.logger.info("Unable to complete accessToken or Serial Number issue")
            return

        mainDevicehvacMode = maindevice.states['hvacOperationMode']

        ## if device asked to hardward control main - then turn on main, and change mode, or turn off
        if dev.deviceTypeId  =="ActronQueMain":
            if maindevice.states['hvacOperationMode'] == indigo.kHvacMode.Off and newHvacMode != indigo.kHvacMode.Off:
                ## need to turn on and change mode
                self.sendCommand(accessToken, serialNo,"UserAirconSettings.isOn", True, 0)
                self.logger.info("Turning on AC System, prior to changing mode")
            elif newHvacMode == indigo.kHvacMode.Off: ## need to turn AC off
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.isOn", False, 0)
                self.logger.info("Turning off AC System. ")

            ## only for main device
            sendSuccess = self.sendCommand(accessToken, serialNo, "UserAirconSettings.Mode", str(actionStr).upper(),0)

        if dev.deviceTypeId == "queZone":
            ## if a zone device needs different command
            ## probably best to be OFF or anything else
            zoneNumber = str(int(dev.states['zoneNumber'])-1)  # counts zones from zero

            if dev.states['hvacOperationMode'] == indigo.kHvacMode.Off and newHvacMode != indigo.kHvacMode.Off:
                ## need to turn on Zone
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", True,0)
                self.logger.info("Turning on Zone number "+str(zoneNumber))
                dev.updateStateOnServer("zoneisEnabled", True)
                dev.updateStateOnServer('hvacOperationMode', mainDevicehvacMode)
            elif newHvacMode == indigo.kHvacMode.Off:  ## need to turn AC off
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", False,0)
                dev.updateStateOnServer("zoneisEnabled", False)
                dev.updateStateOnServer('hvacOperationMode', indigo.kHvacMode.Off)
                self.logger.info("Turning off Zone number "+str(zoneNumber))

            if accessToken == "" or serialNo == "":
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                self.checkMainDevices()
            else:
                zonenames = self.getSystemStatus(maindevice, accessToken, serialNo)


    ######################
    # Process action request from Indigo Server to change thermostat's fan mode.
    def _handleChangeFanModeAction(self, dev, newFanMode):
        # Command hardware module (dev) to change the fan mode here:
        # ** IMPLEMENT ME **
        sendSuccess = False  # Set to False if it failed.

        self.logger.info("Change Fan Mode unsupported currently.  Use Action Group to change.")
        return

    def _handleChangeHvacModeActionError(self,dev,error):
        ##
        self.logger.info("Error changing Hvac mode.  Aborting.")
        return

    ######################
    # Process action request from Indigo Server to change a cool/heat setpoint.
    def _handleChangeSetpointAction(self, dev, newSetpoint, logActionName, stateKey):

        self.logger.debug('_handleChangeSetpoint called: device'+str(dev.name)+" newSetpoint:"+str(newSetpoint)+ str(logActionName)+" "+str(stateKey))

        if dev.deviceTypeId == "queZone":
            maxheatsp = float(dev.states["MaxHeatSetpoint"])
            minheatsp = float(dev.states["MinHeatSetpoint"])
            maxcoolsp = float(dev.states["MaxCoolSetpoint"])
            mincoolsp = float(dev.states["MinCoolSetpoint"])
            if stateKey == u"setpointCool":
                if newSetpoint >= maxcoolsp:
                    self.logger.info( "Maximum Cool Set point reached for zone.  Change Master limit to go higher/lower with the zones.")
                    return
                    newSetpoint = maxcoolsp
                elif newSetpoint <= mincoolsp:
                    self.logger.info( "Minimum Cool Set point reached for zone.  Change Master limit to go higher/lower with the zones.")
                    return
                    newSetpoint = mincoolsp
            else:
                if newSetpoint >=maxheatsp:
                    self.logger.info(  "Maximum Heat Set point reached for zone.  Change Master limit to go higher/lower with the zones.")
                    return
                    newSetpoint=maxheatsp
                elif newSetpoint <= minheatsp:
                    self.logger.info(  "Minimum Heat Set point reached for zone.  Change Master limit to go higher/lower with the zones.")
                    return
                    newSetpoint = minheatsp
        else:  ## main device settings
            if newSetpoint < 8.0:
                newSetpoint = 16.0  # Arbitrary -- set to whatever hardware minimum setpoint value is.
            elif newSetpoint > 30.0:
                newSetpoint = 30.0  # Arbitrary -- set to whatever hardware maximum setpoint value is.

        sendSuccess = False

        accessToken, serialNo, maindevice = self.returnmainAccessSerial(dev)
        if accessToken == "error" or serialNo == "error":
            self.logger.info("Unable to complete accessToken or Serial No issue")
            return

        mainDevicehvacMode = maindevice.states['hvacOperationMode']

        ## if device asked to hardward control main - then turn on main, and change mode, or turn off
        if dev.deviceTypeId == "queZone":

            zoneNumber = str(int(dev.states['zoneNumber']) - 1)  # counts zones from zero
            if stateKey == u"setpointHeat":
                dev.updateStateOnServer("TempSetPointHeat", float(newSetpoint))
                dev.updateStateOnServer("setpointHeat", float(newSetpoint))
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Heat_oC",float(newSetpoint), 0)
                self.logger.info("Heat SetPoint of Zone " + str(int(zoneNumber) + 1) + " updated to " + str( newSetpoint) + " degrees")
            elif stateKey ==u"setpointCool":
                dev.updateStateOnServer("TempSetPointCool", float(newSetpoint))
                dev.updateStateOnServer("setpointCool", float(newSetpoint))
                self.sendCommand(accessToken, serialNo, "RemoteZoneInfo[" + zoneNumber + "].TemperatureSetpoint_Cool_oC", float(newSetpoint), 0)
                self.logger.info("Cool SetPoint of Zone " + str(int(zoneNumber) + 1) + " updated to " + str( newSetpoint) + " degrees")
        else:
            ## need to turn on and change mode
            if stateKey == u"setpointCool":
                dev.updateStateOnServer("setpointCool", float(newSetpoint))
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.TemperatureSetpoint_Cool_oC", newSetpoint, 0)
            elif stateKey == u"setpointHeat":
                dev.updateStateOnServer("setpointHeat", float(newSetpoint))
                self.sendCommand(accessToken, serialNo, "UserAirconSettings.TemperatureSetpoint_Heat_oC", newSetpoint, 0)

            # If success then log that the command was successfully sent.
        indigo.server.log(u"sent \"%s\" %s to %.1f°" % (dev.name, logActionName, newSetpoint))

            # And then tell the Indigo Server to update the state.

    ########################################
    def sendCommand(self, accessToken, serialNo, commandtype, commandbody, repeats):

        self.logger.debug(u"Use Que for Command..")
        if self.debug1:
            self.logger.debug(f"SendCommand Debug:\n{accessToken=}\n{serialNo=}\n{commandtype=}\n{commandbody=}\n{repeats=}")
        item = QueCommand(accessToken, serialNo, commandtype, commandbody, repeats)
        if self.debug1:
            self.logger.debug(u'Putting Command item into Que: Item:' + str(item))
        self.que.put(item)
        return

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.debugLog(u"validateDeviceConfigUi called")
        # User choices look good, so return True (client will then close the dialog window).
        return (True, valuesDict)

    def deviceStartComm(self, device):
        self.logger.debug(u"deviceStartComm called for " + device.name)
        try:
            device.stateListOrDisplayStateIdChanged()
            newProps = device.pluginProps
            self.logger.debug("Props:"+str(newProps))
            if device.deviceTypeId == 'ActronQueMain':
                #device.updateStateOnServer('deviceIsOnline', value=True)
                newProps["NumHumidityInputs"] = 1

            newProps["ShowCoolHeatEquipmentStateUI"]= True
            newProps["SupportsHvacFanMode"] = False

            if device.deviceTypeId == "queZone":
                newProps["SupportsCoolSetpoint"] = True
                newProps["SupportsHeatSetpoint"] = True
                newProps["NumHumidityInputs"] = 1
            device.replacePluginPropsOnServer(newProps)
        except:
            self.logger.exception("Exception in DeviceStartComm")
##
    def generateLabels(self, device,valuesDict, somethingunused):
        self.logger.info("Updating Zone and other Labels")
        self.labelsdueupdate = True
        return

    def shutdown(self):

         self.debugLog(u"shutdown() method called.")

    def startup(self):

        self.debugLog(u"Starting Plugin. startup() method called.")

        self.logger.debug(u'Starting Actron Que Command Thread:')
        CommandThread = threading.Thread(target=self.threadCommand )
        CommandThread.setDaemon(True  )
        CommandThread.start()

#### Actron Que Command Thread
    def threadCommand(self):
        self.logger.debug("ThreadCommand up and running...")
        while True:
            self.sleep(0.5)
            try:
                self.sleep(1)
                item = self.que.get()   # blocks here until another que items
                ## blocks here until next item
                self.sendingCommand = True
                commandaccessToken = item.commandaccessToken
                commandSerialNo = item.commandSerialNo
                commandtype = item.commandtype
                commandbody = item.commandbody
                commandrepeats = item.commandrepeats

                # Retrieve optional parameters
                deviceid = item.deviceid
                hvacOperationMode = item.hvacOperationMode  ##Main Oper Mode
                setpointCool = item.setpointCool
                setpointHeat = item.setpointHeat
                zoneActive = item.zoneActive

                self.logger.debug(
                    "Optional parameters: deviceid=%s, hvacOperationMode=%s, setpointCool=%s, setpointHeat=%s",
                    deviceid,
                    hvacOperationMode,
                    setpointCool,
                    setpointHeat,

                )

                try:
                    self.logger.debug("Sending System Command for System Serial No %s" % commandSerialNo)
                    self.logger.debug("Sending Command " + str(commandtype) + " and commandbody:" + str(
                        commandbody) + " and time command repeated:" + str(commandrepeats))

                    if commandrepeats >= 5:
                        self.logger.info('Command failed after multiple repeats. Aborting.')
                        continue

                    # self.logger.info("Connecting to %s" % address)
                    url = 'https://que.actronair.com.au/api/v0/client/ac-systems/cmds/send?serial=' + str(commandSerialNo)
                    headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au',
                               'User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0',
                               'Authorization': 'Bearer ' + commandaccessToken}
                    payload = {"command": {commandtype: commandbody, "type": "set-settings"}}

                    self.logger.debug(str(payload))
                    r = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
                    self.logger.debug(r.text)

                    if r.status_code != 200:
                        self.logger.debug("Error Message from get System Status.")
                        self.logger.debug(str(r.text))
                        commandrepeats = commandrepeats + 1
                        if r.json() is None:
                            self.logger.info("Nothing returned from Action API.  Aborting.")

                        if 'type' in r.json():
                            typereturned = str(r.json()['type'])
                            self.logger.debug("Type returned and is " + str(typereturned))
                            if typereturned == "timeout":
                                self.logger.info("Timeout received from Actron API for System Command.  Will retry.")
                                if int(commandrepeats) <= 5:
                                    self.sleep(5)
                                    self.sendCommand(commandaccessToken, commandSerialNo, commandtype, commandbody,   int(commandrepeats))
                                else:
                                    self.logger.info("Failed after 5 repeats.  Abandoning attempts.")

                        # Authorisation may have failed/taken over
                        self.logger.debug("Recreating Tokens incase expired.  Another login and then retrying.")
                        self.checkMainDevices()
                        self.sleep(5)
                        if int(commandrepeats) <= 5:
                            self.sendCommand(commandaccessToken, commandSerialNo, commandtype, commandbody, int(commandrepeats))
                        else:
                            self.logger.info("Failed after 5 repeats.  Abandoning attempts.")


                    if r.json() is not None:
                        if 'type' in r.json():
                            typereturned = str(r.json()['type'])
                            if typereturned == "ack":  ## command successful
                                self.logger.info("Command ack successfully by QUE. Returning successful completion.")
                                self.sentCommand = True  ## Successfully command sent.
                                # If deviceid and hvacOperationMode are provided, update Indigo device state.
                                # if deviceid is not None and hvacOperationMode is not None:
                                #     try:
                                #         device = indigo.devices[int(deviceID)]
                                #         if device.deviceTypeId == "queZone":
                                #             if str(zoneActive) == "True":
                                #                 zones.updateStateOnServer("zoneisEnabled", True)
                                #                 currentMode = item.hvacOperationMode
                                #                 zones.updateStateOnServer('hvacOperationMode', currentMode)
                                #             elif str(zoneActive) == "False":
                                #                 zones.updateStateOnServer("zoneisEnabled", False)
                                #                 zones.updateStateOnServer('hvacOperationMode', indigo.kHvacMode.Off)
                                #     except:
                                #         self.logger.debug(f"Exception Caught in Command Update", exc_info=True)

                    self.sendingCommand = False
                    self.latestEventsConnectionError = False
                    self.que.task_done()

                except requests.Timeout:
                    self.logger.info("Request timedout to que.actron.com.au")
                    self.latestEventsConnectionError = True
                    self.sleep(1)

                except:
                    self.logger.exception("Exception in send Command")


            except self.StopThread:
                self.logger.debug(u'Self.Stop Thread called')

            except:
                self.logger.exception(u'Command Thread Excepton')
####################################

    def validatePrefsConfigUi(self, valuesDict):

        self.debugLog(u"validatePrefsConfigUi() method called.")

        error_msg_dict = indigo.Dict()

        # self.errorLog(u"Plugin configuration error: ")

        return True, valuesDict



    def setStatestonil(self, dev):

         self.debugLog(u'setStates to nil run')


    def refreshDataAction(self, valuesDict):
        """
        The refreshDataAction() method refreshes data for all devices based on
        a plugin menu call.
        """

        self.debugLog(u"refreshDataAction() method called.")
        self.refreshData()
        return True

    def refreshData(self):
        """
        The refreshData() method controls the updating of all plugin
        devices.
        """
        self.debugLog(u"refreshData() method called.")
        try:
            # Check to see if there have been any devices created.
            if indigo.devices.itervalues(filter="self"):
                self.debugLog(u"Updating data...")
                for dev in indigo.devices.itervalues(filter="self"):
                    self.refreshDataForDev(dev)
            else:
                indigo.server.log(u"No Client devices have been created.")
            return True
        except Exception as error:
            self.errorLog(u"Error refreshing devices. Please check settings.")
            self.errorLog(str(error.message))
            return False
    ## zonelist return



    def toggleDebugEnabled(self):
        """
        Toggle debug on/off.
        """
        self.debugLog(u"toggleDebugEnabled() method called.")
        if self.logLevel == logging.INFO:
            self.logLevel = logging.DEBUG
            self.indigo_log_handler.setLevel(self.logLevel)

            indigo.server.log(u'Set Logging to DEBUG')
        else:
            self.logLevel = logging.INFO
            indigo.server.log(u'Set Logging to INFO')
            self.indigo_log_handler.setLevel(self.logLevel)

        self.pluginPrefs[u"logLevel"] = self.logLevel
        return
## Triggers

    def triggerStartProcessing(self, trigger):
        self.logger.debug("Adding Trigger %s (%d) - %s" % (trigger.name, trigger.id, trigger.pluginTypeId))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.logger.debug("Removing Trigger %s (%d)" % (trigger.name, trigger.id))
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

    def triggerCheck(self, device, event, partition=0, idofevent=0):
        try:
            for triggerId, trigger in sorted(self.triggers.iteritems()):
                self.logger.debug("Checking Trigger %s (%s), Type: %s" % (trigger.name, trigger.id, trigger.pluginTypeId))

                if trigger.pluginTypeId=="partitionstatuschange" and event=="partitionstatuschange":
                    #self.logger.error("Trigger paritionStatusChange Found: Idofevent:"+str(idofevent))
                    #self.logger.error(str(trigger))
                    if str(idofevent) in trigger.pluginProps["paritionstatus"]:
                        self.logger.debug("Trigger being run: idofevent: " + str(idofevent) + " event: " + str(event) )
                        indigo.trigger.execute(trigger)
                if trigger.pluginTypeId=="bellstatuschange" and event=="bellstatuschange":
                    #self.logger.error("Trigger paritionStatusChange Found: Idofevent:"+str(idofevent))
                    #self.logger.error(str(trigger))
                    if str(idofevent) in trigger.pluginProps["bellstatus"]:
                        self.logger.debug("Trigger being run: idofevent: " + str(idofevent) + " event: " + str(event) )
                        indigo.trigger.execute(trigger)
                if trigger.pluginTypeId=="newtroublestatuschange" and event=="newtroublestatuschange":
                    #self.logger.error("Trigger paritionStatusChange Found: Idofevent:"+str(idofevent))
                    #self.logger.error(str(trigger))
                    if str(idofevent) in trigger.pluginProps["troublestatus"]:
                        self.logger.debug("Trigger being run: idofevent: " + str(idofevent) + " event: " + str(event) )
                        indigo.trigger.execute(trigger)
                if trigger.pluginTypeId == "failedCommand" and event == "failedCommand":
                    if trigger.pluginProps["zonePartition"] == int(partition):
                        self.logger.debug("\tExecuting Trigger %s (%d)" % (trigger.name, trigger.id))
                        indigo.trigger.execute(trigger)


                if trigger.pluginTypeId=="motion" and event=="motion":
                    if trigger.pluginProps["deviceID"] == str(device.id):
                        self.logger.debug("\tExecuting Trigger %s (%d)" % (trigger.name, trigger.id))
                        indigo.trigger.execute(trigger)
                if trigger.pluginTypeId=="alarmstatus" and event =="alarmstatus":
                    if trigger.pluginProps["zonePartition"] == int(partition):
                        if trigger.pluginProps["alarmstate"] == trigger.pluginProps["deviceID"]:
                            self.logger.debug("\tExecuting Trigger %s (%d)" % (trigger.name, trigger.id))
                            indigo.trigger.execute(trigger)

                    #self.logger.debug("\tUnknown Trigger Type %s (%d), %s" % (trigger.name, trigger.id, trigger.pluginTypeId))
            return

        except Exception as error:
            self.errorLog(u"Error Trigger. Please check settings.")
            self.errorLog(str(error.message))
            return False

