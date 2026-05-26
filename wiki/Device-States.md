![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Device States

Complete reference of every state exposed by each device type.

---

## Actron Que Main Device States

These states are available on the `ActronQueMain` device type.

### Online / Connection

| State ID | Type | Description |
|----------|------|-------------|
| `deviceIsOnline` | Boolean | `True` when the AC system is reachable via the cloud API. This is the **display state** shown in the device list. |
| `lastContact` | String | Time since last cloud contact (e.g. `"0 days, 0:00:45"`). Populated when the system goes offline. |
| `serialNumber` | String | Serial number of the AC system, retrieved from the Actron API on first connection. |

### HVAC Mode & Power

| State ID | Type | Description |
|----------|------|-------------|
| `hvacOperationMode` | Enum | Current HVAC mode: `Off`, `Heat`, `Cool`, `HeatCool` (Auto). Standard Indigo thermostat state. |
| `setpointCool` | Number | Current system cool setpoint temperature (°C). |
| `setpointHeat` | Number | Current system heat setpoint temperature (°C). |

### Temperature & Humidity

| State ID | Type | Description |
|----------|------|-------------|
| `temperatureInput1` | Number | **Average** temperature across all active zones (°C). Standard Indigo thermostat state. |
| `humidityInput1` | Number | Master unit humidity reading (%). |

### Fan

| State ID | Type | Description |
|----------|------|-------------|
| `fanSpeed` | String | Current fan speed mode: `AUTO`, `LOW`, `MED`, `HIGH`. |
| `fanOn` | Boolean | `True` when the indoor fan is actively running. |
| `indoorFanRPM` | Number | Indoor fan speed in RPM. |
| `indoorFanPWM` | Number | Indoor fan PWM duty cycle value. |

### Compressor / Outdoor Unit

| State ID | Type | Description |
|----------|------|-------------|
| `outdoorUnitTemp` | Number | Outdoor unit ambient temperature (°C). |
| `outdoorUnitPower` | Number | Outdoor unit compressor power consumption (W). |
| `outdoorUnitPWM` | Number | Outdoor unit compressor PWM value. |
| `outdoorUnitCompSpeed` | Number | Outdoor unit compressor speed (RPM or relative). |
| `outdoorUnitFanSpeed` | Number | Outdoor unit fan speed. |
| `outdoorUnitCompMode` | String | Compressor operating mode: `HEAT`, `COOL`, or empty when idle. |
| `compressorCapacity` | Number | Compressor capacity percentage (%). |
| `indoorUnitTemp` | Number | Indoor unit (roof space) temperature (°C). |
| `indoorModel` | String | Indoor unit model/device ID string from the API. |

### Quiet Mode

| State ID | Type | Description |
|----------|------|-------------|
| `quietMode` | Boolean | `True` when Quiet Mode is active. Reduces noise by limiting fan and compressor speeds. |

### Alerts

| State ID | Type | Description |
|----------|------|-------------|
| `alertCleanFilter` | Boolean | `True` when the system requests a filter clean. |
| `alertDRED` | Boolean | `True` when a DRED (Demand Response Enabling Device) signal is active. |
| `alertDefrosting` | Boolean | `True` when the outdoor unit is in defrost mode. |
| `errorCode` | String | Error code string from the system (e.g. `"Error Code:5"`). `"None"` when no error. |

---

## Que Zone Device States

These states are available on `queZone` devices.

### Zone Identity

| State ID | Type | Description |
|----------|------|-------------|
| `zoneName` | String | Zone name as configured in the Actron system (e.g. `"Bedroom"`). |
| `zoneNumber` | Number | Zone index 1–8. Used to map this device to the API's zero-indexed zone array. |
| `deviceMasterController` | Number | Indigo device ID of the parent `ActronQueMain` device. |

### Zone Status

| State ID | Type | Description |
|----------|------|-------------|
| `hvacOperationMode` | Enum | Zone's effective HVAC mode. Mirrors the main system mode when enabled; `Off` when disabled. |
| `zoneisEnabled` | Boolean | `True` if the user has turned this zone on. |
| `zoneisOpen` | Boolean | `True` if the damper is physically open (airflow active). A zone can be enabled but closed if the setpoint has been reached. |
| `zonePosition` | Number | Raw damper position value (0–20). `0` = fully closed, `20` = fully open. |
| `zonePercentageOpen` | Number | Damper open percentage (0–100%). Calculated as `zonePosition × 5`. |
| `canOperate` | Boolean | `True` if the zone is capable of operating (from the AC system). |

### Temperature & Humidity

| State ID | Type | Description |
|----------|------|-------------|
| `currentTemp` | Number | Current measured temperature in this zone (°C). Same as `temperatureInput1`. |
| `temperatureInput1` | Number | Current measured temperature (°C). Standard Indigo thermostat state. |
| `currentHumidity` | Number | Current humidity in this zone (%). Same as `humidityInput1`. |
| `humidityInput1` | Number | Current humidity (%). Standard Indigo thermostat state. |
| `currentTempHystersis` | Number | Temperature hysteresis value for this zone (°C). |

### Setpoints

| State ID | Type | Description |
|----------|------|-------------|
| `setpointCool` | Number | Zone cool setpoint (°C). Same as `TempSetPointCool`. |
| `setpointHeat` | Number | Zone heat setpoint (°C). Same as `TempSetPointHeat`. |
| `TempSetPointCool` | Number | Zone cool target temperature (°C). |
| `TempSetPointHeat` | Number | Zone heat target temperature (°C). |
| `MinCoolSetpoint` | Number | Minimum allowed cool setpoint for this zone (°C). |
| `MaxCoolSetpoint` | Number | Maximum allowed cool setpoint for this zone (°C). |
| `MinHeatSetpoint` | Number | Minimum allowed heat setpoint for this zone (°C). |
| `MaxHeatSetpoint` | Number | Maximum allowed heat setpoint for this zone (°C). |

### Sensor

| State ID | Type | Description |
|----------|------|-------------|
| `sensorBattery` | Number | Battery level of the zone's wireless sensor (%). |
| `sensorId` | String | Unique ID of the wireless sensor in this zone. |

---

## Using States in Indigo

### Triggers

Any state can be used in Indigo triggers with *"Device State Changed"* as the condition. For example:

- Trigger when `alertCleanFilter` changes to `True` → send a notification
- Trigger when `deviceIsOnline` changes to `False` → log an alert
- Trigger when `zoneisEnabled` changes on the Bedroom zone

### Control Pages

States can be displayed on Indigo control pages using the **Text Label** object bound to a device state. Useful states for control pages:

- `currentTemp` — zone temperature display
- `zonePercentageOpen` — with the included percentage circle images
- `fanSpeed` — current fan speed
- `quietMode` — quiet mode indicator
- `alertCleanFilter` — maintenance reminder

---

## Next Step

➡️ [View all actions →](Actions)
