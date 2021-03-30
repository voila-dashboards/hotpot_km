import asyncio
from contextlib import asynccontextmanager
import platform
from subprocess import PIPE

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
from pytest import mark
from traitlets.config.loader import Config
from tornado.web import HTTPError
from tornado.testing import gen_test, AsyncTestCase

from .. import MaximumKernelsException

try:
    from ..mapping_sync import SyncPooledMappingKernelManager
except ImportError as e:
    print(f"Won't be able to test synced pool: {e}")

from ..async_utils import ensure_async
from .utils import async_shutdown_all_direct, TestAsyncKernelManager


CULL_TIMEOUT = 10 if platform.python_implementation() == 'PyPy' else 5
CULL_INTERVAL = 1


# Test that it works as normal with default config
class TestSyncMappingKernelManagerUnused(TestAsyncKernelManager):
    __test__ = True

    # static so picklable for multiprocessing on Windows
    @staticmethod
    @asynccontextmanager
    async def _get_tcp_km():
        c = Config()
        km = SyncPooledMappingKernelManager(config=c)
        try:
            yield km
        finally:
            await ensure_async(km.shutdown_all())

    # Mapping manager doesn't handle this:
    @mark.skip()
    @gen_test
    async def test_tcp_lifecycle_with_kernel_id(self):
        pass


# Test that it works with a max that is larger than pool size
class TestSyncMappingKernelManagerApplied(TestAsyncKernelManager):
    __test__ = True

    # static so picklable for multiprocessing on Windows
    @staticmethod
    @asynccontextmanager
    async def _get_tcp_km(config_culling=False):
        c = Config()
        c.SyncLimitedKernelManager.max_kernels = 4
        c.SyncPooledMappingKernelManager.fill_delay = 0
        c.SyncPooledMappingKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 2}
        c.SyncPooledMappingKernelManager.pool_kwargs = {
            NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)
        }
        if config_culling:
            c.MappingKernelManager.cull_idle_timeout = CULL_TIMEOUT
            c.MappingKernelManager.cull_interval = CULL_INTERVAL
            c.MappingKernelManager.cull_connected = False
        km = SyncPooledMappingKernelManager(config=c)
        try:
            yield km
        finally:
            await ensure_async(km.shutdown_all())

    # Mapping manager doesn't handle this:
    @mark.skip()
    @gen_test
    async def test_tcp_lifecycle_with_kernel_id(self):
        pass

    @gen_test(timeout=60)
    async def test_exceed_pool_size(self):
        async with self._get_tcp_km() as km:
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 2)
            kids = []
            for i in range(4):
                kid = await ensure_async(km.start_kernel(stdout=PIPE, stderr=PIPE))
                self.assertIn(kid, km)
                kids.append(kid)

            await async_shutdown_all_direct(km)
            for kid in kids:
                self.assertNotIn(kid, km)

            # Cycle again to assure the pool survives that
            kids = []
            for i in range(4):
                kid = await ensure_async(km.start_kernel(stdout=PIPE, stderr=PIPE))
                self.assertIn(kid, km)
                kids.append(kid)

            await ensure_async(km.shutdown_all())
            for kid in kids:
                self.assertNotIn(kid, km)

    @gen_test(timeout=60)
    async def test_breach_max(self):
        async with self._get_tcp_km() as km:
            kids = []
            for i in range(4):
                kid = await ensure_async(km.start_kernel(stdout=PIPE, stderr=PIPE))
                self.assertIn(kid, km)
                kids.append(kid)

            with self.assertRaises(MaximumKernelsException):
                await ensure_async(km.start_kernel(stdout=PIPE, stderr=PIPE))

            # Remove and add one to make sure we correctly recovered
            await ensure_async(km.shutdown_kernel(kid))
            self.assertNotIn(kid, km)
            kids.pop()

            kid = await ensure_async(km.start_kernel(stdout=PIPE, stderr=PIPE))
            self.assertIn(kid, km)
            kids.append(kid)

            await ensure_async(km.shutdown_all())
            for kid in kids:
                self.assertNotIn(kid, km)

    @gen_test(timeout=60)
    async def test_culling(self):
        # this will start and await the pool:
        async with self._get_tcp_km(config_culling=True) as km:
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 2)
            self.assertEqual(len(km), 2)

            kid = km._pools[NATIVE_KERNEL_NAME][0]

            culled = await self.get_cull_status(km, kid)  # in pool, should not be culled
            assert not culled

            # pop one kernel
            kid = await ensure_async(km.start_kernel(stdout=PIPE, stderr=PIPE))

            culled = await self.get_cull_status(km, kid)  # now active, should be culled
            assert culled


    async def get_cull_status(self, km, kid):
        frequency = 0.5
        culled = False
        for _ in range(int((CULL_TIMEOUT + CULL_INTERVAL)/frequency)):  # Timeout + Interval will ensure cull
            try:
                km.get_kernel(kid)
            except HTTPError as e:
                assert e.status_code == 404
                culled = True
                break
            else:
                await asyncio.sleep(frequency)
        return culled
