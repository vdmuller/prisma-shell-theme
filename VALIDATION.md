# Prisma validation

Validated on 2026-10-05 with Ubuntu 26.04, GNOME Shell/Mutter 50.1, Python 3.14
and `/usr/bin/sassc`. The public interface uses Python 3.10-compatible features.

## Automated tests

```bash
python3 -m unittest discover -v
```

**21 tests passed**, with no skips on this machine. Coverage includes:

- Defaults, file/CLI precedence, and HEX, name and JSON validation.
- Contrast, distinct states and derived shades across 45 background/accent
  combinations: black, white, purple, red, green, blue and intermediate grays.
- Selected control foreground/background contrast in compiled CSS, including
  checkboxes, switches and Quick Settings, across four backgrounds.
- Darker OSD surfaces with alpha 0.95 and independent text/indicator roles.
- Byte-for-byte reproducible generation and existing local assets.
- Surface independence from accent changes; panel color changes restricted to
  panel rules in the compiled CSS.
- Installation, updates, coexistence, activation, removal and theme reset.
- Protection of third-party destinations and symbolic links.
- Preservation of previous installations after compilation or commit failures.
- Preservation of installation when User Themes is unavailable.
- Selection restoration after activation failure, and refusal to remove an
  active theme when the required theme reset fails.
- Native dock settings without overwriting compact, position or icon-size
  preferences; obsolete companion cleanup and third-party protection.

Tests do not install themes into the real profile. The reference preset was
also built into `build/Prisma/`.

## Visual validation

```bash
python3 tools/visual_check.py
```

The isolated headless session generated **24 screenshots** in
`build/visual-validation/`, with results in `result.json` and logs in
`session.log`. Coverage includes:

- The reference preset, a light background, a blue accent and a light panel.
- Actual Quick Settings menus and controls with deterministic fixture data.
- LTR and RTL layouts; normal, hover, focus, active and insensitive states.
- Expanded submenus, a notification banner, and a calendar with notifications.
- Overview, a dialog with a default button, and a volume OSD with a darker
  translucent background.

The images were inspected: pills are preserved in both directions, selections
are softly tinted with highlighted text, sliders use the accent, light themes
adapt contrast, and the panel uses its independent color. No theme/CSS parsing
or image loading errors were found.

Fixtures use GNOME QuickToggle/QuickMenuToggle/QuickSlider actors with fixed
labels and states, rather than HTML mockups. Actual menus vary with available
hardware, batteries and devices. The headless environment lacks some audio and
brightness sources available in a physical session. Actual submenus may contain
available network names; review screenshots before sharing.

Logs include headless environment warnings: unavailable camera/authentication/
screencast services, a masked power-profiles-daemon, the location portal and
experimental flags inherited from the distribution. These are not theme
failures. The private session does not change the user's User Themes settings,
global accent or GDM.

## Calendar and notification refinements

Calendar month and weekday headings have no background; validation checks
alpha zero on the eight actual actors in the isolated session. The notification
divider uses 7% of the text color in both LTR and RTL, without changing other
borders or selected dates.

Notification and event cards share the `raised` surface, including empty event
cards. The isolated session compares their effective actor backgrounds and
checks that notification cards are opaque. The notification group container
remains transparent so each card retains its rounded corners.

## Dash to Dock / Ubuntu Dock

Additional validation uses the installed Ubuntu Dock version 105, which derives
from Dash to Dock:

```bash
python3 tools/visual_check.py --dock --output build/dock-validation
```

Validated again on 2026-10-06: **21 automated tests passed** and the native
dock run produced **33 screenshots**, including expanded and compact layouts.

The current check enables only Ubuntu Dock and the private QA fixture; no
Prisma companion extension is installed. It verifies 85% background opacity,
compares actual dock height with compact spacing disabled/enabled, checks
transparent icon backgrounds at rest and visible hover feedback, and captures
native active, checked, focus, focused and running states.

The native dock extension retains control of geometry and interaction states.
Theme CSS supplies its default translucent background. Activation configures
native fixed opacity at 0.85 and disables the dock's built-in theme; the
installer preserves compact mode, panel mode, dock position and icon size.

The previous companion-based validation is superseded by these checks. The
current results are recorded in `build/native-dock-validation/`.

## Limitations

