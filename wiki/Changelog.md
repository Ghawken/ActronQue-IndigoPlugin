![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Changelog

Full version history for the ActronQue Indigo Plugin.

---

## v0.6.56 — Bug Fix
- Fix for rare `NoneType` zone error when iterating zone devices


---

## v0.6.55 — Polling Fallback
- Nimbus events API endpoints now also failing — disabled events-based updates entirely
- Default to full system status poll every **30 seconds**
- Full status poll every **1.5 seconds** immediately after a command is sent
- Both `que.actronair.com.au` and `nimbus.actronair.com.au` events endpoints commented out

---

## v0.6.50
- Internal stability improvements

---

## v0.6.40
- Internal updates and fixes

---

## v0.6.35 — Stability & Humidity (April)
- Timestamp validation for events to avoid applying stale data from the API
- Zone humidity reporting added and live-updated at startup
- `humidityInput1` rounded to 3 decimal places for cleaner display
- Successful command detection (`sentCommand` flag) triggers immediate device state refresh

---

## v0.6.4 — Connection Reliability (April)
- Extended request timeout parameters throughout
- Strengthened connection error handling
- Humidity data captured in event parsing (unused at this stage)

---

## v0.6.2 — Fan Status & Error Codes (May)
- Fan on/off state (`fanOn`) added to Main device states
- Error code (`errorCode`) added to Main device states
- Logging improvements across connection and event handling
- Debug 4 flag added for verbose events API logging
- Command threading corrections — prevents race conditions on rapid commands

---

## v0.6.1 — Python 3 Compatibility (May)
- Full Python 3 compatibility pass
- Various bug fixes related to string handling and type changes

---

## v0.3.9
- Update device states **before** sending command (optimistic state update)
- Prevents multiple rapid commands from reverting to stale temperature values
- States typically update quickly via `latestEvents` after the command

---

## v0.3.8
- Decreased Actron API timeout for faster failure detection
- Added per-zone Heat and Cool setpoint controls within Indigo

---

## v0.3.5
- Changed command code to send Que commands **one at a time** in a separate thread
- Prevents simultaneous commands from causing API timeouts

---

## v0.3.2 — Events API (July)
- Major update: switched to Actron Events API for ~5–10 second refresh intervals
- Added timeout management for event polling
- Multiple login detection with automatic access token recreation
- More robust handling of concurrent sessions

---

## v0.3.1 — Events API Integration (July)
- Initial Events API integration for frequent real-time updates
- Timeout-based connection throttling to prevent flooding the API

---

## v0.2.0
- Fix for plugin version reporting

---

## v0.1.9 — Humidity & Quiet Mode (June)
- Humidity averaging across all active zones
- Zone percentage open tracking
- Set point commands for zones
- Quiet Mode on/off functionality
- Retry logic for timeout errors (up to 5 attempts)

---

## v0.1.8
- Turn off system without changing the current HVAC mode

---

## v0.1.7
- Zone Heat and Cool setpoint increase/decrease actions (0.5 °C increments)
- Handle command timeouts with automatic retry (×5 before giving up)

---

## v0.1.5
- Improved handling of `requests` library errors and timeouts

---

## v0.1.4
- Fix for `isActurnedon` failing on communication error
- Added percentage circle images for zone devices on control pages

---

## v0.1.3
- Removed zone humidity states (they were duplicates of main device humidity)
- Added zone percentage open state
- Zone matching by **number** instead of name (enables safe zone renaming)
- Fix: check for correct `MasterDevice` ID in zone devices to support multiple systems

---

## v0.1.2
- Only include humidity values > 0 in average humidity calculation

---

## v0.1.1 — Polish (May)
- Rounded numeric values for cleaner display
- Status update after each command sent
- Fix for device states on control pages
- Updated GitHub repository links
- Fix for AUTO / HEAT / COOL mode reporting

---

## v0.0.9
- Don't use compressor mode for HVAC mode reporting when not running
- Use Heat/Cool mode from user settings (not compressor mode) for accurate state

---

## v0.0.8
- Added check: system must be running before zones can be opened/closed
- Token recheck on connection errors

---

## v0.0.6
- Zone On/Off reporting now uses the enabled flag (not `ZonePosition`)
- Added `zoneisEnabled` state for use in triggers and control pages
- Added `zoneisOpen` state (may differ from enabled — zone closes when setpoint reached)
- Zone Toggle action (On/Off/Toggle) — ideal for control page buttons
- Main device Toggle On/Off — does not change HVAC mode
- Token validity check on connection attempts

---

## v0.0.5
- Bug fix: crash when no zones defined at startup

---

## v0.0.3 — Initial Release (May)
- First public release
- Basic Actron Que cloud API integration
- Main device and zone devices
- Authentication flow (pairing token → bearer token)
- HVAC mode, setpoint, and zone controls
