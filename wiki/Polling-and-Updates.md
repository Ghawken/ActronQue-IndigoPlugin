![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Polling & Updates

This page explains how the plugin keeps Indigo device states in sync with the physical AC system.

---

## Overview

The Actron Que system is **cloud-based only** — there is no local API. The plugin polls the Actron cloud API at regular intervals to refresh all device states.

```
Indigo Plugin  ──────────►  que.actronair.com.au  ──────────►  AC System
                 HTTPS/REST                          (via cloud)
```

---

## Polling Architecture

The plugin runs a single `runConcurrentThread` loop that iterates over all enabled `ActronQueMain` devices and decides what to fetch.

### Polling Schedule (v0.6.55+)

| Timer | Action |
|-------|--------|
| Every **~30 seconds** | Full system status poll (`/status/latest`) |
| Every **~305 seconds** | Additional guaranteed full poll (fallback) |
| After **successful command** | Immediate full status refresh (resets the 30-second timer) |
| On **offline detection** | Full status poll every 5 minutes until back online |
| Every **24 hours** | Re-authenticate and get a fresh access token |
| On **auth failure** | Immediate re-authentication attempt |

> Prior to v0.6.55 the plugin used the Actron events API (`/events/newer`) for near-instant updates. Both the `que.actronair.com.au` and `nimbus.actronair.com.au` events endpoints became unreliable, so the plugin now defaults to full system polling.

---

## Update Frequency Setting

The **"Update less Frequently"** checkbox in the Main device settings:

| State | Poll interval |
|-------|--------------|
| **Unchecked** (default) | ~30 seconds |
| **Checked** | ~5 minutes |

Use the 5-minute interval if you want to minimise API calls, at the cost of less responsive state updates in Indigo.

---

## API Endpoints Used

### Authentication

```
POST https://que.actronair.com.au/api/v0/client/user-devices
```
- Sends: `username`, `password`, `client=ios`, `deviceUniqueIdentifier=IndigoPlugin`
- Returns: `pairingToken`

```
POST https://que.actronair.com.au/api/v0/oauth/token
```
- Sends: `grant_type=refresh_token`, `refresh_token=<pairingToken>`, `client_id=app`
- Returns: `access_token` (Bearer)

### System Discovery

```
GET https://que.actronair.com.au/api/v0/client/ac-systems
```
- Returns: System list with serial numbers
- The plugin uses the first system's serial number

### Status Polling

```
GET https://que.actronair.com.au/api/v0/client/ac-systems/status/latest?serial=<serial>
```
- Returns: Full system state including all zones, temperatures, setpoints, alerts
- Parsed into all Main device and Zone device states

### Command Sending

```
POST https://que.actronair.com.au/api/v0/client/ac-systems/cmds/send?serial=<serial>
```
- Body: `{"command": {"<setting>": <value>, "type": "set-settings"}}`
- Returns: `{"type": "ack"}` on success or `{"type": "timeout"}` on failure

---

## Command Processing

Commands (actions) are placed on an internal thread-safe **queue** and processed sequentially by a dedicated background thread (`threadCommand`).

```
Action called → QueCommand object → Queue → threadCommand thread → API POST → ack
                                                                       ↓
                                                               Retry on failure (×5)
                                                                       ↓
                                                               sentCommand = True
                                                                       ↓
                                                            Immediate full status refresh
```

### Retry Logic

| Attempt | Delay before retry |
|---------|-------------------|
| 1st retry | ~5 seconds |
| 2nd retry | ~5 seconds |
| 3rd retry | ~5 seconds |
| 4th retry | ~5 seconds |
| 5th attempt | Abort — log error |

On each failure the plugin also re-authenticates (`checkMainDevices()`) in case the token has expired.

---

## State Pre-updating

For setpoint and zone commands, the plugin **immediately updates the local Indigo device state** before the API call completes. This ensures that rapid consecutive commands (e.g. pressing increase setpoint multiple times quickly) start from the correct current value rather than the last-polled value.

---

## Timestamp Validation (Events API)

The code retains the events API infrastructure (currently disabled). When active, it validates event timestamps to avoid applying stale data:

| Event Type | Max Age Accepted |
|-----------|-----------------|
| `full-status-broadcast` | 15 minutes |
| `status-change-broadcast` | 5 minutes |

Events older than these thresholds are discarded without updating device states.

---

## Token Lifecycle

```
Plugin start
    │
    ▼
getPairingToken(username, password)
    │
    ▼
Exchange for access_token (OAuth2 refresh_token grant)
    │
    ▼
Store in device pluginProps['accessToken']
    │
    ├── Normal operation: token reused for all API calls
    │
    ├── Every 24 hours: token refreshed proactively
    │
    └── On API 401/auth error: immediate token refresh
```

> Tokens are **never logged** at any debug level to protect credentials.

---

## Internet Requirements

The plugin requires the Indigo server to be able to reach:

| Host | Port | Purpose |
|------|------|---------|
| `que.actronair.com.au` | 443 (HTTPS) | All API calls |

SSL certificate verification is currently **disabled** (`verify=False`) in the requests library calls to work around certificate issues with the Actron API. This is a known limitation.

---

## Next Step

➡️ [Plugin preferences and debug options →](Plugin-Preferences)
