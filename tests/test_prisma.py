import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from prisma.config import Config, load_config
from prisma.palette import Palette, Color
from prisma.install import Installer, generate, owned, owned_companion, DOCK_EXTENSION, UserThemes


class ConfigTests(unittest.TestCase):
    def test_defaults_and_panel_fallback(self):
        self.assertEqual(Config().panel_background, Config().background)
        self.assertEqual(Config(background='ABCDEF').background, '#abcdef')
        self.assertEqual(Config(background='ABCDEF').panel_background, '#abcdef')

    def test_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            path.write_text(json.dumps({'name': 'Saved', 'accent': '112233', 'background': '445566', 'panel_background': '778899'}))
            config = load_config(path, name='Override', accent='aabbcc')
            self.assertEqual(config.to_dict(), {'name': 'Override', 'accent': '#aabbcc', 'background': '#445566', 'panel_background': '#778899', 'solid_accent': False})

    def test_solid_accent_config_and_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'solid.json'
            path.write_text(json.dumps({'solid_accent': True}))
            self.assertTrue(load_config(path).solid_accent)
            self.assertFalse(load_config(path, solid_accent=False).solid_accent)
            for value in ('true', 1, None):
                path.write_text(json.dumps({'solid_accent': value}))
                with self.assertRaises(ValueError):
                    load_config(path)
        with self.assertRaises(ValueError):
            Config(solid_accent='yes')

    def test_invalid_input(self):
        for value in ('../x', '..', '/tmp/x', 'a/b', '', 'á', 'x'*65):
            with self.subTest(name=value), self.assertRaises(ValueError):
                Config(name=value)
        for value in ('#fff', '#ffffffaa', 'red', 7, True, '#gggggg'):
            with self.subTest(color=value), self.assertRaises(ValueError):
                Config(accent=value)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            for content in ('[]', '{"unknown": "x"}', '{"background": null}', '{broken'):
                path.write_text(content)
                with self.subTest(json=content), self.assertRaises(ValueError):
                    load_config(path)


