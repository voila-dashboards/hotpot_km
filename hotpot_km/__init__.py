# coding: utf-8

# Copyright (c) Vidar Tonaas Fauske.
# Distributed under the terms of the Modified BSD License.
"""Hotpot - Jupyter kernel manager helpers
"""

from ._version import __version__

from .limited import MaximumKernelsException, LimitedKernelManager
from .pooled import PooledKernelManager

__all__ = [
    '__version__',
    'MaximumKernelsException',
    'PooledKernelManager',
    'AsyncPooledKernelManager',
]

try:
    from .mapping import PooledMappingKernelManager
    __all__.append('PooledMappingKernelManager')
except ImportError:
    pass
