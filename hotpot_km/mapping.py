
from jupyter_server.services.kernels.kernelmanager import MappingKernelManager

from . import LimitedKernelManager, PooledKernelManager


class LimitedPooledMappingKernelManager(
    MappingKernelManager,
    PooledKernelManager,
    LimitedKernelManager
):
    pass
