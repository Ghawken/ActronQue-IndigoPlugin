![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# ActronQue Indigo Plugin

> **Control. Automate. Integrate.**  
> Full Indigo home-automation control of your Actron Que ducted air-conditioning system via the cloud API.

---

## Overview

The **ActronQue Indigo Plugin** connects your [Indigo Domotics](https://www.indigodomo.com) home-automation system to your **Actron Que** ducted reverse-cycle air-conditioning system.

Actron is an Australian manufacturer of premium air-conditioning systems. The **Que** is their flagship ducted system offering complete zone control, variable fan speed, and cloud-based remote access.

This plugin accesses the **Actron Que web-based cloud API** to read status and send commands. There is **no local-only control** method available — an internet connection is required.

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🔌 **AC Power Control** | Turn the entire system on, off, or toggle |
| 🏠 **Zone Control** | Enable / disable individual zones independently |
| 🌡️ **Zone Temperatures** | Live temperature readings from every zone sensor |
| 🎯 **Setpoints & Modes** | Cool / Heat / Auto / Off with individual zone setpoints |
| 💨 **Fan Speed Control** | Set fan speed: Auto, Low, Medium, High |
| 😴 **Quiet Mode** | Toggle the system's Quiet Mode on/off |
| ⚡ **Energy Monitoring** | Compressor power, PWM, RPM, capacity readings |
| 🔔 **Live Status & Alerts** | Online/offline status, clean filter, defrost, DRED alerts |

---

## What the Plugin Creates

When set up, the plugin creates:

- **1 × Actron Que Main Device** — represents the entire AC system (thermostat type)
- **Up to 8 × Que Zone Devices** — one per configured zone (thermostat type)

Both device types implement the standard Indigo thermostat interface so they work with any built-in thermostat controls and actions.

---

## Wiki Pages

| Page | Description |
|------|-------------|
| [Installation](Installation) | Download and install the plugin |
| [Configuration](Configuration) | Set up the Main device and generate zones |
| [Devices](Devices) | Main device and Zone device explained |
| [Device States](Device-States) | Complete reference of every state |
| [Actions](Actions) | All available Action Group commands |
| [Polling & Updates](Polling-and-Updates) | How the plugin fetches live data |
| [Plugin Preferences](Plugin-Preferences) | Debug options and log levels |
| [Troubleshooting](Troubleshooting) | Common problems and solutions |
| [Changelog](Changelog) | Full version history |

---

## Requirements

- **Indigo Domotics** 2022.1 or later (Indigo 8+)
- **Actron Que** ducted AC system with cloud connectivity
- **Actron account** (username + password used with the Actron Que app)
- **Internet connection** on the Indigo server (cloud API only — no local access)

---

## Quick Start

1. [Install the plugin](Installation)
2. Create an **Actron Que Main Device** in Indigo
3. Enter your Actron account credentials
4. Click **Generate Zone Devices**
5. Done — all zones appear as individual Indigo devices

---

## Plugin Details

| Property | Value |
|----------|-------|
| **Plugin ID** | `com.GlennNZ.indigoplugin.ActronQUE` |
| **Bundle Name** | `ActronQUE` |
| **Current Version** | 0.6.56 |
| **Author** | GlennNZ |
| **API Endpoint** | `https://que.actronair.com.au` |
| **Repository** | [GitHub](https://github.com/Ghawken/ActronQue-IndigoPlugin) |

---

*Plugin developed by GlennNZ — contributions and issues welcome on [GitHub](https://github.com/Ghawken/ActronQue-IndigoPlugin/issues).*