class PaletteTests(unittest.TestCase):
    def test_solid_accent_uses_exact_accent_and_neutral_text(self):
        for background in ('#262831', '#ffffff', '#000000'):
            for accent in ('#b087e5', '#feac8f', '#ffffff', '#000000'):
                p = Palette(Config(background=background, accent=accent, solid_accent=True)).roles
                self.assertEqual(p['selected'].css(), accent)
                self.assertEqual(p['selected_text'], p['text'])
                self.assertEqual(p['selected_text'].css(), '#ffffff')
                self.assertNotEqual(p['menu_selected'], p['selected'])
                self.assertNotEqual(p['selected_hover'], p['selected_pressed'])
        normal = Palette(Config()).roles
        self.assertEqual(normal['selected_text'], normal['accent_text'])

    def test_reference_button_proportions(self):
        roles = Palette(Config(accent='#b087e5', background='#262831')).roles
        self.assertEqual(roles['control'].css(), '#30333f')
        self.assertEqual(roles['menu_control'].css(), '#363846')
        self.assertEqual(roles['selected'].css(), '#3b374d')
        # A scalar accent blend lands within one RGB level of #494160.
        expected = Color.hex('#494160')
        self.assertLessEqual(max(abs(a - b) for a, b in zip(roles['menu_selected'].rgb, expected.rgb)), 1)

    def test_menu_segments_are_distinct_and_readable(self):
        for background in ('#000000', '#ffffff', '#26272e', '#ff0000', '#00ff00', '#0000ff', '#757575'):
            for accent in ('#000000', '#ffffff', '#bf8ffe', '#feac8f'):
                with self.subTest(background=background, accent=accent):
                    roles = Palette(Config(background=background, accent=accent)).roles
                    self.assertNotEqual(roles['menu_control'], roles['control'])
                    self.assertNotEqual(roles['menu_selected'], roles['selected'])
                    for name in ('menu_control', 'menu_hover', 'menu_pressed'):
                        self.assertGreaterEqual(roles['text'].contrast(roles[name]), 4.5)
                    for name in ('menu_selected', 'menu_selected_hover', 'menu_selected_pressed', 'menu_selected_focus'):
                        self.assertGreaterEqual(roles['accent_text'].contrast(roles[name]), 4.5)

    def test_extreme_palettes_contrast_and_states(self):
        for background in ('#000000', '#ffffff', '#26272e', '#eeeeee', '#ff0000', '#00ff00', '#0000ff', '#757575', '#7a7a7a'):
            for accent in ('#000000', '#ffffff', '#c08aff', '#00ff00', '#ff0000'):
                with self.subTest(background=background, accent=accent):
                    p = Palette(Config(background=background, accent=accent)).roles
                    neutral = [p[name] for name in ('surface', 'raised', 'control', 'hover', 'pressed')]
                    selected = [p[name] for name in ('selected', 'selected_hover', 'selected_pressed', 'selected_focus')]
                    for surface in neutral:
                        self.assertGreaterEqual(p['text'].contrast(surface), 4.5)
                        self.assertGreaterEqual(p['secondary_text'].contrast(surface), 4.5)
                        self.assertGreaterEqual(p['accent'].contrast(surface), 3)
                    for surface in neutral + selected:
                        self.assertGreaterEqual(p['accent_text'].contrast(surface), 4.5)
                    for surface in ('panel', 'panel_hover', 'panel_pressed'):
                        self.assertGreaterEqual(p['panel_text'].contrast(p[surface]), 4.5)
                    self.assertNotEqual(p['control'], p['hover'])
                    self.assertNotEqual(p['hover'], p['pressed'])
                    if accent != background:
                        self.assertNotEqual(p['selected'], p['selected_hover'])

    def test_osd_is_darker_with_independent_contrast(self):
        for background in ('#000000', '#26272e', '#ffffff', '#ff0000', '#7a7a7a'):
            with self.subTest(background=background):
                palette = Palette(Config(background=background))
                roles = palette.roles
                self.assertLessEqual(roles['osd'].luminance, roles['surface'].luminance)
                if background != '#000000':
                    self.assertLess(roles['osd'].luminance, roles['surface'].luminance)
                self.assertEqual(palette.osd_opacity, .95)
                self.assertGreaterEqual(roles['osd_text'].contrast(roles['osd']), 4.5)
                self.assertGreaterEqual(roles['osd_accent'].contrast(roles['osd']), 3)

    def test_palette_independence(self):
        first = Palette(Config()).to_dict()
        accent = Palette(Config(accent='#ff7700')).to_dict()
        panel = Palette(Config(panel_background='#ffffff')).to_dict()
        for name in ('surface', 'control', 'hover', 'pressed', 'text', 'raised'):
            self.assertEqual(first[name], accent[name])
        for name in first:
            if not name.startswith('panel'):
                self.assertEqual(first[name], panel[name])


class DockSettingsTests(unittest.TestCase):
    def test_native_settings_preserve_compact_and_position(self):
        settings = UserThemes()
        with patch.object(settings, 'run', return_value='org.gnome.shell.extensions.dash-to-dock') as run:
            self.assertTrue(settings.configure_dock(Config(background='#123456')))
        writes = [call.args for call in run.call_args_list if call.args[:2] == ('gsettings', 'set')]
        self.assertIn(('gsettings', 'set', 'org.gnome.shell.extensions.dash-to-dock', 'background-opacity', '0.85'), writes)
        self.assertIn(('gsettings', 'set', 'org.gnome.shell.extensions.dash-to-dock', 'apply-custom-theme', 'false'), writes)
        self.assertFalse(any(call[3] in ('custom-theme-shrink', 'extend-height', 'dock-position', 'dash-max-icon-size') for call in writes))
        with patch.object(settings, 'run', return_value=''):
            self.assertFalse(settings.configure_dock(Config()))


