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
| `solid_accent` | `false` |

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

## Solid accent selection

Use `--solid-accent` to fill selected controls with the exact configured accent
and use pure white (`#ffffff`) text/icons on both selected and ordinary controls. Hover, focus and
pressed states use derived shades; the arrow segment remains distinct. This
applies to Quick Settings, selected switches/checkboxes, calendar selection and
default action buttons. Other accent indicators and links retain their roles.

```bash
python3 prisma.py build --config presets/reference.json --solid-accent \
  --name Prisma-Solid --output build/Prisma-Solid
python3 install.py --config presets/reference.json --solid-accent \
  --name Prisma-Solid --activate
```

The equivalent JSON option is `"solid_accent": true`. Command-line options
still override JSON; `--no-solid-accent` explicitly restores the softly tinted
style even when a configuration file enables solid selection.

Solid mode prioritizes the exact accent and consistent white text, so selected
control text is outside the tinted mode's 4.5:1 contrast guarantee. The foreground stays white rather than adapting to the accent.

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

Quick Settings buttons with additional options have a distinct arrow segment.
Selected main buttons use 15.5% accent mixed into the background; arrow segments
use 26%, with stronger tints for hover and pressed states. Neutral controls
preserve the background hue, increase HSL saturation by a factor of 1.07 and
shift HSL lightness by 4.7 percentage points in the appropriate direction.
Inactive arrow segments preserve the same background hue, with a 7.1-point
HSL lightness shift and a 1.03 saturation multiplier, avoiding a washed-out
white blend. Contrast adjustments still take priority for extreme palettes.
With accent `#b087e5` and background `#262831`, the normal control is `#30333f`,
the inactive arrow is `#363846`, the selected control is `#3b374d`, and its
arrow segment is `#4a4160` (within
one RGB level of the reference `#494160`). Adwaita
preserves their shared capsule outline, mirrored in RTL layouts, with separate
hover, focus, pressed and disabled states.

Notifications and calendar event cards share the same raised surface. Calendar
weekday and month headings have transparent backgrounds. The divider between
notifications and the calendar is subtle and follows the theme's text color;
selected dates remain highlighted. Date numbers and the empty Add World Clocks
action use regular font weight.

## Dash to Dock / Ubuntu Dock

Dock icons have transparent backgrounds at rest, exposing the dock's own
background. A subtle rounded highlight appears on hover and disappears when
the pointer leaves. This includes running applications and the applications
button. Running dots, badges and keyboard focus outlines are preserved; the
application grid retains its Adwaita behavior.

Prisma does not install a companion extension. Its CSS provides the dock's
background with 85% opacity (15% transparency), while Dash to Dock / Ubuntu
Dock manages positioning, spacing, hover and compact layout natively.

When `--activate` is used and the native dock settings schema is available,
the installer disables the dock's built-in theme, sets its background to the
configured theme background and selects fixed transparency at 85% opacity.
It preserves compact mode (`custom-theme-shrink`), panel mode (`extend-height`),
position and icon size. These are user preferences, not theme geometry.

Compact mode also reduces the inherited Adwaita icon tile padding from 6px
to 2px, removes inner spacing and uses a 12px corner radius. These adjustments
apply only to the dock's `.shrink` mode, including the applications button;
normal dock mode and the application grid retain their original geometry.

To enable compact spacing manually:

```bash
gsettings set org.gnome.shell.extensions.dash-to-dock custom-theme-shrink true
```

To keep the dock sized to its contents rather than extending across the screen:

```bash
gsettings set org.gnome.shell.extensions.dash-to-dock extend-height false
```

The obsolete `prisma-dock@prisma.local` helper is disabled and removed on the
next installation or removal only if its ownership marker identifies Prisma.
Third-party files are preserved. User Themes is still required to select the
Shell theme; it is separate from the removed dock helper. Native dock settings
persist when switching Shell themes and can be changed in dock preferences.

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
