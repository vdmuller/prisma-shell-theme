# Prisma

A configurable **GNOME Shell 50** theme generator based on official Adwaita
50.1 styles. Independent accent, surface and panel colors, with softly tinted
active controls and highlighted text/icons inspired by the reference image.

## Requirements

- Python 3.10 or later, with no external Python dependencies.
- `sassc` to compile the SCSS sources included in the project.
- GNOME Shell 50 to use the theme.
- The **User Themes** extension enabled to select the theme in your session.

Compilation requires neither internet access nor a full GNOME source checkout.
The base is included in `vendor/`. See [UPSTREAM.md](UPSTREAM.md) for provenance
and licensing.

## Build without installing

From the project directory:

```bash
python3 prisma.py build --config presets/reference.json --output build/Prisma
```

The generated theme contains `gnome-shell/gnome-shell.css`, local SVG assets
and `gnome-shell/prisma.json`. Without `--output`, the destination is
`build/<name>`, relative to the current directory. Building can update an
existing Prisma output, but refuses to replace third-party directories.

## Install and activate

Run **without sudo**. `install.py` accepts all installation options;
`python3 prisma.py install` remains available:

```bash
python3 install.py --config presets/reference.json
```

This installs into `~/.themes/Prisma/gnome-shell`. To also select the theme:

```bash
python3 install.py --config presets/reference.json --activate
```

If User Themes is unavailable, installation is preserved. Enable the extension
and select the theme in its preferences. The installer does not restart the
session, modify GDM or change GNOME's global accent setting.

To customize colors directly:

```bash
python3 install.py --accent '#c08aff' --background '#26272e' \
  --panel-background '#1e1f25' --name Prisma-Purple --activate
```

Quote colors containing `#` in the shell. Colors accept six-digit RGB HEX,
with or without `#`. Names accept 1–64 ASCII letters, digits, dots, hyphens or
underscores, starting with a letter or digit.

## Reusable configuration

```json
{
  "name": "Prisma-Purple",
  "accent": "#c08aff",
  "background": "#26272e",
  "panel_background": "#1e1f25"
}
```

Precedence: **command-line arguments → JSON file → defaults**. Omitted fields
use defaults; unknown or invalid fields stop the operation.

| Option | Default |
| --- | --- |
| `name` | `Prisma` |
| `accent` | `#c08aff` |
| `background` | `#26272e` |
| `panel_background` | same color as `background` |

The `presets/reference.json` preset explicitly sets the panel to `#1e1f25`.
The colors approximate the reference image, with contrast adjustments.

The `presets/ubuntu-orange.json` preset changes only the reference accent to
`#feac8f`. It uses the hue of [Ubuntu orange](https://design.ubuntu.com/brand/colour-palette)
(`#e95420`) while retaining the HSV saturation and value of the current
reference purple (`#bf8ffe`): approximately 43.7% saturation and 99.6% value.
The theme name, background and panel background are unchanged.

```bash
python3 install.py --config presets/ubuntu-orange.json --activate
```

To keep this preset alongside the reference installation, override its name:

```bash
python3 install.py --config presets/ubuntu-orange.json --name Prisma-Ubuntu --activate
```

## Palette and appearance

The configured background is used exactly for the main Quick Settings,
menu and dialog surfaces. Notifications, events and other raised surfaces use
derived shades. Light backgrounds are supported, with automatic adaptation of
text, icons and interaction states.

The configured accent produces softly tinted active controls. Visible accent
text and indicators preserve hue and saturation where possible, adjusting
lightness when necessary for readability. Primary/secondary text and accent
text roles meet a minimum contrast ratio of 4.5:1 on opaque control surfaces;
essential indicators meet 3:1. Disabled foregrounds, decorations and transparent
surfaces retain Adwaita's specific opacities and are outside that guarantee.

For intermediate or highly saturated backgrounds, shades may be darkened or
lightened in a different direction to retain contrast. Resolved roles are
recorded in `prisma.json`, together with the configuration and base version.
Volume, brightness and other OSDs use the base hue/saturation with HSL lightness
reduced by four percentage points, clamped at black, and 95% opacity (5%
transparency). Text and indicators have separate roles for readability; the
final appearance also depends on the content behind the OSD. Errors, warnings,
sharing and recording retain GNOME's semantic colors.

The normal session panel has an independent palette. Overview and lock-screen
panels retain their standard transparent behavior. Pills, spacing, dimensions
and geometry come from Adwaita; scale, fonts and content follow the system.

Notifications and calendar event cards share the same raised surface. Calendar
weekday and month headings have transparent backgrounds. The divider between
notifications and the calendar is subtle and follows the theme's text color;
selected dates remain highlighted.

## Dash to Dock / Ubuntu Dock

Dock icons have transparent backgrounds at rest, exposing the dock's own
background. A subtle rounded highlight appears on hover and disappears when
the pointer leaves. This includes running applications and the applications
button. Running dots, badges and keyboard focus outlines are preserved; the
application grid retains its Adwaita behavior.

GNOME 50 gives extension styles priority over theme styles. Installation
therefore includes the **Prisma Dock** companion extension at
`$XDG_DATA_HOME/gnome-shell/extensions/prisma-dock@prisma.local` (normally
`~/.local/share/gnome-shell/extensions/`). `--activate` also requests its
activation. On first installation, logging out and back in may be necessary
for Shell to discover the extension; the installer reports this when needed.
When installing without `--activate`, enable Prisma Dock in the Extensions app.

The companion loads `gnome-shell/prisma-dock.css` from the selected theme only
when its metadata identifies Prisma. Switching to another theme unloads the
adjustments. Removing the last Prisma theme also removes the companion if it
still belongs to the project. Builds include a copy in `extensions/` for
manual installation or theme distribution.

To validate with the installed Ubuntu Dock in a private session:

```bash
python3 tools/visual_check.py --dock --output build/dock-validation
```

## Update or remove

To update, run the installer again with the same name and desired configuration.
Themes with different names coexist. Without `--activate`, User Themes settings
are unchanged; an already active theme may need to be selected again to reload
its styles. With `--activate`, the installer handles this. Omitted options are
not recovered from the previous installation; use your saved JSON configuration.

```bash
python3 prisma.py remove --name Prisma-Purple
```

Removing an active theme selects the default before deleting files. The
installer replaces/removes only themes with Prisma metadata and refuses
symbolic-link destinations. Generation and updates are transactional; failures
preserve the previous installation.

## Validation

```bash
python3 -m unittest discover -v
python3 tools/visual_check.py
```

Installation tests use temporary directories exclusively. Visual checks start
a headless GNOME Shell with private D-Bus and settings, producing screenshots
and logs in `build/visual-validation` without installing or selecting a theme
in the real session. They require GNOME Shell, `dbus-run-session` and `gsettings`.
Reference controls are real QuickToggle/QuickSlider actors with fixed data;
actual menu screenshots depend on available devices.

See [VALIDATION.md](VALIDATION.md) for results and limitations. Initial support
covers GNOME Shell 50.1 on Ubuntu 26.04. GDM, GTK themes, a graphical configuration
interface and dynamic color synchronization are outside this version's scope.
