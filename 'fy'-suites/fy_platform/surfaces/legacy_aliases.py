"""Legacy aliases for fy_platform.surfaces.

"""
from __future__ import annotations

LEGACY_ALIAS_MAP = {
    'contractify': ('fy', 'analyze', 'contract'),
    'testify': ('fy', 'analyze', 'quality'),
    'documentify': ('fy', 'analyze', 'docs'),
    'docify': ('fy', 'analyze', 'code_docs'),
    'despag-check': ('fy', 'analyze', 'structure'),
    'despaghettify': ('fy', 'analyze', 'structure'),
    'securify': ('fy', 'analyze', 'security'),
    'mvpify': ('fy', 'import', 'mvp'),
    'metrify': ('fy', 'metrics', 'report'),
}
