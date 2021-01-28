
from subprocess import PIPE

from jupyter_client.tests.test_multikernelmanager import TestKernelManager
from traitlets.config.loader import Config

from .. import (
    LimitedKernelManager,
    MaximumKernelsException,
)



# Test that it works as normal with default config
class TestLimitedKernelManager(TestKernelManager):
    def _get_tcp_km(self):
        c = Config()
        km = LimitedKernelManager(config=c)
        return km

    def _get_ipc_km(self):
        c = Config()
        c.KernelManager.transport = 'ipc'
        c.KernelManager.ip = 'test'
        km = LimitedKernelManager(config=c)
        return km


# Test that it works with a max of 4
class TestLimitedKernelManager(TestKernelManager):
    def _get_tcp_km(self):
        c = Config()
        c.LimitedKernelManager.max_kernels = 4
        km = LimitedKernelManager(config=c)
        return km

    def _get_ipc_km(self):
        c = Config()
        c.LimitedKernelManager.max_kernels = 4
        c.KernelManager.transport = 'ipc'
        c.KernelManager.ip = 'test'
        km = LimitedKernelManager(config=c)
        return km

    def test_touch_max(self):
        km = self._get_tcp_km()
        kids = []
        for i in range(4):
            kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
            kids.append(kid)

        # Remove and add one to make sure we don't count closed kernels
        km.shutdown_kernel(kid)
        self.assertNotIn(kid, km)
        kids.pop()

        kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
        self.assertIn(kid, km)
        kids.append(kid)

        km.shutdown_all()
        for kin in kids:
            self.assertNotIn(kid, km)
        # shutdown again is okay, because we have no kernels
        km.shutdown_all()

    def test_breach_max(self):
        km = self._get_tcp_km()
        kids = []
        for i in range(4):
            kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
            kids.append(kid)

        with self.assertRaises(MaximumKernelsException):
            km.start_kernel(stdout=PIPE, stderr=PIPE)

        # Remove and add one to make sure we correctly recovered
        km.shutdown_kernel(kid)
        self.assertNotIn(kid, km)
        kids.pop()

        kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
        self.assertIn(kid, km)
        kids.append(kid)

        km.shutdown_all()
        for kin in kids:
            self.assertNotIn(kid, km)
        # shutdown again is okay, because we have no kernels
        km.shutdown_all()
