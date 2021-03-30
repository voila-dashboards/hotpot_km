
import asyncio

from jupyter_server.services.kernels.kernelmanager import MappingKernelManager

from .pooled_sync import SyncPooledKernelManager


class SyncPooledMappingKernelManager(SyncPooledKernelManager, MappingKernelManager):
    def restart_kernel(self, kernel_id, **kwargs):
        if kwargs:
            self.log.warning("Ignored arguments to restart_kernel: %r", kwargs)
        return super().restart_kernel(kernel_id)

    if asyncio.iscoroutinefunction(MappingKernelManager.cull_kernel_if_idle):
        async def cull_kernel_if_idle(self, kernel_id):
            # Ensure we don't cull pooled kernels:
            for pool in self._pools.values():
                if kernel_id in pool:
                    return
            return await super().cull_kernel_if_idle(kernel_id)
    else:
        def cull_kernel_if_idle(self, kernel_id):
            # Ensure we don't cull pooled kernels:
            for pool in self._pools.values():
                if kernel_id in pool:
                    return
            return super().cull_kernel_if_idle(kernel_id)
