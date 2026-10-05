# Base provenance

Prisma uses **GNOME Shell 50.1**, without a Marble or Quartz base.

- Official source: https://download.gnome.org/sources/gnome-shell/50/gnome-shell-50.1.tar.xz
- Reference revision: tag `50.1`, https://gitlab.gnome.org/GNOME/gnome-shell/-/tree/50.1/data/theme
- Archive SHA-256: `1b47760172c14f3f4edd1c9aff365f4de45583517bf0f80df4d3acbd4e4cb294`
- Imported on 2026-10-05, including the entire `data/theme/` directory and `COPYING`.

`vendor/gnome-shell-50.1/theme/` preserves the original sources and assets
unchanged. Upstream-generated files are also retained for reference; Prisma
recompiles the SCSS using `sassc`.

GNOME Shell is distributed under GPL-2.0-or-later. The styles include specific
LGPL-2.1 notices, for example in `_common.scss`, from Red Hat and Intel. All
original notices are preserved. See `vendor/gnome-shell-50.1/COPYING` and
`licenses/LGPL-2.1.txt`. New Prisma code uses GPL-2.0-or-later.

Generation adapts a temporary copy of the SCSS: it resolves St color functions
using Sass, replaces dynamic accent references with explicit roles, injects
the palette before the mixins and adds color rules for widget exceptions.
Geometry comes from official Adwaita styles. Referenced assets are copied
alongside the CSS, and calendar markers receive adapted foreground colors.

To update the base, import a new version separately, review the integration
points in `prisma/build.py`, and repeat tests and isolated screenshot checks.
Generation does not automatically fetch the latest upstream version.
