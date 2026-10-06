"""Compile official GNOME 50.1 SCSS with explicit Prisma palette roles."""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from .palette import Palette

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / 'vendor/gnome-shell-50.1/theme'

# Injected after upstream colors, before drawing functions and widgets. Keeping
# vendor sources unchanged makes comparison and future version updates simple.
ROLE_OVERRIDES = '''
$base_color: $prisma_surface;
$bg_color: $prisma_surface;
$fg_color: $prisma_text;
$osd_bg_color: rgba($prisma_osd, $prisma_osd_opacity);
$osd_fg_color: $prisma_osd_text;
$system_base_color: $prisma_surface;
$system_bg_color: $prisma_surface;
$system_fg_color: $prisma_text;
$system_overlay_bg_color: $prisma_raised;
$panel_bg_color: $prisma_panel;
$panel_fg_color: $prisma_panel_text;
$panel_border_color: transparent;
$card_bg_color: $prisma_raised;
$borders_color: rgba($prisma_text, .15);
$outer_borders_color: rgba($prisma_text, .12);
$osd_borders_color: rgba($prisma_osd_text, .12);
$osd_outer_borders_color: rgba($prisma_osd_text, .12);
$system_borders_color: rgba($prisma_text, .15);
$system_insensitive_fg_color: rgba($prisma_text, .5);
$insensitive_fg_color: rgba($prisma_text, .5);
$card_insensitive_fg_color: rgba($prisma_text, .5);
$insensitive_bg_color: $prisma_control;
$insensitive_borders_color: rgba($prisma_text, .08);
$checked_bg_color: $prisma_selected;
$checked_fg_color: $prisma_selected_text;
$hover_bg_color: $prisma_hover;
$hover_fg_color: $prisma_text;
$active_bg_color: $prisma_pressed;
$active_fg_color: $prisma_text;
$focus_border_opacity: 0;
$accent_color: $prisma_accent_text;
$accent_borders_color: $prisma_accent;
$link_color: $prisma_accent_text;
$link_visited_color: rgba($prisma_accent_text, .7);
'''

BUTTON_ROLES = '''
  // Prisma: use bounded, contrast-tested roles for ordinary surfaces.
  @if $tc == $prisma_text and $style != 'notification' and $style != 'lockscreen' {
    $button_bg_color: if($style == 'flat', $c, $prisma_control);
    @if $style == 'card' { $button_bg_color: $prisma_raised; }
    $hover_button_bg_color: $prisma_hover;
    $active_button_bg_color: $prisma_pressed;
    $checked_button_bg_color: $prisma_pressed;
    $insensitive_button_bg_color: $prisma_control;
    $active_hover_button_bg_color: $prisma_pressed;
    $checked_hover_button_bg_color: $prisma_hover;
    $checked_active_button_bg_color: $prisma_pressed;
  }
  @if $style == 'default' and $c == $prisma_selected {
    $button_bg_color: $prisma_selected;
    $hover_button_bg_color: $prisma_selected_hover;
    $active_button_bg_color: $prisma_selected_pressed;
    $checked_button_bg_color: $prisma_selected;
    $insensitive_button_bg_color: $prisma_selected;
    $active_hover_button_bg_color: $prisma_selected_pressed;
    $checked_hover_button_bg_color: $prisma_selected_hover;
    $checked_active_button_bg_color: $prisma_selected_pressed;
  }
'''

