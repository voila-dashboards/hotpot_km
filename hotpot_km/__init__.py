# coding: utf-8

# Copyright (c) Vidar Tonaas Fauske.
# Distributed under the terms of the Modified BSD License.
"""Hotpot - Jupyter kernel manager helpers

This module contains
"""

import asyncio
from queue import SimpleQueue

from jupyter_client.multikernelmanager import MultiKernelManager, AsyncMultiKernelManager
from traitlets import Bool, Dict, Integer, List, Unicode, observe

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


class _PooledBase(MultiKernelManager):
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

    _pool = List()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fill_if_needed()
        self.observe(self._pool_size_changed, 'kernel_pool_size')

    def _pool_size_changed(self, change):
        if change['old'] > change['new']:
            self.unfill_as_needed()
        else:
            self.fill_if_needed()

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


class PooledKernelManager(_PooledBase):

    def unfill_as_needed(self):
        """Kills extra kernels in pool"""
        for i in range(len(self._pool) - self.kernel_pool_size):
            super().shutdown_kernel(self._pool.pop(0))

    def fill_if_needed(self):
        """Start kernels until pool is full"""
        for i in range(self.kernel_pool_size - len(self._pool)):
            self._pool.append(super().start_kernel(kernel_name=self.pool_kernel_name, **self.pool_kwargs))

    def start_kernel(self, kernel_name=None, **kwargs):
        if self._should_use_pool(kernel_name, kwargs):
            ret = self._pool.pop(0)
        else:
            ret = super().start_kernel(kernel_name=kernel_name, **kwargs)

        try:
            self.fill_if_needed()
        except MaximumKernelsException:
            pass
        return ret

    def shutdown_kernel(self, kernel_id, *args, **kwargs):
        if kernel_id in self._pool:
            self._pool.remove(kernel_id)
        return super().shutdown_kernel(kernel_id, *args, **kwargs)

    def shutdown_all(self, *args, **kwargs):
        self._pool = []
        return super().shutdown_all(*args, **kwargs)


async def _await_then_kill(aw):
    return await (await aw).shutdown()


class AsyncPooledKernelManager(_PooledBase, AsyncMultiKernelManager):

    def unfill_as_needed(self):
        """Kills extra kernels in pool"""
        for i in range(len(self._pool) - self.kernel_pool_size):
            asyncio.create_task(_await_then_kill(self._pool.pop(0)))

    def fill_if_needed(self):
        """Start kernels until pool is full"""
        for i in range(self.kernel_pool_size - len(self._pool)):
            fut = super().start_kernel(kernel_name=self.pool_kernel_name, **self.pool_kwargs)
            # Start the work on the loop immediately, so it is ready when needed:
            self._pool.append(asyncio.create_task(fut))

    async def start_kernel(self, kernel_name=None, **kwargs):
        if self._should_use_pool(kernel_name, kwargs):
            fut = self._pool.pop(0)
        else:
            fut = super().start_kernel(kernel_name=kernel_name, **kwargs)

        try:
            self.fill_if_needed()
        except MaximumKernelsException:
            pass
        return await fut

    async def shutdown_kernel(self, kernel_id, *args, **kwargs):
        for i, f in enumerate(self._pool):
            if f.done() and f.result() == kernel_id:
                self._pool.pop(i)
                break
        return await super().shutdown_kernel(kernel_id, *args, **kwargs)

    async def shutdown_all(self, *args, **kwargs):
        await super().shutdown_all(*args, **kwargs)
        # Parent doesn't correctly add all created kernels until they have completed startup:
        for fut in self._pool:
            kid = await fut
            if kid in self:
                await self.shutdown_kernel(kid, *args, **kwargs)
        self._pool = []


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