Initial support was verified on Shell 50.1. Theme selection through User Themes
was tested with a simulated adapter to preserve the user's real selection;
the original selection tests did not activate the physical session. On
2026-10-06, the active Prisma installation was updated while preserving its
configuration, the obsolete helper was removed, and native dock opacity was
set to 0.85 without changing compact mode or position.

Disabled foregrounds and decorations use Adwaita opacities. The 4.5:1 guarantee
applies to opaque primary/secondary/accent text roles on resolved control
surfaces, not every interface pixel. Content, typography, scale and extensions
can affect visual perception.

## Compact icon padding correction (2026-10-06)

Compact mode now also reduces the inherited inner icon tile padding from 6px
to 2px and removes inner spacing, scoped to `.shrink`. The isolated run in
`build/compact-dock-validation/` produced 33 screenshots. Measured dock height
changed from 88px in normal mode to 63px in compact mode; the measured visible
icon tile width changed from 60px to 52px. Effective maximum inner padding was
6px and 2px respectively. Opacity and hover checks still passed.

## Split Quick Settings arrow segments (2026-10-06)

Arrow segments now use independent neutral and accent-tinted roles between
the existing bounded state surfaces, with separate hover, focus, active and
disabled colors. The shared Adwaita capsule outline and LTR/RTL geometry are
preserved. All 22 automated tests passed, including distinct segment colors
and 4.5:1 text contrast across dark, light and saturated palettes. The private
run in `build/split-buttons-validation/` produced 33 screenshots and verified
that each menu arrow differs from its main button across four theme variants.

## Reference color proportions (2026-10-06)

Calibrated with accent `#b087e5` and background `#262831`. Inactive controls
resolve to `#30333f`; selected controls to `#3b374d`; selected arrow segments
to `#4a4160`, one red-channel level from the sampled `#494160`. The formulas
remain relative to the configured colors rather than hardcoded widget colors.
All 23 tests passed, including exact reference control/selection colors,
arrow tolerance and contrast across extreme palettes. The private run in
`build/proportions-validation/` produced 33 screenshots covering LTR/RTL,
interaction states, light themes, the compact dock and the updated preset.

## Calendar typography (2026-10-06)

Date numbers, including today and adjacent-month dates, and the empty
Add World Clocks action use regular font weight. The isolated session in
`build/calendar-typography-validation/` produced 24 screenshots and verified
Pango font weight 400 on the actual date/action actors. Month and weekday
headings, existing world-clock titles and selected-date backgrounds retain
their existing styles.

## Inactive arrow surface (2026-10-06)

The inactive arrow now preserves the background hue, shifts HSL lightness by
7.1 percentage points and scales saturation by 1.03. With the current reference
background `#262831`, it resolves exactly to `#363846`. The selected arrow
formula is unchanged. All 23 tests passed, including the exact reference
color assertion and extreme-palette contrast checks; the private run in
`build/inactive-arrow-validation/` produced 24 screenshots without CSS errors.

## Optional solid accent selection (2026-10-06)

`--solid-accent` / `solid_accent: true` use the exact configured accent for
selected control backgrounds and the ordinary neutral foreground for their
text/icons. The tinted style remains the default; `--no-solid-accent` overrides
a JSON file that enables solid mode. Arrow segments and interaction states
remain distinct, including black/white accents. Links and ordinary accent
indicators keep their own roles.

All 25 automated tests passed, including boolean validation, precedence and
exact accent/neutral text roles. Direct installer flags and JSON disabling
were checked with a simulated installer. The isolated run in
`build/solid-accent-validation/` produced 26 screenshots and checked effective
selected button colors and neutral text in actual GNOME actors. Solid mode
intentionally prioritizes exact accent and foreground consistency over the
tinted mode's selected-control contrast guarantee.

## White foreground in solid mode (2026-10-06)

Solid-accent mode now uses opaque `#ffffff` for primary neutral and selected
control text/icons. The default tinted mode is unchanged. All 25 tests passed
and `build/white-text-validation/` contains 26 isolated screenshots; actor
checks confirm exact accent backgrounds and white foregrounds. The user's
font and antialiasing settings were preserved. No text shadow or blur rule was
found in the theme; both physical displays reported scale 1.0. A physical
font rendering issue was not reproduced or confirmed by isolated validation.