# Geometry stays upstream. These rules override color-only widget exceptions.
WIDGET_ROLES = '''
.quick-toggle:checked, .quick-toggle-menu-button:checked,
.button.default, .icon-button.default,
.modal-dialog .modal-dialog-button:default {
  color: $prisma_selected_text;
  background-color: $prisma_selected;
  &:hover, &:active, &:focus { color: $prisma_selected_text; }
  &:hover { background-color: $prisma_selected_hover; }
  &:active, &:active:hover { background-color: $prisma_selected_pressed; }
  &:focus { background-color: $prisma_selected_focus; }
  &:focus:hover { background-color: $prisma_selected_hover; }
  &:focus:active { background-color: $prisma_selected_pressed; }
  &:insensitive { color: rgba($prisma_selected_text, .5); background-color: $prisma_selected; }
}
.quick-toggle:checked .quick-toggle-title,
.quick-toggle:checked .quick-toggle-subtitle,
.quick-toggle:checked StIcon { color: inherit; }
.quick-toggle-menu .header .icon.active {
  background-color: $prisma_selected; color: $prisma_selected_text;
}
.quick-toggle-has-menu .quick-toggle-menu-button {
  background-color: $prisma_menu_control; color: $prisma_text;
  &:hover { background-color: $prisma_menu_hover; }
  &:focus { background-color: $prisma_menu_hover; }
  &:active { background-color: $prisma_menu_pressed; }
  &:insensitive { background-color: $prisma_menu_control; color: rgba($prisma_text, .5); }
  &:checked { background-color: $prisma_menu_selected; color: $prisma_selected_text; }
  &:checked:hover { background-color: $prisma_menu_selected_hover; }
  &:checked:focus { background-color: $prisma_menu_selected_focus; }
  &:checked:focus:hover { background-color: $prisma_menu_selected_hover; }
  &:checked:active, &:checked:active:hover, &:checked:active:focus { background-color: $prisma_menu_selected_pressed; }
  &:checked:insensitive { background-color: $prisma_menu_selected; color: rgba($prisma_selected_text, .5); }
}
.toggle-switch:checked .handle { background-color: $prisma_selected_text; }
.quick-toggle-has-menu .quick-toggle-separator { background-color: rgba($prisma_text, .1); }
.quick-toggle-has-menu:checked .quick-toggle-separator { background-color: rgba($prisma_selected_text, .12); }
.quick-slider .slider, .slider {
  color: $prisma_secondary_text;
  -barlevel-background-color: rgba($prisma_text, .35);
  -barlevel-active-background-color: $prisma_accent;
  &:hover { color: $prisma_text; }
}
.osd-window .level { -barlevel-active-background-color: $prisma_osd_accent; }
.quick-toggle-menu, .popup-sub-menu { background-color: $prisma_raised; }
.message { background-color: $prisma_raised; color: $prisma_text; }
// Paint each rounded card, not the rectangular notification group container.
.message-notification-group, .message-notification-group:hover,
.message-notification-group:active, .message-notification-group:active:hover {
  background-color: transparent; color: $prisma_text;
}
// Empty event cards retain the same surface as notification cards.
.events-button:insensitive { background-color: $prisma_raised; }
.message:hover { background-color: $prisma_hover; }
.message:active { background-color: $prisma_pressed; }
.device-subtitle { color: $prisma_secondary_text; }
// Calendar headings are labels, not filled pills. Keep date selection intact.
.calendar .calendar-day-heading,
.calendar .calendar-month-header .calendar-month-label {
  background-color: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
}
// Use regular weight for date numbers and the empty clocks action.
.calendar .calendar-day,
.world-clocks-button .world-clocks-header.no-world-clocks {
  font-weight: normal;
}
// A subtle divider, scoped to the date menu (LTR and RTL share this color).
.message-list { border-color: rgba($prisma_text, .07); }
// Local recolored event markers make today's indicator readable in light themes.
.calendar .calendar-day.calendar-today.calendar-day-with-events {
  background-image: url("calendar-today-accent.svg") !important;
}
'''


# Dash to Dock and Ubuntu Dock share this container ID. Scope backgrounds to
# their icon layers; never clear running dots, badges or the app-grid tiles.
DOCK_ROLES = r"""
#dashtodockContainer #dash .dash-background {
  background-color: rgba($prisma_surface, .85);
}
// Compact spacing must also shrink the inner Adwaita icon tile. The dock
// extension reduces button padding, but leaves this inherited 6px layer alone.
#dashtodockContainer.shrink #dash .dash-item-container .overview-icon {
  padding: 2px;
  spacing: 0;
  border-radius: 12px;
}
#dashtodockContainer #dash .dash-item-container {
  .app-well-app, .overview-tile, .show-apps, .overview-icon {
    background-color: transparent !important;
    background-image: none !important;
    background-gradient-start: transparent !important;
    background-gradient-end: transparent !important;
    border-color: transparent !important;
    box-shadow: none !important;
  }
  // A single rounded highlight on hover, with no permanent icon tile.
  .app-well-app:hover .overview-icon,
  .overview-tile:hover .overview-icon,
  .show-apps:hover .overview-icon {
    background-color: rgba($prisma_text, 0.12) !important;
  }
  // Keep keyboard focus visible without introducing an icon background.
  .app-well-app:focus .overview-icon,
  .overview-tile:focus .overview-icon,
  .show-apps:focus .overview-icon {
    box-shadow: inset 0 0 0 2px $prisma_accent !important;
  }
}
"""


