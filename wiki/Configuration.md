![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Configuration

This page explains how to create and configure the Main Que Device and generate your zone devices.

---

## Overview

The plugin uses a **two-step setup**:

1. Create the **Actron Que Main Device** and enter your account credentials
2. Click **Generate Zone Devices** — the plugin automatically creates one device per zone

---

## Step 1 — Create the Main Que Device

1. In Indigo, open **Devices** → click **New Device…** (or press ⌘N)
2. In the *Type* dropdown select **Plugin**
3. In the *Plugin* dropdown select **Actron QUE AC**
4. In the *Model* dropdown select **Actron Que Main Device**
5. Give the device a meaningful name, e.g. `Actron Que AC`
6. Click **Edit Device Settings…**

---

## Step 2 — Device Settings

The device configuration dialog looks like this:

![Main Device Setup](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/QueMainSetup.png)

### Fields

| Field | Description |
|-------|-------------|
| **Username** | Your Actron account email address |
| **Password** | Your Actron account password |
| **Generate Zone Devices** *(button)* | Creates one Zone device per configured zone |
| **Update less Frequently** *(checkbox)* | See below |
| **Using Serial No** *(read-only)* | Populated automatically after first connection |

### Account Credentials

Enter the **same username and password** you use with the Actron Que iOS/Android app. These are sent to the Actron cloud to obtain a bearer token; they are stored locally in the Indigo device properties and never logged.

> ⚠️ **Security note:** Credentials are stored in Indigo's device plugin properties. Avoid sharing Indigo backups that contain this device without sanitising them first.

### Update Frequency

The **"Update less Frequently"** checkbox controls how often the plugin polls:

| Setting | Behaviour |
|---------|-----------|
| **Disabled** (default) | Polls full system status every ~30 seconds |
| **Enabled** | Polls only every ~5 minutes |

> In v0.6.55+ the plugin always uses full system polling because the Actron events API (`/events/newer`) became unreliable. The checkbox still controls the 5-minute vs 30-second interval.

---

## Step 3 — Save and Connect

1. Click **Save** to close the dialog
2. Click **Save** again on the new device dialog
3. The plugin will immediately:
   - Authenticate with the Actron API
   - Retrieve the system serial number
   - Pull the full system status
   - Populate all device states
4. Check the **Serial No** field — it should now show your unit's serial number

If the device shows **offline** or states remain empty, see [Troubleshooting](Troubleshooting).

---

## Step 4 — Generate Zone Devices

Once the Main device is online:

1. Re-open the device settings (**Edit Device Settings…**)
2. Click **Generate Zone Devices**
3. The plugin creates one `Que AC Zone` device per zone, placed in the **same Indigo folder** as the Main device
4. Each zone device is named `Que Zone:N:ZoneName` (e.g. `Que Zone:1:Bedroom`)

![Zone Device](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/QueZone.png)

> **Tip:** Run Generate Zone Devices only once. Re-running it skips any zones that already exist, so it is safe to run again if you add new zones.

---

## Step 5 — Verify Status

After setup your devices should show:

![Main Device Status](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/QueMainStatus.png)

The main device display state is `deviceIsOnline`. Check the device details panel for all states — temperatures, setpoints, compressor readings, etc.

---

## Multi-System Setup

If you have more than one Actron Que system:

1. Create a **second** Actron Que Main Device with the second system's credentials
2. Each Main device will retrieve its own serial number
3. Run **Generate Zone Devices** for each Main device separately
4. Zone devices are linked to their parent Main device via the `deviceMasterController` state

---

## Reconfiguring / Changing Password

If you change your Actron account password:

1. Open the Main device settings
2. Update the **Password** field
3. Save — the plugin will re-authenticate at next poll (within 30 seconds)

The access token is automatically refreshed every 24 hours or whenever authentication fails.

---

## Next Step

➡️ [Learn about the devices →](Devices)
