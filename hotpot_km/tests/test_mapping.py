
from contextlib import contextmanager
from subprocess import PIPE
from traitlets.config.loader import Config

from .. import MaximumKernelsException
from ..mapping import LimitedPooledMappingKernelManager


from .utils import TestKernelManager

# Test that it works as normal with default config
class TestMappingKernelManager(TestKernelManager):
    __test__ = True

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        km = LimitedPooledMappingKernelManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all()


# Test that it works with a max that is larger than pool size
class TestMappingKernelManagerApplied(TestKernelManager):
    __test__ = True

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        c.LimitedKernelManager.max_kernels = 4
        c.LimitedPooledMappingKernelManager.kernel_pool_size = 2
        c.LimitedPooledMappingKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        km = LimitedPooledMappingKernelManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all()

    def test_exceed_pool_size(self):
        with self._get_tcp_km() as km:
            self.assertEqual(len(km._pool), 2)
            kids = []
            for i in range(4):
                kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            self.assertEqual(len(km._pool), 0)

            km.shutdown_all()
            for kin in kids:
                self.assertNotIn(kid, km)

            # Cycle again to assure the pool survives that
            kids = []
            for i in range(4):
                kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            self.assertEqual(len(km._pool), 0)

            km.shutdown_all()
            for kin in kids:
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
            for kin in kids:
                self.assertNotIn(kid, km)
