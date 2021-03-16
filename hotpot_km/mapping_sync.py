from jupyter_server.services.kernels.kernelmanager import MappingKernelManager

from .pooled_sync import SyncPooledKernelManager


class SyncPooledMappingKernelManager(SyncPooledKernelManager, MappingKernelManager):
    def restart_kernel(self, kernel_id, **kwargs):
        if kwargs:
            self.log.warning("Ignored arguments to restart_kernel: %r", kwargs)
        return super().restart_kernel(kernel_id)
