# coding: utf-8

# Copyright (c) Vidar Tonaas Fauske.
# Distributed under the terms of the Modified BSD License.
"""Hotpot - Jupyter kernel manager helpers
"""

from ._version import __version__

from .base import MaximumKernelsException, PooledKernelManager, AsyncPooledKernelManager

__all__ = [
    '__version__',
    'MaximumKernelsException',
    'PooledKernelManager',
    'AsyncPooledKernelManager',
]

try:
    from .mapping import LimitedPooledMappingKernelManager
    __all__.append('PooledMappingKernelManager')
except ImportError:
    pass

try:
    from .async_mapping import AsyncLimitedPooledMappingKernelManager
    __all__.append('AsyncPooledMappingKernelManager')
except ImportError:
    pass
