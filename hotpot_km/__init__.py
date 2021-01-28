# coding: utf-8

# Copyright (c) Vidar Tonaas Fauske.
# Distributed under the terms of the Modified BSD License.
"""Hotpot - Jupyter kernel manager helpers

This module contains
"""

from jupyter_client.multikernelmanager import MultiKernelManager
from traitlets import Bool, Dict, Integer, Unicode

from ._version import __version__


class MaximumKernelsException(Exception):
    pass


class LimitedKernelManager(MultiKernelManager):
    max_kernels = Integer(0, config=True,
        help="The maximum number of concurrent kernels",
    )

    def pre_start_kernel(self, kernel_name, kwargs):
        if len(self) >= self.max_kernels > 0:
            raise MaximumKernelsException("No kernels are available.")
        return super().pre_start_kernel(kernel_name, kwargs)


class PooledKernelManager(MultiKernelManager):
    kernel_pool_size = Integer(0, config=True,
        help="The number of started kernels to keep on standby",
    )

    pool_kernel_name = Unicode(None, allow_none=True, config=True,
        help="The name of the kernel to pre-warm"
    )

    pool_kwargs = Dict(config=True,
        help="The arguments passed to kernel_start when pre-warming"
    )

    strict_pool_names = Bool(config=True,
        help="Whether to allow starting kernels with other names than that of the pool"
    )

    strict_pool_kwargs = Bool(config=True,
        help="Whether to allow starting kernels with other kwargs than that of the pool"
    )

    _pool = Dict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fill_if_needed()

    def fill_if_needed(self):
        """Start kernels until pool is full"""
        for i in range(len(self) - len(self._pool)):
            km, _, kernel_id = self.pre_start_kernel(self.pool_kernel_name, self.pool_kwargs)
            _pool[kernel_id] = km

    def _should_use_pool(self, kernel_name, kwargs):
        """Verify name and kwargs, and check whether we should use the pool"""
        if "kernel_id" in kwargs:
            return False

        if self.strict_pool_names and kernel_name != self.pool_kernel_name:
            raise ValueError("Cannot start kernel with name %r" % (kernel_name,))
        if self.strict_pool_kwargs and kwargs != self.pool_kwargs:
            raise ValueError("Cannot start kernel with kwargs %r" % (kwargs,))

        return (
            kernel_name == self.pool_kernel_name and
            kwargs == self.pool_kwargs and
            len(self._pool) > 0
        )

    def pre_start_kernel(self, kernel_name, kwargs):
        if not self._should_use_pool(kernel_name, kwargs):
            return super().pre_start_kernel(kernel_name, kwargs)

        # TODO: Use a queue?
        kernel_id = tuple(self._pool.keys())[0]
        km = self._pool.pop(kernel_id)
        try:
            self.fill_if_needed()
        except MaximumKernelsException:
            pass
        return km, km.kernel_name, kernel_id


__all__ = [
    '__version__',
    'MaximumKernelsException',
    'LimitedKernelManager',
    'PooledKernelManager',
]

try:
    from .mapping import LimitedPooledMappingKernelManager
    __all__.append('LimitedPooledMappingKernelManager')
except ImportError:
    pass

try:
    from .async_mapping import AsyncLimitedPooledMappingKernelManager
    __all__.append('AsyncLimitedPooledMappingKernelManager')
except ImportError:
    pass
