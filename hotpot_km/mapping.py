from jupyter_server.services.kernels.kernelmanager import AsyncMappingKernelManager

from .limited import MaximumKernelsException
from .pooled import PooledKernelManager


class PooledMappingKernelManager(PooledKernelManager, AsyncMappingKernelManager):
    async def restart_kernel(self, kernel_id, **kwargs):
        if kwargs:
            self.log.warning("Ignored arguments to restart_kernel: %r", kwargs)
        return await super().restart_kernel(kernel_id)

    async def cull_kernel_if_idle(self, kernel_id):
        # Ensure we don't cull pooled kernels:
        # (this logic assumes the init time is shorter than the cull time)
        for pool in self._pools.values():
            for i, f in enumerate(pool):
                try:
                    if f.done() and f.result() == kernel_id:
                        return
                except Exception as e:
                    if not isinstance(e, MaximumKernelsException):
                        self.log.exception("Kernel failed starting up")
                    pool.pop(i)
        return await super().cull_kernel_if_idle(kernel_id)
