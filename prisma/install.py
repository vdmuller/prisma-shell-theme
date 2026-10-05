"""Transactional generation and per-user installation."""
import ast
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from .build import compile_theme, ROOT
from .config import theme_name

SCHEMA = 'org.gnome.shell.extensions.user-theme'
EXTENSION = 'user-theme@gnome-shell-extensions.gcampax.github.com'
DOCK_EXTENSION = 'prisma-dock@prisma.local'


def owned(path):
    shell, marker = path / 'gnome-shell', path / 'gnome-shell/prisma.json'
    if path.is_symlink() or shell.is_symlink() or marker.is_symlink():
        return False
    try:
        meta = json.loads(marker.read_text())
        return isinstance(meta, dict) and meta.get('project') == 'Prisma' and meta.get('schema') == 1
    except (OSError, ValueError):
        return False


def generate(path, config):
    """Build first, then atomically exchange a Prisma-owned directory."""
    path = Path(path).expanduser().absolute()
    if path.exists() or path.is_symlink():
        if not owned(path):
            raise ValueError(f'{path} já existe e não pertence ao Prisma.')
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.prisma-', dir=path.parent) as temp:
        stage, backup = Path(temp) / 'new', Path(temp) / 'previous'
        compile_theme(stage, config)
        if path.exists() or path.is_symlink():
            if not owned(path):
                raise ValueError(f'O destino foi alterado durante a geração: {path}.')
            path.rename(backup)
        try:
            stage.rename(path)
        except OSError:
            if backup.exists():
                backup.rename(path)
            raise
    return path


def owned_companion(path):
    marker = path / 'prisma.json'
    if path.is_symlink() or marker.is_symlink():
        return False
    try:
        return json.loads(marker.read_text()) == {'project': 'Prisma', 'component': 'dock', 'schema': 1}
    except (OSError, ValueError):
        return False


def install_companion(extensions_dir):
    target = extensions_dir / DOCK_EXTENSION
    if (target.exists() or target.is_symlink()) and not owned_companion(target):
        raise ValueError(f'{target} já existe e não pertence ao Prisma.')
    extensions_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.prisma-dock-', dir=extensions_dir) as temp:
        stage, backup = Path(temp) / 'new', Path(temp) / 'previous'
        shutil.copytree(ROOT / 'integrations' / DOCK_EXTENSION, stage)
        if target.exists():
            target.rename(backup)
        try:
            stage.rename(target)
        except OSError:
            if backup.exists():
                backup.rename(target)
            raise
    return target


class UserThemes:
    def run(self, *args):
        return subprocess.run(args, check=True, capture_output=True, text=True,
                              timeout=10, env={**os.environ, 'LC_ALL': 'C'}).stdout.strip()

    def current(self):
        value = ast.literal_eval(self.run('gsettings', 'get', SCHEMA, 'name'))
        if not isinstance(value, str):
            raise ValueError('Configuração User Themes inválida.')
        return value

    def available(self):
        try:
            info = self.run('gnome-extensions', 'info', EXTENSION)
            return any(f'State: {state}' in info for state in ('ENABLED', 'ACTIVE'))
        except (OSError, ValueError, subprocess.SubprocessError):
            return False

    def set(self, name):
        # A GVariant string, passed as one argument; no shell interpretation.
        self.run('gsettings', 'set', SCHEMA, 'name', json.dumps(name))


    def enable_dock(self):
        try:
            self.run('gnome-extensions', 'enable', DOCK_EXTENSION)
            return True
        except subprocess.SubprocessError:
            # A newly installed local extension is discovered at next login.
            self._update_extension_list('enabled-extensions', enable=True)
            self._update_extension_list('disabled-extensions', enable=False)
            return False

    def disable_dock(self):
        self._update_extension_list('enabled-extensions', enable=False)

    def _update_extension_list(self, key, enable):
        text = self.run('gsettings', 'get', 'org.gnome.shell', key)
        if text.startswith('@as '):
            text = text[4:]
        try:
            entries = ast.literal_eval(text)
        except (ValueError, SyntaxError) as error:
            raise ValueError('Lista de extensões inválida.') from error
        if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
            raise ValueError('Lista de extensões inválida.')
        desired = [item for item in entries if item != DOCK_EXTENSION]
        if enable:
            desired.append(DOCK_EXTENSION)
        if desired != entries:
            self.run('gsettings', 'set', 'org.gnome.shell', key, repr(desired))


class Installer:
    def __init__(self, themes_dir=None, settings=None, extensions_dir=None):
        self.themes_dir = Path(themes_dir) if themes_dir is not None else Path.home() / '.themes'
        self.settings = settings if settings is not None else UserThemes()
        self.extensions_dir = (Path(extensions_dir) if extensions_dir is not None else
                               self.themes_dir.parent / 'extensions' if themes_dir is not None else
                               Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'gnome-shell/extensions')

    def install(self, config, activate=False):
        companion = self.extensions_dir / DOCK_EXTENSION
        if (companion.exists() or companion.is_symlink()) and not owned_companion(companion):
            raise ValueError(f'{companion} já existe e não pertence ao Prisma.')
        target = generate(self.themes_dir / config.name, config)
        install_companion(self.extensions_dir)
        print(f'Tema instalado em {target}.')
        if activate:
            try:
                if not self.settings.available():
                    raise RuntimeError('User Themes não está habilitado.')
                previous = self.settings.current()
                if previous == config.name:
                    self.settings.set('')
                try:
                    self.settings.set(config.name)
                except (OSError, ValueError, subprocess.SubprocessError):
                    self.settings.set(previous)
                    raise
                print(f'Tema {config.name} selecionado.')
                try:
                    if not self.settings.enable_dock():
                        print('Prisma Dock será habilitado no próximo login. Saia e entre na sessão para carregar a nova extensão.')
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    print(f'Tema selecionado; habilite Prisma Dock pelo aplicativo Extensões. Detalhe: {error}')
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                print(f'Instalação preservada. Ativação indisponível: {error} Habilite User Themes e selecione {config.name}.')
        return target

    def remove(self, name):
        target = self.themes_dir / theme_name(name)
        if not target.exists() and not target.is_symlink():
            print(f'Tema {name} não está instalado.')
            return
        if not owned(target):
            raise ValueError(f'Recusando remover {target}: não pertence ao Prisma.')
        try:
            active = self.settings.current() == name
        except (OSError, ValueError, subprocess.SubprocessError):
            active = False
        if active:
            self.settings.set('')
        shutil.rmtree(target)
        print(f'Tema {name} removido.')
        companion = self.extensions_dir / DOCK_EXTENSION
        if owned_companion(companion) and not any(owned(path) for path in self.themes_dir.iterdir()):
            try:
                self.settings.disable_dock()
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                print(f'Extensão auxiliar preservada: {error}')
            else:
                shutil.rmtree(companion)
