![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Devices

The plugin creates two types of Indigo devices — one per physical system and one per zone.

---

## Actron Que Main Device

**Device type ID:** `ActronQueMain`  
**Indigo type:** Thermostat

The Main device represents the **entire Actron Que AC system** — indoor unit, outdoor unit, and all system-wide settings. It is the top-level device that all zone devices link back to.

![Main Device Status](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/QueMainStatus.png)

### What it controls

| Control | Description |
|---------|-------------|
| Power (On/Off) | Turns the entire AC system on or off |
| HVAC Mode | Sets system mode: Cool / Heat / Auto / Off |
| Cool Setpoint | Master system cooling target temperature |
| Heat Setpoint | Master system heating target temperature |
| Fan Speed | Sets fan to Auto / Low / Medium / High |
| Quiet Mode | Enables/disables the low-noise operating mode |

### Indigo Thermostat Interface

The Main device supports the **standard Indigo thermostat controls**, meaning you can use all built-in Indigo thermostat actions directly:

- *Set HVAC Mode*
- *Set Cool/Heat Setpoint*
- *Increase/Decrease Cool/Heat Setpoint*
- *Request Status*

> **Note:** The standard Indigo fan mode control is **not supported** — use the dedicated *Set Fan Speed* action group instead.

### Display State

The device's display state in the Indigo device list is `deviceIsOnline` (True/False). This gives you immediate visibility of whether the AC system is reachable from the cloud.

### Authentication Flow

The plugin uses a two-step OAuth2-style flow:
1. POST credentials → receive a `pairingToken`
2. POST `pairingToken` as a refresh token → receive an `access_token` (Bearer)
3. All subsequent API calls use `Authorization: Bearer <access_token>`

The access token is stored in the device's plugin properties (not exposed in states). It is refreshed automatically every 24 hours or whenever an API call returns an authorisation error.

---

## Que AC Zone Device

**Device type ID:** `queZone`  
**Indigo type:** Thermostat

Each zone device represents **one physical zone** in your ducted system. Zones are created automatically by clicking **Generate Zone Devices** on the Main device.

![Zone Device](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/QueZone.png)

### What it controls

| Control | Description |
|---------|-------------|
| Zone On/Off | Enables or disables this zone's airflow |
| Zone Setpoints | Per-zone cool and heat target temperatures |
| Increase/Decrease Setpoint | Adjust zone setpoint by 0.5 °C increments |

### Zone vs Main Mode

- A zone's **HVAC mode** reflects the main system mode when the zone is enabled
- Setting a zone to **Off** disables it (closes the damper) — it does not turn off the whole system
- You cannot change the main system mode (Heat → Cool) via a zone device — use the Main device

### Zone Setpoint Constraints

Each zone has minimum and maximum allowable setpoints:

| State | Description |
|-------|-------------|
| `MinHeatSetpoint` | Lowest allowed heat setpoint for this zone |
| `MaxHeatSetpoint` | Highest allowed heat setpoint for this zone |
| `MinCoolSetpoint` | Lowest allowed cool setpoint for this zone |
| `MaxCoolSetpoint` | Highest allowed cool setpoint for this zone |

The plugin enforces these limits when processing setpoint actions — attempts to exceed the range are logged and silently clamped.

### Zone Identification

Each zone device stores:

| State | Description |
|-------|-------------|
| `zoneName` | Name of the zone as configured in the Actron app |
| `zoneNumber` | Zone index (1–8) |
| `deviceMasterController` | Indigo device ID of the parent Main device |

Zones are matched to the API data **by number** (not name), so renaming a zone in Indigo or in the Actron app does not break the link.

### Zone Position & Open State

The Actron system reports damper position as a raw integer (0–20). The plugin converts this:

| Raw Value | `zonePosition` | `zoneisOpen` | `zonePercentageOpen` |
|-----------|---------------|-------------|----------------------|
| 0 | 0 | False | 0% |
| 1 | 1 | True | 5% |
| 10 | 10 | True | 50% |
| 20 | 20 | True | 100% |

> `zoneisEnabled` reflects whether the user has enabled the zone; `zoneisOpen` reflects whether airflow is actually flowing (the damper may be closed even if enabled, e.g. when the zone has reached its setpoint).

### Zone Percentage Circles

The plugin ships with a full set of pre-rendered **percentage circle images** (`circle+0.png` through `circle+100.png`) that you can use on Indigo control pages to display zone open percentage visually.

---

## Device Relationships

```
Actron Que Main Device (ActronQueMain)
│
├── Que Zone:1:Bedroom    (queZone) ─ deviceMasterController → Main Device ID
├── Que Zone:2:Living     (queZone) ─ deviceMasterController → Main Device ID
├── Que Zone:3:Kitchen    (queZone) ─ deviceMasterController → Main Device ID
├── ...
└── Que Zone:8:Study      (queZone) ─ deviceMasterController → Main Device ID
```

All zone devices are placed in the **same Indigo folder** as the Main device during creation. You can freely move them afterwards.

---

## Next Step

➡️ [View all device states →](Device-States)
