# coding: utf-8

# Copyright (c) Vidar Tonaas Fauske.
# Distributed under the terms of the Modified BSD License.
"""Hotpot - Jupyter kernel manager helpers
"""

from ._version import __version__

from .limited import MaximumKernelsException, SyncLimitedKernelManager
from .pooled_sync import SyncPooledKernelManager

__all__ = [
    '__version__',
    'MaximumKernelsException',
    'SyncPooledKernelManager',
    'SyncLimitedKernelManager',
]

try:
    from .pooled import PooledKernelManager
    __all__.append('PooledKernelManager')
except ImportError:
    pass

try:
    from .limited import LimitedKernelManager
    __all__.append('LimitedKernelManager')
except ImportError:
    pass

try:
    from .mapping import PooledMappingKernelManager
    __all__.append('PooledMappingKernelManager')
except ImportError:
    pass
