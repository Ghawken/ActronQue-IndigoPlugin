#! /usr/bin/env python2.6
# -*- coding: utf-8 -*-

"""
Author: GlennNZ

"""

import datetime
import time as t
import urllib2
import os
import shutil
import logging
import sys
import requests
from collections import namedtuple
import json



try:
    import indigo
except:
    pass

################################################################################
kHvacModeEnumToStrMap = {
	indigo.kHvacMode.Cool				: u"cool",
	indigo.kHvacMode.Heat				: u"heat",
	indigo.kHvacMode.HeatCool			: u"auto",
	indigo.kHvacMode.Off				: u"off",
	indigo.kHvacMode.ProgramHeat		: u"program heat",
	indigo.kHvacMode.ProgramCool		: u"program cool",
	indigo.kHvacMode.ProgramHeatCool	: u"program auto"
}

kFanModeEnumToStrMap = {
	indigo.kFanMode.AlwaysOn			: u"always on",
	indigo.kFanMode.Auto				: u"auto"
}

def _lookupActionStrFromHvacMode(hvacMode):
	return kHvacModeEnumToStrMap.get(hvacMode, u"unknown")

def _lookupActionStrFromFanMode(fanMode):
	return kFanModeEnumToStrMap.get(fanMode, u"unknown")

################################################################################

class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        try:
            self.logLevel = int(self.pluginPrefs[u"showDebugLevel"])
        except:
            self.logLevel = logging.INFO

        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))

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

        self.connected = False
        self.deviceUpdate = False
        self.devicetobeUpdated =''

        self.ipaddress = self.pluginPrefs.get('ipaddress', '')
        self.port = self.pluginPrefs.get('port', 10000)
        self.ip150password = self.pluginPrefs.get('ip150password', 'paradox')
        self.pcpassword = self.pluginPrefs.get('pcpassword', 1234)

        self.labelsdueupdate = True
        self.debug1 = self.pluginPrefs.get('debug1', False)
        self.debug2 = self.pluginPrefs.get('debug2', False)
        self.debug3 = self.pluginPrefs.get('debug3', False)
        self.debug4 = self.pluginPrefs.get('debug4',False)
        self.debug5 = self.pluginPrefs.get('debug5', False)

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
            self.ipaddress = valuesDict.get('ipaddress', '')
            # self.logger.error(unicode(valuesDict))
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
            self.logger.debug(u"Debugging on (Level: {0})".format(self.logLevel))

        return True

    # Start 'em up.

    # Shut 'em down.
    def deviceStopComm(self, dev):

        self.debugLog(u"deviceStopComm() method called.")
        #indigo.server.log(u"Stopping  device: " + dev.name)
        if dev.deviceTypeId == 'ActronQueMain':
            dev.updateStateOnServer('deviceIsOnline', value=False)




    def forceUpdate(self):
        self.updater.update(currentVersion='0.0.0')

    def checkForUpdates(self):
        if self.updater.checkForUpdate() == False:
            indigo.server.log(u"No Updates are Available")

    def updatePlugin(self):
        self.updater.update()

    def runConcurrentThread(self):

        updatemaindevice = t.time() + 60*60*70

        try:
            # check once on statup
            # also check zones
            self.checkMainDevices()  #
            while True:
                self.sleep(5)
                for dev in indigo.devices.itervalues(filter="self"):
                    if dev.deviceTypeId == "ActronQueMain":
                        accessToken = dev.pluginProps['accessToken']
                        serialNo = dev.pluginProps['serialNo']
                        if accessToken == "" or accessToken == None:
                            self.logger.info("Try again later, once Main device setup and connected")
                            self.logger.error("Probably expired token")
                        else:
                            zonenames = self.getSystemStatus(dev, accessToken, serialNo)
                self.sleep(60)
                if t.time() > updatemaindevice:
                    self.logger.info("Updating Access Token as 24 hours has passed")
                    self.checkMainDevices()
                    updatemaindevice = t.time() + 60 * 60 * 24

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

                    serialNo = self.getACsystems(accessToken)
                    if serialNo != "":
                        localPropscopy['serialNo']=serialNo
                        self.logger.debug("Updated device pluginProps with Serial Number:")
                        self.logger.debug("Device :"+dev.name+" PluginProps:")
                        dev.updateStateOnServer('serialNumber', value=serialNo )
                    else:
                        self.logger.info("Unable to get Serial Number, check username, Password")
                        return
                    ## update system status
                    dev.replacePluginPropsOnServer(localPropscopy)

                    zonenames = self.getSystemStatus(dev, accessToken, serialNo)
                    localPropscopy['zoneNames'] = zonenames
                    dev.replacePluginPropsOnServer(localPropscopy)
                    self.logger.debug("Device :" + dev.name + " PluginProps:")
                    self.logger.debug(unicode(dev.pluginProps))

    def getACsystems(self,accessToken):

        try:
            if accessToken == None or accessToken=="":
                self.logger.debug("Access token nil.  Aborting")
                return

            self.logger.debug( "Trying to using access Token %s" % accessToken )
            #self.logger.info("Connecting to %s" % address)
            url = 'https://que.actronair.com.au/api/v0/client/ac-systems'
            headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au','User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0',
                       'Authorization':'Bearer '+accessToken                       }
           # payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}

            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                self.logger.debug(unicode(r.text))
                jsonResponse = r.json()
                if '_embedded' in jsonResponse:
                    if 'ac-system' in jsonResponse['_embedded']:
                        if 'serial' in jsonResponse['_embedded']['ac-system'][0]:
                            self.logger.debug(jsonResponse['_embedded']['ac-system'][0])
                            serialNumber = jsonResponse['_embedded']['ac-system'][0]['serial']
                            self.logger.debug("Serial Number:"+unicode(serialNumber))
                            return serialNumber
            else:
                self.logger.error(unicode(r.text))
                return

        except Exception, e:
            self.logger.exception("Error getting AC systems : " + repr(e))
            self.logger.debug("Error connecting" + unicode(e.message))
            self.connected = False

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
        self.logger.debug(unicode(valuesDict))
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

        except:
            self.logger.exception(u'Caught Exception creating Que Zone Devices')
            return

    def getSystemStatus(self, device, accessToken, serialNo):

        try:
            if accessToken == None or accessToken=="":
                self.logger.debug("Access token nil.  Aborting")
                return

            self.logger.debug("Getting System Status for System Serial No %s" % serialNo)
            # self.logger.info("Connecting to %s" % address)
            url = 'https://que.actronair.com.au/api/v0/client/ac-systems/status/latest?serial='+str(serialNo)
            headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au',
                       'User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0',
                       'Authorization': 'Bearer ' + accessToken}
            # payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                self.logger.info("Error Message from get System Status")
                self.logger.debug(unicode(r.text))
                return

