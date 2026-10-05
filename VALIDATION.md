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
- Companion extension installation, third-party protection, next-login
  activation and removal when the last Prisma theme is removed.

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

This enables the dock and Prisma Dock only in the private session and produces
**31 screenshots**. Checks inspect effective actor colors, rather than just
CSS selectors. Button background alpha is zero in all tested states; icon
background alpha is zero in normal, active, checked, focus, focused and running
states. On hover, only the icon layer receives a subtle highlight with alpha
30/255 (12% in CSS, quantized by Shell). Companion styles are also verified to
unload when selecting the default theme. Screenshots show no permanent icon
backgrounds and a rounded hover highlight.

The companion is needed for extension-defined states: in GNOME 50, extension
style origins override even theme `!important` declarations. Adjustments are
restricted to the Dash to Dock / Ubuntu Dock container, preserving the
application grid, running indicators and badges. Dock position, geometry and
transparency settings remain controlled by the dock extension.

## Limitations

Initial support was verified on Shell 50.1. Theme selection through User Themes
was tested with a simulated adapter to preserve the user's real selection;
activation in the physical session was not performed.

Disabled foregrounds and decorations use Adwaita opacities. The 4.5:1 guarantee
applies to opaque primary/secondary/accent text roles on resolved control
surfaces, not every interface pixel. Content, typography, scale and extensions
can affect visual perception.
