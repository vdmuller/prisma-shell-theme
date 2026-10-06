#!/usr/bin/env python3
"""Prisma CLI. SPDX-License-Identifier: GPL-2.0-or-later."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from prisma.config import load_config
from prisma.install import Installer, generate


def main(argv=None, *, install_only=False):
    parser = argparse.ArgumentParser(description='Prisma — temas configuráveis para GNOME Shell 50.', allow_abbrev=False)
    commands = None if install_only else parser.add_subparsers(dest='command', required=True)
    if install_only:
        parser.set_defaults(command='install')
    for command in (('install',) if install_only else ('build', 'install', 'remove')):
        child = parser if install_only else commands.add_parser(command, allow_abbrev=False)
        child.add_argument('--config', type=Path, help='arquivo JSON reutilizável')
        child.add_argument('--name', help='nome do tema')
        if command != 'remove':
            child.add_argument('--accent', metavar='HEX')
            child.add_argument('--background', metavar='HEX')
            child.add_argument('--panel-background', metavar='HEX')
            child.add_argument('--solid-accent', action=argparse.BooleanOptionalAction, default=None,
                               help='botões selecionados com accent exata e texto neutro')
        if command == 'build':
            child.add_argument('--output', type=Path, help='raiz do tema gerado (default: build/<nome>)')
        if command == 'install':
            child.add_argument('--activate', action='store_true', help='selecionar em User Themes e configurar a dock nativa após instalar')
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config, **{key: getattr(args, key, None)
                            for key in ('name', 'accent', 'background', 'panel_background', 'solid_accent')})
        if args.command == 'build':
            target = generate(args.output or Path('build') / config.name, config)
            print(f'Tema gerado em {target}.')
        else:
            if os.geteuid() == 0:
                raise ValueError('Execute install/remove sem sudo; a instalação é por usuário.')
            if args.command == 'install':
                Installer().install(config, args.activate)
            else:
                Installer().remove(config.name)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(f'Erro: {detail}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
