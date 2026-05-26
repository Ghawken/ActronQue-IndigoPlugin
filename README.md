![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# ActronQue — Indigo Plugin

[![Version](https://img.shields.io/badge/version-0.6.56-blue)](https://github.com/Ghawken/ActronQue-IndigoPlugin/releases)
[![Indigo](https://img.shields.io/badge/Indigo-2022.1%2B-green)](https://www.indigodomo.com)
[![Python](https://img.shields.io/badge/Python-3-yellow)](https://www.python.org)

> **Control. Automate. Integrate.**  
> Full Indigo home-automation control of your Actron Que ducted air-conditioning system via the cloud API.

---

## Overview

The **ActronQue Indigo Plugin** connects [Indigo Domotics](https://www.indigodomo.com) to your **Actron Que** ducted reverse-cycle air-conditioning system. Actron is an Australian manufacturer of premium AC systems — the Que is their flagship ducted model offering full zone control, variable fan speed, and cloud connectivity.

This plugin communicates with the **Actron Que cloud API** over HTTPS. An internet connection on the Indigo server is required — there is no local-only access method.

---

## Features

| Feature | Details |
|---------|---------|
| 🔌 **AC Power Control** | Turn the system on, off, or toggle from Indigo actions |
| 🏠 **Zone Control** | Enable / disable individual zones (up to 8) independently |
| 🌡️ **Live Zone Temperatures** | Per-zone temperature and humidity from wireless sensors |
| 🎯 **Setpoints & Modes** | Cool / Heat / Auto / Off with per-zone and system-wide setpoints |
| 💨 **Variable Fan Speed** | Auto / Low / Med / High — down to ~20%, near-silent operation |
| 😴 **Quiet Mode** | Toggle the system's low-noise Quiet Mode |
| ⚡ **Energy & Performance Data** | Compressor power, PWM, RPM, capacity, outdoor unit temperature |
| 🔔 **Alerts** | Clean filter, defrost, DRED, error codes |
| 📊 **Zone Open Percentage** | Damper position (0–100%) with visual circle images for control pages |
| 🔄 **Auto Status Updates** | Full system poll every ~30 seconds; immediate refresh after commands |

---

## Quick Start

1. **[Install](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Installation)** the plugin — double-click `ActronQUE.indigoPlugin`
2. Create an **Actron Que Main Device** in Indigo → enter your Actron account credentials
3. Click **Generate Zone Devices** — one device per zone is created automatically
4. Done — control your AC system from Indigo actions, triggers, and control pages

---

## Screenshots

| Main Device Setup | Main Device Status | Zone Device |
|:-----------------:|:-----------------:|:-----------:|
| ![Setup](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/QueMainSetup.png) | ![Status](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/QueMainStatus.png) | ![Zone](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/QueZone.png) |

---

## Available Actions

- **Turn Main Unit On / Off / Toggle**
- **Turn Zone On / Off / Toggle**
- **Set Fan Speed** — Auto / Low / Med / High
- **Turn Quiet Mode On / Off / Toggle**
- **Set Zone Cool / Heat Setpoint** (from a list, within zone limits)
- **Increase / Decrease Zone Cool Setpoint** (0.5 °C steps)
- **Increase / Decrease Zone Heat Setpoint** (0.5 °C steps)
- All standard **Indigo thermostat actions** (Set HVAC Mode, Set Setpoint, Increase/Decrease Setpoint, Request Status)

---

## Requirements

- **Indigo Domotics** 2022.1 or later
- **Actron Que** ducted AC system with cloud connectivity
- **Actron account** — same login as the Actron Que iOS/Android app
- **Internet access** on the Indigo server

---

## Wiki Documentation

Full documentation is available in the [GitHub Wiki](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki):

| Page | Description |
|------|-------------|
| [🏠 Home](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Home) | Overview, features, quick start |
| [📦 Installation](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Installation) | How to download, install, upgrade |
| [⚙️ Configuration](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Configuration) | Setting up credentials, generating zone devices |
| [🖥️ Devices](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Devices) | Main device and Zone device explained |
| [📊 Device States](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Device-States) | Complete reference of every Indigo device state |
| [▶️ Actions](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Actions) | All Action Group commands with examples |
| [🔄 Polling & Updates](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Polling-and-Updates) | How live data and commands work |
| [🔧 Plugin Preferences](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Plugin-Preferences) | Debug options and log levels |
| [🛠️ Troubleshooting](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Troubleshooting) | Common issues and solutions |
| [📋 Changelog](https://github.com/Ghawken/ActronQue-IndigoPlugin/wiki/Changelog) | Full version history |

---

## Plugin Details

| Property | Value |
|----------|-------|
| **Plugin ID** | `com.GlennNZ.indigoplugin.ActronQUE` |
| **Current Version** | 0.6.56 |
| **Author** | GlennNZ |
| **API** | `https://que.actronair.com.au` (cloud, HTTPS) |
| **Indigo API** | 3.0.0 |
| **Python** | 3 |

---

## Issues & Contributions

Found a bug or have a feature request? Please open an [issue on GitHub](https://github.com/Ghawken/ActronQue-IndigoPlugin/issues).

---

*Developed by GlennNZ — Indigo plugin for Actron Que ducted AC systems.*
