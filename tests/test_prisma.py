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
            self.assertEqual(config.to_dict(), {'name': 'Override', 'accent': '#aabbcc', 'background': '#445566', 'panel_background': '#778899'})

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


class CompanionSettingsTests(unittest.TestCase):
    def test_new_extension_activation_handles_typed_empty_lists(self):
        import ast
        state = {'enabled-extensions': ['other@local'], 'disabled-extensions': []}
        def command(*args):
            if args[0] == 'gnome-extensions':
                raise subprocess.CalledProcessError(1, args)
            key = args[3]
            if args[1] == 'get':
                return repr(state[key]) if state[key] else '@as []'
            state[key] = ast.literal_eval(args[4])
            return ''
        settings = UserThemes()
        with patch.object(settings, 'run', side_effect=command):
            self.assertFalse(settings.enable_dock())
            self.assertFalse(settings.enable_dock())
            self.assertEqual(state['enabled-extensions'], ['other@local', DOCK_EXTENSION])
            self.assertEqual(state['disabled-extensions'], [])
            settings.disable_dock()
            self.assertEqual(state['enabled-extensions'], ['other@local'])


class Settings:
    def __init__(self, current='', available=True):
        self.value, self.enabled, self.calls = current, available, []
    def current(self):
        return self.value
    def available(self):
        return self.enabled
    def enable_dock(self):
        return True
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

    def test_companion_install_coexistence_and_last_theme_cleanup(self):
        self.installer.install(Config())
        companion = self.installer.extensions_dir / DOCK_EXTENSION
        self.assertTrue(owned_companion(companion))
        self.assertTrue((companion / 'extension.js').is_file())
        self.installer.install(Config(name='Second'))
        self.installer.remove('Prisma')
        self.assertTrue(companion.exists())
        self.installer.remove('Second')
        self.assertFalse(companion.exists())

    def test_foreign_companion_prevents_overwriting_theme(self):
        companion = self.installer.extensions_dir / DOCK_EXTENSION
        companion.mkdir(parents=True)
        (companion / 'important').write_text('keep')
        with self.assertRaises(ValueError):
            self.installer.install(Config())
        self.assertFalse((self.installer.themes_dir / 'Prisma').exists())
        self.assertEqual((companion / 'important').read_text(), 'keep')

    def test_companion_activation_next_login_preserves_theme(self):
        with patch.object(self.settings, 'enable_dock', return_value=False):
            path = self.installer.install(Config(), activate=True)
        self.assertTrue(owned(path))
        self.assertEqual(self.settings.value, 'Prisma')

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
