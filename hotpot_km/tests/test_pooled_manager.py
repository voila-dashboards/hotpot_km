
from subprocess import PIPE

from jupyter_client.tests.test_multikernelmanager import TestKernelManager
from traitlets.config.loader import Config

from .. import (
    PooledKernelManager,
    MaximumKernelsException,
)

# Prevent the base class from being collected directly
TestKernelManager.__test__ = False

# Test that it works as normal with default config
class TestPooledKernelManager(TestKernelManager):
    __test__ = True

    def _get_tcp_km(self):
        c = Config()
        km = PooledKernelManager(config=c)
        return km

    def _get_ipc_km(self):
        c = Config()
        c.KernelManager.transport = 'ipc'
        c.KernelManager.ip = 'test'
        km = PooledKernelManager(config=c)
        return km


# Test that it works with an unstrict pool
class TestLimitedKernelManagerApplied(TestKernelManager):
    __test__ = True

    def _get_tcp_km(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 4
        km = PooledKernelManager(config=c)
        return km

    def _get_ipc_km(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 4
        c.KernelManager.transport = 'ipc'
        c.KernelManager.ip = 'test'
        km = PooledKernelManager(config=c)
        return km

