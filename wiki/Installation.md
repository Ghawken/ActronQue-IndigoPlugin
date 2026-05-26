![ActronQue Indigo Plugin](https://raw.githubusercontent.com/Ghawken/ActronQue-IndigoPlugin/master/Images/banner.png)

# Installation

This page walks you through downloading and installing the ActronQue Indigo Plugin.

---

## Prerequisites

Before you begin, confirm you have:

- ✅ **Indigo Domotics** installed and running (v2022.1 / Indigo 8 or later recommended)
- ✅ An **Actron Que** ducted AC system registered in the Actron Que mobile app
- ✅ Your **Actron account username and password** (same credentials as the Actron Que app)
- ✅ The Indigo server has **internet access** (cloud API required)

---

## Download

### Option 1 — GitHub Releases (Recommended)

1. Go to the [Releases page](https://github.com/Ghawken/ActronQue-IndigoPlugin/releases)
2. Download the latest `ActronQUE.indigoPlugin.zip` (or `.tar.gz`) asset
3. Unzip the file — you should have a file named `ActronQUE.indigoPlugin`

### Option 2 — Clone the Repository

```bash
git clone https://github.com/Ghawken/ActronQue-IndigoPlugin.git
```

The plugin bundle is at `ActronQUE.indigoPlugin/` inside the cloned folder.

---

## Install

### Method A — Double-click (Easiest)

1. Locate the `ActronQUE.indigoPlugin` file in Finder
2. **Double-click** it
3. Indigo will prompt: *"Do you want to install the plugin ActronQUE?"*
4. Click **Install and Enable**

### Method B — Indigo Plugin Store / Drag & Drop

1. Open **Indigo** → **Plugins** menu → **Manage Plugins…**
2. Drag the `ActronQUE.indigoPlugin` bundle into the plugin list
3. Indigo will install and enable it automatically

### Method C — Manual Copy

1. Copy `ActronQUE.indigoPlugin` to:
   ```
   ~/Library/Application Support/Perceptive Automation/Indigo 2025.1/Plugins/
   ```
2. In Indigo: **Plugins** → **Manage Plugins** → find *ActronQUE* → click **Enable**

---

## Verify Installation

After installation the plugin should appear in:

- **Indigo menu bar** → **Plugins** → **ActronQUE** (menu item visible)
- **Plugins window** with status **Running**

If the plugin shows **Disabled** or **Error**, see [Troubleshooting](Troubleshooting).

---

## Upgrading

To upgrade to a newer version:

1. Download the new `.indigoPlugin` bundle
2. Double-click it — Indigo will detect the existing installation and upgrade in place
3. All your configured devices and settings are preserved

> **Note:** Always check the [Changelog](Changelog) before upgrading — some versions have migration notes.

---

## Uninstalling

1. **Plugins** → **Manage Plugins** → select *ActronQUE* → click **Delete**
2. This removes the plugin bundle but leaves your Indigo devices intact
3. Delete the Que Main Device and Zone devices manually if desired

---

## Next Step

➡️ [Configure the plugin →](Configuration)