def prepare_sources(directory, palette):
    shutil.copytree(UPSTREAM, directory)
    for path in directory.rglob('*.scss'):
        text = path.read_text()
        text = text.replace('-st-accent-fg-color', '$prisma_selected_text')
        text = text.replace('-st-accent-color', '$prisma_accent')
        for function in ('mix', 'lighten', 'darken', 'transparentize'):
            text = text.replace('st-' + function + '(', function + '(')
        # Filled accent backgrounds use tint; focus rings and slider fills
        # keep the strong indicator accent. Foregrounds stay contrast-tested.
        text = re.sub(r'(background(?:-color)?:\s*)\$prisma_accent\b', r'\1$prisma_selected', text)
        text = re.sub(r'(background(?:-color)?:\s*)lighten\(\$prisma_accent,\s*[^)]+\)', r'\1$prisma_selected_hover', text)
        text = re.sub(r'(background(?:-color)?:\s*)darken\(\$prisma_accent,\s*[^)]+\)', r'\1$prisma_selected_pressed', text)
        text = re.sub(r'(\bcolor:\s*)(?:lighten|darken)\(\$prisma_selected_text,\s*[^)]+\)', r'\1$prisma_selected_text', text)
        text = text.replace('@if $always_dark {', "@if $always_dark and $variant == 'dark' {")
        if path.name == '_common.scss':
            text = text.replace('$c:$prisma_accent, $tc:$prisma_selected_text',
                                '$c:$prisma_selected, $tc:$prisma_selected_text')
        if path.name == '_drawing.scss':
            needle = '  // normal style\n'
            if text.count(needle) != 1:
                raise ValueError('Base upstream incompatível: ponto de integração dos botões mudou.')
            text = text.replace(needle, BUTTON_ROLES + needle)
            # Normal panel states use their independent resolved role colors.
            text = text.replace('  @include panel_button_fill($fill);', '''
  @if $fg == $prisma_panel_text and $style != 'filled' {
    $hover_fill: $prisma_panel_hover;
    $active_fill: $prisma_panel_pressed;
    $active_hover_fill: $prisma_panel_pressed;
  }
  @include panel_button_fill($fill);''')
        text = re.sub(r'resource:///org/gnome/shell/theme/', '', text)
        path.write_text(text)
    entry = ("$variant: '" + ('light' if palette.light else 'dark') + "';\n$contrast: 'normal';\n" +
             palette.sass() + '@import "gnome-shell-sass/colors";\n' + ROLE_OVERRIDES +
             '@import "gnome-shell-sass/drawing";\n@import "gnome-shell-sass/common";\n' +
             '@import "gnome-shell-sass/widgets";\n' + WIDGET_ROLES + DOCK_ROLES)
    (directory / 'prisma.scss').write_text(entry)


def compile_theme(destination, config):
    """Write a complete theme root into a new staging directory."""
    palette = Palette(config)
    shell = destination / 'gnome-shell'
    shell.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='prisma-sass-') as temp:
        source = Path(temp) / 'theme'
        prepare_sources(source, palette)
        result = subprocess.run(['sassc', '-t', 'expanded', str(source / 'prisma.scss')],
                                check=True, capture_output=True, text=True, timeout=60)
        css = '/* Prisma — GNOME Shell 50.1; see UPSTREAM.md for licensing. */\n' + result.stdout
    if re.search(r'-st-accent(?:-fg)?-color|st-(?:mix|lighten|darken|transparentize)\(|\$prisma_|resource:///org/gnome/shell/theme/', css):
        raise ValueError('O CSS contém cores ou recursos não resolvidos.')
    for name in ('LICENSE', 'UPSTREAM.md'):
        shutil.copyfile(ROOT / name, destination / name)
    shutil.copytree(ROOT / 'licenses', destination / 'licenses')
    for asset in sorted(UPSTREAM.glob('*.svg')):
        shutil.copyfile(asset, shell / asset.name)
    event = (shell / 'calendar-today.svg').read_text()
    event = event.replace('#ffffff', palette.roles['selected_text'].css()).replace('#fff', palette.roles['selected_text'].css())
    (shell / 'calendar-today-accent.svg').write_text(event)
    for asset in ('calendar-today.svg', 'calendar-today-light.svg'):
        text = (shell / asset).read_text()
        text = re.sub(r'fill:#[0-9a-fA-F]+', 'fill:' + palette.roles['text'].css(), text)
        (shell / asset).write_text(text)
    (shell / 'gnome-shell.css').write_text(css)
    (shell / 'prisma.json').write_text(json.dumps({
        'project': 'Prisma', 'schema': 1, 'gnome_shell': '50.1',
        'upstream_archive_sha256': '1b47760172c14f3f4edd1c9aff365f4de45583517bf0f80df4d3acbd4e4cb294',
        'config': config.to_dict(), 'palette': palette.to_dict(), 'osd_opacity': palette.osd_opacity,
    }, indent=2, sort_keys=True) + '\n')
    return palette