# serialNumber = jsonResponse['_embedded']['ac-system'][0]['serial']

            self.logger.debug(unicode(r.text))
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
            CompressorMode =""
            FanMode = ""
            WorkingMode = ""
            SystemSetpoint_Cool = float(0)
            SystemSetpoint_Heat = float(0)
            MainStatus = indigo.kHvacMode.Off
            zonenames = ""

            if 'lastKnownState' in jsonResponse:
                if "<"+serialNo.upper()+">" in jsonResponse['lastKnownState']:
                    self.logger.debug(unicode(jsonResponse['lastKnownState']["<"+serialNo.upper()+">"]))
                if "AirconSystem" in jsonResponse['lastKnownState']:
                    if 'IndoorUnit' in jsonResponse['lastKnownState']['AirconSystem']:
                        indoorModel = jsonResponse['lastKnownState']['AirconSystem']['IndoorUnit']["NV_DeviceID"]
                if 'Alerts' in jsonResponse['lastKnownState']:
                    alertCF = jsonResponse['lastKnownState']['Alerts']['CleanFilter']
                    alertDRED = jsonResponse['lastKnownState']['Alerts']['DRED']
                    alertDefrosting = jsonResponse['lastKnownState']['Alerts']['Defrosting']
                if 'LiveAircon' in jsonResponse['lastKnownState']:
                    if 'FanPWM' in jsonResponse['lastKnownState']['LiveAircon']:
                        fanPWM = jsonResponse['lastKnownState']['LiveAircon']['FanPWM']
                    if 'FanRPM' in jsonResponse['lastKnownState']['LiveAircon']:
                        fanRPM = jsonResponse['lastKnownState']['LiveAircon']['FanRPM']
                    if 'IndoorUnitTemp' in jsonResponse['lastKnownState']['LiveAircon']:
                        IndoorUnitTemp = float(jsonResponse['lastKnownState']['LiveAircon']['IndoorUnitTemp'])
                    if 'OutdoorUnit' in jsonResponse['lastKnownState']['LiveAircon']:
                        if 'AmbTemp' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            OutdoorUnitTemp = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['AmbTemp']
                        if 'CompPower' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            CompPower = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['CompPower']
                        if 'CompRunningPWM' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            CompRunningPWM = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['CompRunningPWM']
                        if 'CompSpeed' in jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']:
                            CompSpeed = jsonResponse['lastKnownState']['LiveAircon']['OutdoorUnit']['CompSpeed']
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
                    if 'TemperatureSetpoint_Cool_oC' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        SystemSetpoint_Cool = jsonResponse['lastKnownState']['UserAirconSettings']['TemperatureSetpoint_Cool_oC']
                    if 'TemperatureSetpoint_Heat_oC' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        SystemSetpoint_Heat = jsonResponse['lastKnownState']['UserAirconSettings']['TemperatureSetpoint_Heat_oC']
                    if 'EnabledZones' in jsonResponse['lastKnownState']['UserAirconSettings']:
                        #self.logger.error(unicode(jsonResponse['lastKnownState']['UserAirconSettings']['EnabledZones']))
                        listzonesopen = jsonResponse['lastKnownState']['UserAirconSettings']['EnabledZones']
                        self.logger.debug(u"List of Zone Status:"+unicode(listzonesopen))
                if 'RemoteZoneInfo' in jsonResponse['lastKnownState']:

                    for x in range (0,8):
                        ## go through all zones
                        self.logger.debug("Zone Number:"+unicode(x))
                        self.logger.debug(jsonResponse['lastKnownState']['RemoteZoneInfo'][x])
                        zonenames = zonenames +jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['NV_Title'] + ","
                        self.logger.debug(unicode(zonenames))

                        for dev in indigo.devices.itervalues('self.queZone'):
                            # go through all devices, and compare to 8 zones returned.
                            if dev.states["zoneName"] == jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['NV_Title']:

                                canoperate = False
                                livehumidity = float(0)
                                liveTemphys = float(0)
                                livetemp = float(0)
                                tempsetpointcool = float(0)
                                tempsetpointheat = float(0)
                                ZonePosition = int(0)
                                sensorbattery = int(0)
                                sensorid =""
                                ZoneStatus = indigo.kHvacMode.Off  ## Cool, HeatCool, Heat, Off
                                zoneOpen = False

                                if 'CanOperate' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    canoperate = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['CanOperate']
                                if 'LiveHumidity_pc' in jsonResponse['lastKnownState']['RemoteZoneInfo'][x]:
                                    livehumidity = jsonResponse['lastKnownState']['RemoteZoneInfo'][x]['LiveHumidity_pc']
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

                                if listzonesopen[x]==True:
                                    if CompressorMode=="HEAT":
                                        ZoneStatus = indigo.kHvacMode.Heat
                                    else:
                                        ZoneStatus = indigo.kHvacMode.Cool
                                else:
                                    ZoneStatus = indigo.kHvacMode.Off

                                if int(ZonePosition) ==0:
                                    zoneOpen = False
                                else:
                                    zoneOpen = True

                                listzonetemps.append(livetemp)
                                listzonehumidity.append(livehumidity)
                                zoneStatelist =[
                                    {'key': 'canOperate', 'value': canoperate},
                                    {'key': 'currentTemp', 'value': livetemp},
                                    {'key': 'temperatureInput1', 'value': livetemp},
                                    {'key': 'humidityInput1', 'value': livehumidity},
                                    {'key': 'currentTempHystersis', 'value': liveTemphys},
                                    {'key': 'currentHumidity', 'value': livehumidity},
                                    {'key': 'sensorBattery', 'value': sensorbattery},
                                    {'key': 'sensorId', 'value': sensorid},
                                    {'key': 'zoneisEnabled', 'value': listzonesopen[x]},
                                    {'key': 'zoneisOpen', 'value': zoneOpen},
                                    {'key': 'hvacOperationMode', 'value': ZoneStatus},
                                    {'key': 'TempSetPointCool', 'value': tempsetpointcool},
                                    {'key': 'TempSetPointHeat', 'value': tempsetpointheat},
                                    {'key': 'zonePosition', 'value': ZonePosition},
                                    {'key': 'deviceMasterController', 'value': device.id},
                                #    {'key': 'setpointHeat', 'value': tempsetpointheat}
                                ]

                                dev.updateStatesOnServer(zoneStatelist)

            if CompressorMode == "HEAT":
                MainStatus = indigo.kHvacMode.Heat
            elif CompressorMode =="COOL" :
                MainStatus = indigo.kHvacMode.Cool
            averageTemp = 0
            averageHum = 0
            tempInputsAll = []
            humdInputAll = []
            if len(listzonetemps) > 1:
                tempInputsAll = str(','.join(map(str, listzonetemps)) )
                averageTemp = reduce(lambda a,b:a+b, listzonetemps) / len(listzonetemps)
                humdInputsAll = str(','.join(map(str, listzonehumidity)))
                averageHum = reduce(lambda a, b: a + b, listzonehumidity) / len(listzonehumidity)

            self.logger.debug(unicode(tempInputsAll))
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
                {'key': 'outdoorUnitCompSpeed', 'value': CompSpeed},
                {'key': 'outdoorUnitCompMode', 'value': CompressorMode},
                {'key': 'hvacOperationMode', 'value': MainStatus},
                {'key': 'temperatureInput1', 'value': averageTemp},
                {'key': 'humidityInput1', 'value': averageHum},
                {'key': 'fanSpeed', 'value': FanMode},
                {'key': 'outdoorUnitFanSpeed', 'value': outdoorFanSpeed},
            ]

            device.updateStatesOnServer(stateList)
            return zonenames



        except Exception, e:
            self.logger.exception("Error getting System Status : " + repr(e))
            self.logger.debug("Error connecting" + unicode(e.message))



    def getPairingToken(self,username, password):

        try:
            self.logger.info( "Trying to connect %s" % username )
            #self.logger.info("Connecting to %s" % address)
            url = 'https://que.actronair.com.au/api/v0/client/user-devices'
            headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au','User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0'}
            payload = {'username':username, 'password':password, 'client':'ios', 'deviceUniqueIdentifier':'IndigoPlugin'}

            r = requests.post(url, data=payload, headers=headers, timeout=10)

            pairingToken =""
            if r.status_code==200:
                self.logger.debug(unicode(r.text))
                jsonResponse = r.json()
                if 'pairingToken' in jsonResponse:
                    self.logger.debug(jsonResponse['pairingToken'])
                    pairingToken = jsonResponse['pairingToken']
            else:
                self.logger.error(unicode(r.text))
                return ""

            ## pairingToken should exists
            if pairingToken=="":
                self.logger.info("No pairing Token received?  Ending.")
                return ""

            ## now get bearer token
            ## will need to save these for each main device

            payload2 = {'grant_type':'refresh_token', 'refresh_token':pairingToken, 'client_id':'app'}
            url2 = 'https://que.actronair.com.au/api/v0/oauth/token'

            newr = requests.post(url2, data=payload2, headers=headers,timeout=10)

            accessToken = ""
            if newr.status_code==200:
                self.logger.debug(unicode(newr.text))
                jsonResponse = newr.json()
                if 'access_token' in jsonResponse:
                    self.logger.debug(jsonResponse['access_token'])
                    accessToken = jsonResponse['access_token']
            ## pairingToken should exists
            if accessToken=="":
                self.logger.info("No Access Token received?  Ending.")
                return ""

            return accessToken

        except Exception, e:
            self.logger.debug("Error getting Pairing Token : " + repr(e))
            self.logger.debug( "Error connecting"+unicode(e.message))
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
        if self.sendCommand(accessToken, serialNo, "UserAirconSettings.FanMode", str(fanspeed)):
            sendSuccess = True
            maindevice.updateStateOnServer("fanSpeed", fanspeed)
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
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", True):
                    self.logger.info("Turning on Zone number "+unicode(zoneNumber))
                    sendSuccess = True
                    zonedevice.updateStateOnServer("hvacOperationMode", mainDevicehvacMode)
                else:
                    self.logger.info("Error completing command, aborted")
            elif zoneonoroff == "OFF":  ## need to turn AC off
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", False):
                    self.logger.info("Turning off Zone number "+unicode(zoneNumber))
                    zonedevice.updateStateOnServer("hvacOperationMode", indigo.kHvacMode.Off)
                    sendSuccess = True
                else:
                    self.logger.info("Error completing command, aborted")
            elif zonedevice.states['hvacOperationMode'] != indigo.kHvacMode.Off and (zoneonoroff == "OFF" or zoneonoroff=="TOGGLE"):
                ## DEVICE IS ON - COOL or Heat and wants to go off or toggle
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", False):
                    self.logger.info("Turning off Zone number "+unicode(zoneNumber))
                    zonedevice.updateStateOnServer("hvacOperationMode", indigo.kHvacMode.Off)
                    sendSuccess = True
                else:
                    self.logger.info("Error completing command, aborted")


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
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.isOn", True):
                    self.logger.info("Turning on AC System.")
                    sendSuccess = True
                else:
                    self.logger.info("Error completing command, aborted")
                    return
            elif onoroff == "OFF":  ## need to turn AC off
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.isOn", False):
                    self.logger.info("Turning off AC System")
                    sendSuccess = True
                else:
                    self.logger.info("Error completing command, aborted")
                    return
                ## only for main device
            elif mainDevicehvacMode != indigo.kHvacMode.Off and (onoroff == "OFF" or onoroff=="TOGGLE"):
                ## DEVICE IS ON - COOL or Heat and wants to go off or toggle
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.isOn", False):
                    self.logger.info("Turning off AC System.")
                    sendSuccess = True
                else:
                    self.logger.info("Error completing command, aborted")
                    return

        if sendSuccess:
            # If success then log that the command was successfully sent.
            indigo.server.log(u"Sent \"%s\" mode change to %s" % (maindevice.name, onoroff))
            if "hvacOperationMode" in maindevice.states:
                if onoroff == "OFF":
                    maindevice.updateStateOnServer("hvacOperationMode", indigo.kHvacMode.Off)
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
                zonenames = self.getSystemStatus(dev, accessToken, serialNo)
        else: ## if zonenames - need to get device of Main
            maindevice = indigo.devices[int(dev.states["deviceMasterController"])]
            accessToken = maindevice.pluginProps['accessToken']
            serialNo = maindevice.pluginProps['serialNo']
            if accessToken == "" or serialNo == "":
                self.logger.debug("Try again later, once Main device setup and connected")
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                self.checkMainDevices()
            else:
                zonenames = self.getSystemStatus(maindevice, accessToken, serialNo)
    ######################
    def returnmainAccessSerial(self,dev):
        self.logger.debug("Figuring out Access Token from Hardware")
        if dev.deviceTypeId == "ActronQueMain":
            accessToken = dev.pluginProps['accessToken']
            serialNo = dev.pluginProps['serialNo']
            if accessToken == "" or serialNo == "":
                self.logger.debug("Try again later, once Main device setup and connected")
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                return "error","error"
            else:
                return accessToken,serialNo,dev

        else: ## if zonenames - need to get device of Main
            maindevice = indigo.devices[int(dev.states["deviceMasterController"])]
            accessToken = maindevice.pluginProps['accessToken']
            serialNo = maindevice.pluginProps['serialNo']
            if accessToken == "" or serialNo == "":
                self.logger.debug("Try again later, once Main device setup and connected")
                self.logger.debug("Probably expired token.  Running Access Token Recreate")
                return "error","error"
            else:
                return accessToken, serialNo, maindevice

    # Process action request from Indigo Server to change main thermostat's main mode.
    def _handleChangeHvacModeAction(self, dev, newHvacMode):
        # Command hardware module (dev) to change the thermostat mode here:
        # ** IMPLEMENT ME **
        sendSuccess = False  # Set to False if it failed.
        actionStr = _lookupActionStrFromHvacMode(newHvacMode)

        accessToken, serialNo, maindevice = self.returnmainAccessSerial(dev)
        if accessToken == "error" or serialNo=="error":
            self.logger.info("Unable to complete accessToken or Serial No issue")
            return

        mainDevicehvacMode = maindevice.states['hvacOperationMode']

        ## if device asked to hardward control main - then turn on main, and change mode, or turn off
        if dev.deviceTypeId  =="ActronQueMain":
            if maindevice.states['hvacOperationMode'] == indigo.kHvacMode.Off and newHvacMode != indigo.kHvacMode.Off:
                ## need to turn on and change mode
                if self.sendCommand(accessToken, serialNo,"UserAirconSettings.isOn", True):
                    self.logger.info("Turning on AC System, prior to changing mode")
                else:
                    self.logger.info("Error completing command, aborted")
                    return
            elif newHvacMode == indigo.kHvacMode.Off: ## need to turn AC off
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.isOn", False):
                    self.logger.info("Turning off AC System")
                else:
                    self.logger.info("Error completing command, aborted")
                    return
            ## only for main device
            sendSuccess = self.sendCommand(accessToken, serialNo, "UserAirconSettings.Mode", str(actionStr).upper())

        if dev.deviceTypeId == "queZone":
            ## if a zone device needs different command
            ## probably best to be OFF or anything else
            zoneNumber = str(int(dev.states['zoneNumber'])-1)  # counts zones from zero
            if dev.states['hvacOperationMode'] == indigo.kHvacMode.Off and newHvacMode != indigo.kHvacMode.Off:
                ## need to turn on Zone
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", True):
                    self.logger.info("Turning on Zone number "+unicode(zoneNumber))
                    newHvacMode = mainDevicehvacMode
                    actionStr = _lookupActionStrFromHvacMode(mainDevicehvacMode)
                    sendSuccess = True
                else:
                    self.logger.info("Error completing command, aborted")
            elif newHvacMode == indigo.kHvacMode.Off:  ## need to turn AC off
                if self.sendCommand(accessToken, serialNo, "UserAirconSettings.EnabledZones["+zoneNumber+"]", False):
                    self.logger.info("Turning off Zone number "+unicode(zoneNumber))
                    sendSuccess = True
                else:
                    self.logger.info("Error completing command, aborted")

        if sendSuccess:
            # If success then log that the command was successfully sent.
            indigo.server.log(u"sent \"%s\" mode change to %s" % (dev.name, actionStr))
            # And then tell the Indigo Server to update the state.
            if "hvacOperationMode" in dev.states:
                dev.updateStateOnServer("hvacOperationMode", newHvacMode)
        else:
            # Else log failure but do NOT update state on Indigo Server.
            indigo.server.log(u"send \"%s\" mode change to %s failed" % (dev.name, actionStr), isError=True)

    ######################
    # Process action request from Indigo Server to change thermostat's fan mode.
    def _handleChangeFanModeAction(self, dev, newFanMode):
        # Command hardware module (dev) to change the fan mode here:
        # ** IMPLEMENT ME **
        sendSuccess = True  # Set to False if it failed.

        self.logger.info("Change Fan Mode unsupported currently")
        return

    ######################
    # Process action request from Indigo Server to change a cool/heat setpoint.
    def _handleChangeSetpointAction(self, dev, newSetpoint, logActionName, stateKey):
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
            self.logger.info("Not support for Zone devices unfortunately")
            return


            ## need to turn on and change mode
        if stateKey == u"setpointCool":
            sendSuccess = self.sendCommand(accessToken, serialNo, "UserAirconSettings.TemperatureSetpoint_Cool_oC", newSetpoint)


        elif stateKey == u"setpointHeat":
            # Command hardware module (dev) to change the heat setpoint to newSetpoint here:
            # ** IMPLEMENT ME **
            sendSuccess = self.sendCommand(accessToken, serialNo, "UserAirconSettings.TemperatureSetpoint_Heat_oC", newSetpoint)


        if sendSuccess:
            # If success then log that the command was successfully sent.
            indigo.server.log(u"sent \"%s\" %s to %.1f°" % (dev.name, logActionName, newSetpoint))

            # And then tell the Indigo Server to update the state.
            if stateKey in dev.states:
                dev.updateStateOnServer(stateKey, newSetpoint)
        else:
            # Else log failure but do NOT update state on Indigo Server.
            indigo.server.log(u"send \"%s\" %s to %.1f° failed" % (dev.name, logActionName, newSetpoint), isError=True)

    ########################################
    def sendCommand(self, accessToken, serialNo, commandtype, commandbody):
        try:
            self.logger.debug("Sending System Command for System Serial No %s" % serialNo)
            self.logger.debug("Sending Command "+unicode(commandtype)+" and commandbody:"+unicode(commandbody))

            # self.logger.info("Connecting to %s" % address)
            url = 'https://que.actronair.com.au/api/v0/client/ac-systems/cmds/send?serial='+str(serialNo)
            headers = {'Host': 'que.actronair.com.au', 'Accept': '*/*', 'Accept-Language': 'en-au',
                       'User-Agent': 'nxgen-ios/1214 CFNetwork/976 Darwin/18.2.0',
                       'Authorization': 'Bearer ' + accessToken}
            payload = {"command": { commandtype : commandbody, "type":"set-settings"}}

            self.logger.debug(unicode(payload))
            r = requests.post(url, headers=headers,json=payload, timeout=10)
            self.logger.debug(r.text)
            if r.status_code != 200:
                self.logger.info("Error Message from get System Status.  Rerunning Token check.")
                self.logger.debug(unicode(r.text))
                # Authorisation may have failed/taken over
                self.checkMainDevices()
                return False
            return True
        except requests.Timeout:
            self.logger.info("Request timedout to que.actron.com.au")
            self.sleep(1)
            return False

        except:
            self.logger.exception("Exception in send Command")
            return False

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.debugLog(u"validateDeviceConfigUi called")
        # User choices look good, so return True (client will then close the dialog window).
        return (True, valuesDict)

    def deviceStartComm(self, device):
        self.logger.debug(u"deviceStartComm called for " + device.name)
        device.stateListOrDisplayStateIdChanged()
        if device.deviceTypeId == 'ActronQueMain':
            device.updateStateOnServer('deviceIsOnline', value=True)
        newProps = device.pluginProps
        newProps["NumHumidityInputs"]=1
        newProps["ShowCoolHeatEquipmentStateUI"]= True
        newProps["SupportsHvacFanMode"] = False
        if device.deviceTypeId == "queZone":
            newProps["SupportsCoolSetpoint"] = False
            newProps["SupportsHeatSetpoint"] = False

        device.replacePluginPropsOnServer(newProps)
