#!/usr/bin/env python3
"""Capture real GNOME 50 widgets with private XDG paths and private D-Bus."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prisma.config import Config, load_config
from prisma.install import generate


def child(output, dock=False):
    settings = [
        ('org.gnome.shell', 'enabled-extensions', "['ubuntu-dock@ubuntu.com', 'prisma-qa@local']" if dock else "['prisma-qa@local']"),
        ('org.gnome.shell', 'disable-user-extensions', 'false'),
        ('org.gnome.shell', 'welcome-dialog-last-shown-version', "'50'"),
        ('org.gnome.desktop.background', 'picture-uri', "''"),
        ('org.gnome.desktop.background', 'picture-uri-dark', "''"),
        ('org.gnome.desktop.background', 'picture-options', "'none'"),
        ('org.gnome.desktop.background', 'primary-color', "'#35353c'"),
    ]
    if dock:
        settings += [
            ('org.gnome.shell.extensions.dash-to-dock', 'dock-fixed', 'true'),
            ('org.gnome.shell.extensions.dash-to-dock', 'dock-position', "'BOTTOM'"),
            ('org.gnome.shell.extensions.dash-to-dock', 'extend-height', 'false'),
            ('org.gnome.shell.extensions.dash-to-dock', 'apply-custom-theme', 'false'),
            ('org.gnome.shell.extensions.dash-to-dock', 'custom-background-color', 'false'),
            ('org.gnome.shell.extensions.dash-to-dock', 'transparency-mode', "'DEFAULT'"),
            ('org.gnome.shell.extensions.dash-to-dock', 'custom-theme-shrink', 'false'),
        ]
    for schema, key, value in settings:
        subprocess.run(['gsettings', 'set', schema, key, value], check=True)
    with (output / 'session.log').open('w') as log:
        process = subprocess.Popen(['gnome-shell', '--headless', '--wayland', '--no-x11',
                                    '--virtual-monitor', '1300x900', '--wayland-display', 'prisma-qa',
                                    '--mode', 'user'], stdout=log, stderr=subprocess.STDOUT)
        try:
            process.wait(timeout=55)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    report = json.loads((output / 'result.json').read_text())
    if report.get('error'):
        raise RuntimeError(report['error'])
    # Unrelated missing services in a headless session are kept in the log;
    # stylesheet warnings are failures, not silently ignored.
    log = (output / 'session.log').read_text()
    css_errors = [line for line in log.splitlines() if
                  any(text in line.lower() for text in ('theme parsing error', 'stylesheet parse', 'could not load image', 'failed to load image'))]
    if css_errors:
        raise RuntimeError('\n'.join(css_errors))
    print(f'{len(report["screenshots"])} capturas em {output}.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/visual-validation')
    parser.add_argument('--dock', action='store_true', help='validar também Ubuntu Dock instalado (base Dash to Dock)')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.child:
        child(output, args.dock)
        return
    for tool in ('gnome-shell', 'sassc', 'dbus-run-session', 'gsettings'):
        if not shutil.which(tool):
            parser.error(f'Ferramenta não encontrada: {tool}')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'result.json').unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='prisma-qa-') as temp:
        workspace = Path(temp)
        env = dict(os.environ)
        for key, directory in (('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                               ('XDG_CACHE_HOME', 'cache'), ('XDG_RUNTIME_DIR', 'runtime')):
            path = workspace / directory
            path.mkdir(mode=0o700)
            env[key] = str(path)
        env.update(LANG='C.UTF-8', LC_ALL='C.UTF-8', GSETTINGS_BACKEND='keyfile')
        for key in ('XDG_SESSION_ID', 'DBUS_SESSION_BUS_ADDRESS', 'DISPLAY', 'WAYLAND_DISPLAY'):
            env.pop(key, None)
        extension = workspace / 'data/gnome-shell/extensions/prisma-qa@local'
        extension.mkdir(parents=True)
        shutil.copyfile(ROOT / 'tools/qa-extension.js', extension / 'extension.js')
        (extension / 'metadata.json').write_text(json.dumps({
            'uuid': 'prisma-qa@local', 'name': 'Prisma private visual QA',
            'description': 'Private test fixture', 'shell-version': ['50'], 'session-modes': ['user'],
        }))
        themes = []
        reference = load_config(ROOT / 'presets/reference.json')
        for name, background, accent, panel in (
            ('reference', reference.background, reference.accent, reference.panel_background),
            ('solid-accent', reference.background, reference.accent, reference.panel_background),
            ('light', '#eeeeee', '#c08aff', '#eeeeee'),
            ('blue', '#26272e', '#3584e4', '#1e1f25'),
            ('light-panel', '#26272e', '#c08aff', '#eeeeee'),
        ):
            root = generate(workspace / name, Config(name, accent, background, panel, solid_accent=name == 'solid-accent'))
            themes.append({'name': name, 'css': str(root / 'gnome-shell/gnome-shell.css'),
                           'solid_accent': name == 'solid-accent', 'accent': accent})
        (extension / 'configuration.json').write_text(json.dumps({'output': str(output), 'themes': themes, 'dock': args.dock}))
        command = ['dbus-run-session', '--', sys.executable, str(Path(__file__).resolve()), '--child', '--output', str(output)]
        if args.dock:
            command.append('--dock')
        subprocess.run(command, env=env, check=True, timeout=65)


if __name__ == '__main__':
    main()
