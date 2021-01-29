
from jupyter_server.services.kernels.kernelmanager import AsyncMappingKernelManager

from . import LimitedKernelManager, PooledKernelManager


class AsyncLimitedPooledMappingKernelManager(
    AsyncMappingKernelManager,
    PooledKernelManager,
    LimitedKernelManager
):
    pass
