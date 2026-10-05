#!/usr/bin/env python3
"""Instalação direta do Prisma. SPDX-License-Identifier: GPL-2.0-or-later."""
import runpy
import sys
from pathlib import Path


if __name__ == '__main__':
    cli = runpy.run_path(str(Path(__file__).resolve().with_name('prisma.py')))
    sys.exit(cli['main'](install_only=True))
