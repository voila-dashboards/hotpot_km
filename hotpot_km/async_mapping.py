
from jupyter_server.services.kernels.kernelmanager import AsyncMappingKernelManager

from .base import PooledKernelManager


class AsyncLimitedPooledMappingKernelManager(
    AsyncMappingKernelManager,
    PooledKernelManager
):
    pass