##
    def generateLabels(self, device,valuesDict, somethingunused):
        self.logger.info("Updating Zone and other Labels")
        self.labelsdueupdate = True
        return

    def shutdown(self):

         self.debugLog(u"shutdown() method called.")

    def startup(self):

        self.debugLog(u"Starting Plugin. startup() method called.")

        # See if there is a plugin update and whether the user wants to be notified.

        # Attempt Socket Connection here


    ## Motion Detected




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
            self.errorLog(unicode(error.message))
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
                    #self.logger.error("Trigger paritionStatusChange Found: Idofevent:"+unicode(idofevent))
                    #self.logger.error(unicode(trigger))
                    if str(idofevent) in trigger.pluginProps["paritionstatus"]:
                        self.logger.debug("Trigger being run: idofevent: " + unicode(idofevent) + " event: " + unicode(event) )
                        indigo.trigger.execute(trigger)
                if trigger.pluginTypeId=="bellstatuschange" and event=="bellstatuschange":
                    #self.logger.error("Trigger paritionStatusChange Found: Idofevent:"+unicode(idofevent))
                    #self.logger.error(unicode(trigger))
                    if str(idofevent) in trigger.pluginProps["bellstatus"]:
                        self.logger.debug("Trigger being run: idofevent: " + unicode(idofevent) + " event: " + unicode(event) )
                        indigo.trigger.execute(trigger)
                if trigger.pluginTypeId=="newtroublestatuschange" and event=="newtroublestatuschange":
                    #self.logger.error("Trigger paritionStatusChange Found: Idofevent:"+unicode(idofevent))
                    #self.logger.error(unicode(trigger))
                    if str(idofevent) in trigger.pluginProps["troublestatus"]:
                        self.logger.debug("Trigger being run: idofevent: " + unicode(idofevent) + " event: " + unicode(event) )
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
            self.errorLog(unicode(error.message))
            return False

