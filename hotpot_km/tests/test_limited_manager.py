
from contextlib import contextmanager
from subprocess import PIPE

from traitlets.config.loader import Config

from .. import (
    LimitedKernelManager,
    MaximumKernelsException,
)

from .utils import TestKernelManager


# Test that it works as normal with default config
class TestLimitedKernelManager(TestKernelManager):
    __test__ = True

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        km = LimitedKernelManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all()


# Test that it works with a max of 4
class TestLimitedKernelManagerApplied(TestKernelManager):
    __test__ = True

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        c.LimitedKernelManager.max_kernels = 4
        km = LimitedKernelManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all()

    def test_touch_max(self):
        with self._get_tcp_km() as km:
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
            for kid in kids:
                self.assertNotIn(kid, km)

    def test_breach_max(self):
        with self._get_tcp_km() as km:
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
            for kid in kids:
                self.assertNotIn(kid, km)
