"""Independent surface, accent and panel roles; sRGB contrast calculations."""
import colorsys
from dataclasses import dataclass


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

    @classmethod
    def hex(cls, value):
        return cls(*(int(value[i:i+2], 16) for i in (1, 3, 5)))

    def css(self):
        return '#%02x%02x%02x' % (self.r, self.g, self.b)

    def mix(self, other, amount):
        return Color(*(round(a * (1 - amount) + b * amount)
                       for a, b in zip(self.rgb, other.rgb)))

    @property
    def rgb(self):
        return self.r, self.g, self.b

    @property
    def luminance(self):
        linear = [c/255/12.92 if c/255 <= .04045 else ((c/255+.055)/1.055)**2.4 for c in self.rgb]
        return sum(a*b for a, b in zip(linear, (.2126, .7152, .0722)))

    def contrast(self, other):
        lo, hi = sorted((self.luminance, other.luminance))
        return (hi + .05) / (lo + .05)


BLACK, WHITE = Color(0, 0, 0), Color(255, 255, 255)


def contrasting(color, surfaces, minimum=4.5):
    """Keep hue/saturation and find the closest lightness meeting every surface."""
    if min(color.contrast(bg) for bg in surfaces) >= minimum:
        return color
    h, light, s = colorsys.rgb_to_hls(*(v/255 for v in color.rgb))
    choices = []
    for step in range(1001):
        l = step/1000
        candidate = Color(*(round(v*255) for v in colorsys.hls_to_rgb(h, l, s)))
        if min(candidate.contrast(bg) for bg in surfaces) >= minimum:
            choices.append((abs(l-light), l, candidate))
    if not choices:
        raise ValueError('Não foi possível obter contraste para a paleta.')
    return min(choices, key=lambda item: item[:2])[2]


class Palette:
    def __init__(self, config):
        bg, accent, panel = map(Color.hex, (config.background, config.accent, config.panel_background))
        # The 0.179 threshold maximizes the available black/white contrast.
        self.light = bg.luminance > .179
        target = BLACK if self.light else WHITE
        # Mixing toward a neutral endpoint yields distinct states even at pure
        # white/black, without hue jumps from clamping HSL lightness.
        # Avoid crossing the black/white contrast boundary at midtones.
        ink = BLACK if self.light else WHITE
        if bg.mix(target, .14).contrast(ink) < 4.5:
            target = WHITE if self.light else BLACK
        surfaces = {name: bg.mix(target, amount) for name, amount in
                    (('surface', 0), ('raised', .04), ('control', .06),
                     ('hover', .10), ('pressed', .14))}
        neutral_surfaces = list(surfaces.values())
        text = contrasting(bg.mix(target, .76 if not self.light else .88), neutral_surfaces)
        tint = accent if accent != bg else contrasting(accent, [bg], 3)
        selected = {name: bg.mix(tint, amount) for name, amount in
                    (('selected', .16), ('selected_hover', .21), ('selected_pressed', .26), ('selected_focus', .19))}
        # Bound tint on middle-luminance or saturated inputs so all controls
        # remain readable with the same foreground hue. Retain as much tint
        # as possible, mixing toward the safe endpoint only when needed.
        safe = WHITE if ink == BLACK else BLACK
        for name, surface in selected.items():
            for step in range(101):
                candidate = surface.mix(safe, step/100)
                if candidate.contrast(ink) >= 4.5:
                    selected[name] = candidate
                    break
        if selected['selected_hover'] == selected['selected']:
            selected['selected_hover'] = selected['selected'].mix(safe, .04)
        if selected['selected_pressed'] in (selected['selected'], selected['selected_hover']):
            selected['selected_pressed'] = selected['selected_hover'].mix(safe, .04)
        accent_text = contrasting(accent, neutral_surfaces + list(selected.values()))
        panel_target = BLACK if panel.luminance > .179 else WHITE
        panel_ink = BLACK if panel.luminance > .179 else WHITE
        if panel.mix(panel_target, .17).contrast(panel_ink) < 4.5:
            panel_target = WHITE if panel_ink == BLACK else BLACK
        panel_surfaces = [panel.mix(panel_target, amount) for amount in (0, .10, .17)]
        panel_text = contrasting(panel.mix(panel_target, .88), panel_surfaces)
        # OSD surfaces keep the base hue/saturation, with HSL lightness
        # reduced by four percentage points. Black is the lower bound.
        h, lightness, saturation = colorsys.rgb_to_hls(*(v / 255 for v in bg.rgb))
        osd = Color(*(round(v * 255) for v in
                      colorsys.hls_to_rgb(h, max(0, lightness - .04), saturation)))
        self.osd_opacity = .95
        self.roles = {**surfaces, **selected, 'text': text,
                      'secondary_text': contrasting(bg.mix(target, .65), neutral_surfaces),
                      'accent': contrasting(accent, neutral_surfaces, 3), 'accent_text': accent_text,
                      'osd': osd, 'osd_text': contrasting(text, [osd]),
                      'osd_accent': contrasting(accent, [osd], 3),
                      'panel': panel, 'panel_text': panel_text,
                      'panel_hover': panel_surfaces[1], 'panel_pressed': panel_surfaces[2]}

    def to_dict(self):
        return {name: value.css() for name, value in self.roles.items()}

    def sass(self):
        roles = self.to_dict()
        return '\n'.join(f'$prisma_{name}: {value};' for name, value in roles.items()) + '\n' + f'$prisma_osd_opacity: {self.osd_opacity};\n'
