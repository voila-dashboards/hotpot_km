
from jupyter_server.services.kernels.kernelmanager import AsyncMappingKernelManager

from .pooled import PooledKernelManager


class PooledMappingKernelManager(
    PooledKernelManager,
    AsyncMappingKernelManager
):
    async def restart_kernel(self, kernel_id, **kwargs):
        if kwargs:
            self.log.warning("Ignored arguments to restart_kernel: %r", kwargs)
        return await super().restart_kernel(kernel_id)
