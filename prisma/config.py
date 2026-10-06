"""Validated, reusable Prisma configuration (SPDX-License-Identifier: GPL-2.0-or-later)."""
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


def color(value):
    if not isinstance(value, str) or not re.fullmatch(r'#?[0-9a-fA-F]{6}', value):
        raise ValueError('Use uma cor HEX RGB de seis dígitos, como #c08aff.')
    return '#' + value.lstrip('#').lower()


def theme_name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', value):
        raise ValueError('Nome: 1–64 letras ASCII, números, pontos, hífens ou underscores; comece com letra ou número.')
    return value


@dataclass(frozen=True)
class Config:
    name: str = 'Prisma'
    accent: str = '#c08aff'
    background: str = '#26272e'
    panel_background: str | None = None
    solid_accent: bool = False

    def __post_init__(self):
        if not isinstance(self.solid_accent, bool):
            raise ValueError('solid_accent deve ser true ou false.')
        object.__setattr__(self, 'name', theme_name(self.name))
        for field in ('accent', 'background'):
            object.__setattr__(self, field, color(getattr(self, field)))
        object.__setattr__(self, 'panel_background', color(self.background if self.panel_background is None else self.panel_background))

    def to_dict(self):
        return asdict(self)


def load_config(path=None, **overrides):
    values = {}
    if path:
        values = json.loads(Path(path).expanduser().read_text())
        if not isinstance(values, dict):
            raise ValueError('A configuração deve ser um objeto JSON.')
        unknown = values.keys() - Config.__dataclass_fields__.keys()
        if unknown:
            raise ValueError(f'Opções desconhecidas: {", ".join(sorted(unknown))}.')
        if any(not isinstance(v, bool if k == 'solid_accent' else str) for k, v in values.items()):
            raise ValueError('Cores e nome devem ser strings; solid_accent deve ser true ou false.')
    values.update({k: v for k, v in overrides.items() if v is not None})
    return Config(**values)
