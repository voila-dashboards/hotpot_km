
from jupyter_server.services.kernels.kernelmanager import MappingKernelManager

from .base import PooledKernelManager


class LimitedPooledMappingKernelManager(
    PooledKernelManager,
    MappingKernelManager
):
    async def restart_kernel(self, kernel_id, **kwargs):
        if kwargs:
            self.log.warning("Ignored arguments to restart_kernel: %r", kwargs)
        return await super().restart_kernel(kernel_id)
