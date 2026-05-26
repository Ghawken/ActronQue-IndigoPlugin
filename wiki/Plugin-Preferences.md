![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Plugin Preferences

The plugin preferences panel provides logging and debug controls. Access it via:

**Indigo** → **Plugins** → **Actron QUE AC** → **Configure…**

---

## Log Level Settings

### Indigo Log Debug Level

Controls what the plugin writes to the **Indigo event log** (the main log you see in the Indigo application).

| Option | Level | Description |
|--------|-------|-------------|
| Detailed Debugging Messages | 5 | Very verbose — every internal step |
| Debugging Messages | 10 | Standard debug output |
| **Informational Messages** | **20** | **Default — normal operation messages** |
| Warning Messages | 30 | Warnings only |
| Error Messages | 40 | Errors only |
| Critical Errors Only | 50 | Minimal output |

### File Debug Level

Controls what the plugin writes to its **log file** on disk (independent of the Indigo event log).

| Option | Level | Default |
|--------|-------|---------|
| Detailed Debugging Messages | 5 | ✅ Default |
| Debugging Messages | 10 | |
| Informational Messages | 20 | |
| Warning Messages | 30 | |
| Error Messages | 40 | |
| Critical Errors Only | 50 | |

The plugin log file is stored at:
```
~/Library/Application Support/Perceptive Automation/Indigo 2025.1/Logs/com.GlennNZ.indigoplugin.ActronQUE/plugin.log
```

---

## Debug Flags

Five individual debug flags provide targeted logging for specific subsystems. All are **off by default**.

| Flag | ID | Description |
|------|----|-------------|
| **Debug 1** | `debug1` | Verbose command logging — logs full access tokens and serial numbers in command debug output. ⚠️ Exposes credentials in the log file. |
| **Debug 2** | `debug2` | General additional debug (currently spare) |
| **Debug 3** | `debug3` | General additional debug (currently spare) |
| **Debug 4** | `debug4` | **Events API logging** — logs every event received from the Actron API, including full JSON payloads. Very verbose. |
| **Report Unknown Events** | `debug5` | Logs any API event field that the plugin doesn't specifically handle. Useful for discovering new API fields. |

> ⚠️ **Warning:** Debug 1 logs the access token. Only enable when troubleshooting connectivity issues and only post log extracts to public places after redacting the token.

---

## Toggle Debugging (Menu Item)

A quick toggle is available via the plugin menu:

**Indigo** → **Plugins** → **Actron QUE AC** → **Toggle Debugging**

This switches the Indigo log level between `INFO` (20) and `DEBUG` (10) without opening the preferences dialog. It does not affect the file log level or the specific debug flags.

---

## Recommended Settings for Normal Operation

| Setting | Recommended Value |
|---------|------------------|
| Indigo Log Level | Informational Messages (20) |
| File Log Level | Detailed Debugging Messages (5) |
| Debug 1–5 | All off |

---

## Recommended Settings for Troubleshooting

| Scenario | Settings |
|----------|---------|
| **Connection problems** | Enable Debug 1, set Indigo Log to Debugging (10) |
| **Missing state updates** | Enable Debug 4, set Indigo Log to Debugging (10) |
| **Unknown API data** | Enable Debug 5 |
| **Posting to forums** | Use Informational level; redact any access tokens before posting |

---

## Next Step

➡️ [Troubleshooting guide →](Troubleshooting)
