![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Actions

The plugin exposes dedicated Action Group actions for controlling the AC system, in addition to the standard Indigo thermostat actions.

---

## Plugin-Specific Actions


These actions appear under the **Actron QUE AC** plugin section in Indigo's Action Group editor.

---

### Turn Main Unit On / Off / Toggle

**Action ID:** `setMain`  
**Target:** Actron Que Main Device

Turns the entire AC system on, off, or toggles the current state.

| Setting | Behaviour |
|---------|-----------|
| **On** | Turns the system on (restores the last used mode) |
| **Off** | Turns the system off |
| **Toggle** | Turns on if currently off; turns off if currently on or in any active mode |

> This action does **not** change the HVAC mode (Heat/Cool/Auto). To change mode, use the standard Indigo thermostat *Set HVAC Mode* action or use the Main device's mode controls.

---

### Turn Zone On / Off / Toggle

**Action ID:** `setZone`  
**Target:** Que AC Zone Device

Enables or disables a specific zone's airflow.

| Setting | Behaviour |
|---------|-----------|
| **On** | Enables the zone (opens the damper) |
| **Off** | Disables the zone (closes the damper) |
| **Toggle** | Enables if currently off; disables if currently on |

> ⚠️ **Requirement:** The main AC system must be **running** to open or close zones. If the system is off, the action is ignored and a log message is written.

---

### Set Fan Speed

**Action ID:** `setFanSpeed`  
**Target:** Actron Que Main Device

Sets the indoor fan speed.

| Option | Description |
|--------|-------------|
| **Auto** | Fan speed controlled automatically by the system |
| **Low** | Minimum fan speed (~20% — very quiet) |
| **Medium** | Medium fan speed |
| **High** | Maximum fan speed |

The Actron Que system supports **variable fan speed** all the way down to ~20%, which significantly reduces noise and power consumption when few zones are active.

---

### Turn Quiet Mode On / Off / Toggle

**Action ID:** `setQuiet`  
**Target:** Actron Que Main Device

Controls the system's Quiet Mode.

| Setting | Behaviour |
|---------|-----------|
| **On** | Activates Quiet Mode (limits fan and compressor speed) |
| **Off** | Deactivates Quiet Mode |
| **Toggle** | Switches Quiet Mode to the opposite of its current state |

---

### Set Zone Heat Set Point

**Action ID:** `setZoneHeatsetpoint`  
**Target:** Que AC Zone Device

Sets a zone's heat target temperature to a specific value selected from a list. The list is populated dynamically from the zone's `MinHeatSetpoint` → `MaxHeatSetpoint` range in 0.5 °C steps.

**Usage:**
1. Select the zone
2. Click **Press to Update Temps** to refresh the list
3. Choose the target temperature
4. Save

---

### Set Zone Cool Set Point

**Action ID:** `setZoneCoolsetpoint`  
**Target:** Que AC Zone Device

Sets a zone's cool target temperature to a specific value selected from a list (populated from `MinCoolSetpoint` → `MaxCoolSetpoint` in 0.5 °C steps).

---

### Increase Zone Heat Set Point

**Action ID:** `increaseZoneHeatPoint`  
**Target:** Que AC Zone Device

Increases the zone's heat setpoint by **0.5 °C**. Stops at `MaxHeatSetpoint`.

---

### Decrease Zone Heat Set Point

**Action ID:** `decreaseZoneHeatPoint`  
**Target:** Que AC Zone Device

Decreases the zone's heat setpoint by **0.5 °C**. Stops at `MinHeatSetpoint`.

---

### Increase Zone Cool Set Point

**Action ID:** `increaseZoneCoolPoint`  
**Target:** Que AC Zone Device

Increases the zone's cool setpoint by **0.5 °C**. Stops at `MaxCoolSetpoint`.

---

### Decrease Zone Cool Set Point

**Action ID:** `decreaseZoneCoolPoint`  
**Target:** Que AC Zone Device

Decreases the zone's cool setpoint by **0.5 °C**. Stops at `MinCoolSetpoint`.

---

## Standard Thermostat Actions

Because both device types implement the Indigo thermostat interface, all **built-in Indigo thermostat actions** work directly:

| Action | Main Device | Zone Device |
|--------|:-----------:|:-----------:|
| Set HVAC Mode (Off/Heat/Cool/Auto) | ✅ | ✅ (On/Off only via zone) |
| Set Cool Setpoint | ✅ | ✅ |
| Set Heat Setpoint | ✅ | ✅ |
| Increase Cool Setpoint | ✅ | ✅ |
| Decrease Cool Setpoint | ✅ | ✅ |
| Increase Heat Setpoint | ✅ | ✅ |
| Decrease Heat Setpoint | ✅ | ✅ |
| Request Status | ✅ | ✅ |

> **Fan Mode via standard action:** The standard *Set Fan Mode* action is not supported. Use the plugin's *Set Fan Speed* action instead.

---

## Command Queue & Retry

All commands are placed on an internal queue and processed by a dedicated background thread. This ensures:

- Commands don't time out the main Indigo thread
- Multiple rapid commands are sent in sequence (not simultaneously)
- Failed commands are **automatically retried up to 5 times**
- After 5 failures the command is abandoned and a log message is written

After a successful command, the plugin immediately triggers a **full system status refresh** to update all device states.

---

## Action Examples

### Turn on AC in Cool mode at 24 °C

1. Action: *Turn Main Unit On/Off/Toggle* → **On** → select Main device
2. Action: *Set HVAC Mode* → **Cool** → select Main device
3. Action: *Set Cool Setpoint* → `24` → select Main device

### Enable Bedroom zone and set 22 °C cool

1. Action: *Turn Zone On/Off/Toggle* → **On** → select `Que Zone:1:Bedroom`
2. Action: *Set Zone Cool Set Point* → select zone → `22.0`

### Quiet bedtime routine

1. Action: *Turn Quiet Mode On/Off/Toggle* → **On** → select Main device
2. Action: *Set Fan Speed* → **Low** → select Main device

---

## Next Step

➡️ [Learn about polling and updates →](Polling-and-Updates)