class Settings:
    def __init__(self, current='', available=True):
        self.value, self.enabled, self.calls = current, available, []
    def current(self):
        return self.value
    def available(self):
        return self.enabled
    def configure_dock(self, config):
        return True
    def run(self, *args):
        return ''
    def disable_dock(self):
        pass
    def set(self, value):
        self.value = value
        self.calls.append(value)


@unittest.skipUnless(shutil.which('sassc'), 'sassc não disponível')
class BuildInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = Settings()
        self.installer = Installer(self.root / 'themes', self.settings)
    def tearDown(self):
        self.temp.cleanup()

    def test_build_reproducible_and_assets_resolved(self):
        a, b = self.root / 'a', self.root / 'b'
        generate(a, Config())
        generate(b, Config())
        for path in a.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (b / path.relative_to(a)).read_bytes())
        css = (a / 'gnome-shell/gnome-shell.css').read_text()
        self.assertNotIn('-st-accent-color', css)
        self.assertNotIn('$prisma_', css)
        self.assertNotIn('st-mix(', css)
        self.assertIn('border-radius: 999px', css)
        import re
        for asset in re.findall(r'url\("([^"\)]+)"\)', css):
            self.assertTrue((a / 'gnome-shell' / asset).is_file(), asset)
        self.assertIn('#c01c28', css) # upstream screencast/error red

    def test_selected_widgets_have_readable_foregrounds(self):
        import re
        for background in ('#26272e', '#ffffff', '#ff0000', '#757575'):
            path = self.root / background[1:]
            generate(path, Config(background=background))
            css = (path / 'gnome-shell/gnome-shell.css').read_text()
            count = 0
            for selector, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
                if not any(widget in selector for widget in ('.check-box:checked', '.toggle-switch:checked', '.quick-toggle:checked')):
                    continue
                fg = re.search(r'(?:^|;)\s*color:\s*(#[0-9a-fA-F]{6})', body)
                bg = re.search(r'(?:^|;)\s*background(?:-color)?:\s*(#[0-9a-fA-F]{6})', body)
                if fg and bg:
                    self.assertGreaterEqual(Color.hex(fg[1]).contrast(Color.hex(bg[1])), 4.5, selector)
                    count += 1
            self.assertGreater(count, 2)

    def test_osd_css_has_translucent_darker_surface(self):
        import re
        target = generate(self.root / 'osd', Config())
        css = (target / 'gnome-shell/gnome-shell.css').read_text()
        rules = re.findall(r'([^{}]+)\{([^{}]*)\}', css)
        osd = [body for selector, body in rules if '.osd-window' in selector and
               'background-color:' in body]
        self.assertTrue(any('rgba(29, 30, 35, 0.95)' in body for body in osd), osd)
        metadata = json.loads((target / 'gnome-shell/prisma.json').read_text())
        self.assertEqual(metadata['osd_opacity'], .95)

    def test_build_light_and_panel_independence(self):
        a, b = self.root / 'a', self.root / 'b'
        generate(a, Config(background='#ffffff'))
        generate(b, Config(background='#ffffff', panel_background='#000000'))
        import re
        css_a = (a / 'gnome-shell/gnome-shell.css').read_text()
        css_b = (b / 'gnome-shell/gnome-shell.css').read_text()
        rules_a = re.findall(r'([^{}]+)\{([^{}]*)\}', css_a)
        rules_b = re.findall(r'([^{}]+)\{([^{}]*)\}', css_b)
        self.assertEqual(len(rules_a), len(rules_b))
        for (selector_a, rule_a), (selector_b, rule_b) in zip(rules_a, rules_b):
            self.assertEqual(selector_a, selector_b)
            if rule_a != rule_b:
                self.assertIn('#panel', selector_a)

    def test_install_update_coexist_remove(self):
        path = self.installer.install(Config())
        self.assertTrue(owned(path))
        self.assertEqual(self.settings.calls, [])
        self.installer.install(Config(accent='#ff8800'), activate=True)
        self.assertEqual(self.settings.value, 'Prisma')
        self.installer.install(Config(name='Other'))
        self.installer.install(Config(), activate=True)
        self.assertEqual(self.settings.calls[-2:], ['', 'Prisma'])
        self.installer.remove('Prisma')
        self.assertEqual(self.settings.value, '')
        self.assertFalse(path.exists())
        self.assertTrue((path.parent / 'Other').exists())

    def test_foreign_and_symlinks_protected(self):
        path = self.root / 'themes/Prisma'
        path.mkdir(parents=True)
        sentinel = path / 'important'
        sentinel.write_text('keep')
        with self.assertRaises(ValueError):
            self.installer.install(Config())
        with self.assertRaises(ValueError):
            self.installer.remove('Prisma')
        self.assertEqual(sentinel.read_text(), 'keep')
        link = self.root / 'link'
        link.symlink_to(path, target_is_directory=True)
        with self.assertRaises(ValueError):
            generate(link, Config())
        self.assertTrue(link.is_symlink())

    def test_failed_build_keeps_installed_theme(self):
        path = self.installer.install(Config())
        before = (path / 'gnome-shell/gnome-shell.css').read_bytes()
        with patch('prisma.install.compile_theme', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                self.installer.install(Config(accent='#0088ff'))
        self.assertEqual(before, (path / 'gnome-shell/gnome-shell.css').read_bytes())

    def test_failed_commit_restores_previous_theme(self):
        path = self.installer.install(Config())
        before = (path / 'gnome-shell/prisma.json').read_bytes()
        rename = Path.rename
        def failing(src, target):
            if src.name == 'new':
                raise OSError('failed rename')
            return rename(src, target)
        with patch.object(Path, 'rename', failing):
            with self.assertRaises(OSError):
                self.installer.install(Config(accent='#0088ff'))
        self.assertEqual(before, (path / 'gnome-shell/prisma.json').read_bytes())

    def test_no_extension_generated_or_installed(self):
        path = self.installer.install(Config())
        self.assertFalse((path / 'extensions').exists())
        self.assertFalse((path / 'gnome-shell/prisma-dock.css').exists())
        self.assertFalse(self.installer.extensions_dir.exists())

    def test_owned_legacy_extension_removed_on_update(self):
        companion = self.installer.extensions_dir / DOCK_EXTENSION
        companion.mkdir(parents=True)
        (companion / 'prisma.json').write_text(json.dumps({'project': 'Prisma', 'component': 'dock', 'schema': 1}))
        (companion / 'extension.js').write_text('legacy')
        self.installer.install(Config())
        self.assertFalse(companion.exists())

    def test_foreign_legacy_extension_is_preserved(self):
        companion = self.installer.extensions_dir / DOCK_EXTENSION
        companion.mkdir(parents=True)
        (companion / 'important').write_text('keep')
        self.installer.install(Config())
        self.assertEqual((companion / 'important').read_text(), 'keep')

    def test_missing_user_themes_keeps_install(self):
        self.settings.enabled = False
        path = self.installer.install(Config(), activate=True)
        self.assertTrue(owned(path))
        self.assertEqual(self.settings.calls, [])

    def test_failed_reset_prevents_removal(self):
        path = self.installer.install(Config())
        self.settings.value = 'Prisma'
        with patch.object(self.settings, 'set', side_effect=OSError('no session')):
            with self.assertRaises(OSError):
                self.installer.remove('Prisma')
        self.assertTrue(path.exists())

    def test_activation_failure_restores_previous_selection(self):
        self.settings.value = 'Prisma'
        original = self.settings.set
        failures = [False, True, False]
        def flaky(value):
            if failures.pop(0):
                raise OSError('failed activation')
            original(value)
        with patch.object(self.settings, 'set', flaky):
            path = self.installer.install(Config(), activate=True)
        self.assertTrue(owned(path))
        self.assertEqual(self.settings.value, 'Prisma')
