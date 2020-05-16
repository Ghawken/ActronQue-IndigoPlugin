# Actron Que AC IndigoPlugin

![](https://github.com/Ghawken/ActronQue-IndigoPlugin/blob/master/ActronQUE.indigoPlugin/Contents/Resources/icon400.png?raw=true)

Indigodomo Plugin for Actron Que Ducted AC Sytems

Actron is a Australian manufactor of AC systems.  The Que system is their premiere ducted offering.  Its offers "best in world" Air Conditioning.  The aim of this plugin is to control and interface with the Que API.  

Some features include complete variable fan speed of both internal and external units (down to 20% fanspeed), meaning that when most zones are off a fraction of power is used and both internal and external boxes are practically silent. 

This plugin access Actron QUE Web Based API to update/control your system.

It is different to some of my previous plugins - because Web based/Internet API access is needed.
There is no local control method only.

Usage

Install

Create Actron Main Que Device.
Enter Actron Account Details.

![](https://github.com/Ghawken/ActronQue-IndigoPlugin/blob/master/ActronQUE.indigoPlugin/Contents/Resources/QueMainSetup.png?raw=true)


Press Create Zone Devices
8 Zone devices will be create in the same directory as main device

You will be able to access multiple status from both the main Que device, including power usage, sound frequency.
Temperature readings from each zone are also accessible.

![](https://github.com/Ghawken/ActronQue-IndigoPlugin/blob/master/ActronQUE.indigoPlugin/Contents/Resources/QueMainStatus.png?raw=true)

![](https://github.com/Ghawken/ActronQue-IndigoPlugin/blob/master/ActronQUE.indigoPlugin/Contents/Resources/QueZone.png?raw=true)



Most of the relevant Indigo thermostat controls function
eg. Increase set-point, decrease
Change Mode Heat/Cool/Off

There are two additional action groups to turn a zone on or off
& to change fan speed.

Some of the control options vary depending whether targetting a zone or main controller.
Can't change main mode (heat -> cool) via zone for example.  

Early release, but as I am increasingly finding - often just runs without problem for long period so never actually update/change hence the release

Cheers

