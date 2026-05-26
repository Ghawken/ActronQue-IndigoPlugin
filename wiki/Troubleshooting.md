![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Troubleshooting

This page covers the most common issues and how to resolve them.

---

## Plugin Won't Start / Shows Error

### Check the Indigo log

Open **Indigo** → **Window** → **Event Log** and look for error messages from `Actron QUE AC`.

### Verify Python version

The plugin requires **Python 3** (included with Indigo 8+). Check the Indigo server's Python version in the plugin's startup log message.

### Check plugin is enabled

**Plugins** → **Manage Plugins** → ensure *ActronQUE* shows **Running**. If it shows *Disabled*, click the Enable button.

---

## Cannot Connect / No Access Token

**Symptom:** Log shows *"Unable to get Access Token, check username, Password"* or *"Failed to get Access Token"*

### Causes & Solutions

| Cause | Solution |
|-------|---------|
| Wrong username/password | Verify credentials in the Actron Que iOS/Android app — use exact same login |
| Actron API temporarily down | Wait 5–10 minutes and check again; API outages do occur |
| Multiple active sessions | Log out of the Actron app on other devices; the API may reject multiple concurrent tokens |
| Internet not available | Check Indigo server's internet connection |
| Firewall blocking | Ensure `que.actronair.com.au` port 443 is reachable |

### How to test manually

From the Indigo server's Terminal:
```bash
curl -X POST https://que.actronair.com.au/api/v0/client/user-devices \
  -d "username=YOUR_EMAIL&password=YOUR_PASSWORD&client=ios&deviceUniqueIdentifier=test" \
  -k
```
A successful response contains a `pairingToken`. An error response will indicate the problem (e.g. `"Invalid credentials"`).

---

## Serial Number Not Retrieved

**Symptom:** The *"Using Serial No"* field is blank in device settings; log shows *"Unable to get Serial Number"*

**Cause:** This usually follows an authentication failure. The plugin cannot query AC systems without a valid token.

**Solution:** Resolve the access token issue first (see above). Once authenticated, the serial number is populated on the next poll cycle (~30 seconds).

---

## Device Shows Offline (deviceIsOnline = False)

**Symptom:** The Main device's display state shows `False` or the device is marked offline in Indigo.

### Causes & Solutions

| Cause | Solution |
|-------|---------|
| AC system controller not reachable by Actron cloud | Check that the Actron wall controller has internet connectivity (LED indicators, Actron app connectivity) |
| Actron cloud service outage | Check the Actron app — if it also shows offline, it's an Actron service issue |
| Plugin authentication expired | Wait for the automatic re-authentication cycle (~24 hours), or restart the plugin |
| Indigo server has no internet | Check Indigo server's network connection |

The `lastContact` state will show how long ago the system was last seen when offline.

---

## Zone Devices Not Created

**Symptom:** Clicking *"Generate Zone Devices"* produces no new devices.

### Causes & Solutions

| Cause | Solution |
|-------|---------|
| Main device not yet connected | Wait for `deviceIsOnline` to become `True` before generating zones |
| Access token or serial not populated | Verify the *Using Serial No* field is filled in device settings |
| Zones already exist | Re-running Generate Zone Devices skips existing zones — check if they already exist in a different Indigo folder |

---

## Zone Actions Ignored

**Symptom:** *Turn Zone On/Off/Toggle* action does nothing; log shows *"Main Que Device is Off"*

**Cause:** Zone commands require the main AC system to be **running**. You cannot open or close dampers when the system is off.

**Solution:** Turn on the Main device first, then control zones.

---

## Commands Fail / Timeout

**Symptom:** Log shows *"Timeout received from Actron API for System Command. Will retry"* or *"Command failed after multiple repeats. Aborting"*

### Causes & Solutions

| Cause | Solution |
|-------|---------|
| Actron API slowness | Normal — the plugin retries up to 5 times automatically |
| Token expired mid-command | The plugin re-authenticates on failure — try the action again |
| Network instability | Check the Indigo server's internet connection |

If commands consistently fail, enable **Debug 1** and check the full API response in the log.

---

## States Not Updating

**Symptom:** Device states in Indigo don't change even though the physical system is operating.

### Check device online state

If `deviceIsOnline = False` the plugin is not receiving data from the API.

### Check polling frequency

With *"Update less Frequently"* enabled, updates occur only every 5 minutes.

### Enable Debug 4

Enable **Debug 4 (Latest Events)** in Plugin Preferences. This logs every API response payload to the Indigo log and the plugin log file. Check for parse errors or missing fields.

### Restart the plugin

**Plugins** → **Manage Plugins** → *ActronQUE* → **Disable** → **Enable**. This re-runs the full startup sequence including authentication.

---

## Setpoint Actions Out of Range

**Symptom:** Log shows *"Maximum/Minimum Cool/Heat Set point reached for zone"* and the setpoint doesn't change.

**Cause:** Each zone has enforced min/max setpoint limits from the AC system. These limits are stored in `MinCoolSetpoint`, `MaxCoolSetpoint`, `MinHeatSetpoint`, `MaxHeatSetpoint`.

**Solution:** Adjust the **master system setpoint** on the main device first to widen the allowable range for zones. Zone setpoints must stay within the range defined by the master controller.

---

## Incorrect Temperature Averaging

**Symptom:** The Main device's temperature (`temperatureInput1`) looks wrong.

**Cause:** The main device temperature is calculated as the **average of all active zones**. If some zones have zero temperature readings (offline sensors), this can skew the average.

**Solution:** Check individual zone `currentTemp` states to identify zones with bad sensor readings. The plugin excludes zones with zero humidity from averaging but does include all zone temperatures.

---

## Clean Filter / Alert Not Clearing

**Symptom:** `alertCleanFilter` remains `True` after cleaning the filter.

**Cause:** This state is read directly from the Actron API. The alert is cleared by the AC system itself, not by the plugin.

**Solution:** Follow the Actron system's filter reset procedure (usually holding a button on the wall controller). The plugin will pick up the cleared state on the next poll.

---

## Getting More Debug Information

1. Open **Plugins** → **Actron QUE AC** → **Configure…**
2. Set **Indigo Log Debug Level** to *Debugging Messages* (10)
3. Enable **Debug 4** for API event details
4. Reproduce the issue
5. Check **Indigo** → **Window** → **Event Log** for detailed output

The plugin log file contains the most complete output (set to Detailed level by default):
```
~/Library/Application Support/Perceptive Automation/Indigo 2025.1/Logs/
com.GlennNZ.indigoplugin.ActronQUE/plugin.log
```

---

## Reporting Issues

When reporting an issue on [GitHub](https://github.com/Ghawken/ActronQue-IndigoPlugin/issues), please include:

- Plugin version (check **Info.plist** or the startup log message)
- Indigo version
- macOS version
- Relevant log output (with access tokens redacted)
- Steps to reproduce

---

## Next Step

➡️ [View the full changelog →](Changelog)
