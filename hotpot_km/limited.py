# coding: utf-8

# Copyright (c) Vidar Tonaas Fauske.
# Distributed under the terms of the Modified BSD License.
"""Hotpot - Jupyter kernel manager helpers

This module contains
"""

from jupyter_client.multikernelmanager import MultiKernelManager

from traitlets import Integer


class MaximumKernelsException(Exception):
    pass


class SyncLimitedKernelManager(MultiKernelManager):
    max_kernels = Integer(
        0,
        config=True,
        help="The maximum number of concurrent kernels",
    )

    def start_kernel(self, kernel_name=None, **kwargs):
        if "kernel_id" not in kwargs and len(self) >= self.max_kernels > 0:
            self.log.debug("Refusing to start kernel, maximum number reached.")
            raise MaximumKernelsException("No kernels are available.")
        return super().start_kernel(kernel_name=kernel_name, **kwargs)


__all__ = [
    "MaximumKernelsException",
    "SyncLimitedKernelManager",
]


try:
    from jupyter_client.multikernelmanager import (
        AsyncMultiKernelManager,
        MultiKernelManager,
    )

    class LimitedKernelManager(AsyncMultiKernelManager):
        max_kernels = Integer(
            0,
            config=True,
            help="The maximum number of concurrent kernels",
        )

        def pre_start_kernel(self, kernel_name, kwargs):
            if len(self) >= self.max_kernels > 0:
                self.log.debug("Refusing to start kernel, maximum number reached.")
                raise MaximumKernelsException("No kernels are available.")
            return super().pre_start_kernel(kernel_name, kwargs)

    __all__.append("LimitedKernelManager")

except ImportError:
    pass
