
import asyncio
from contextlib import contextmanager, asynccontextmanager
from subprocess import PIPE
from traitlets.config.loader import Config
from tornado.testing import gen_test

from .. import (
    AsyncPooledKernelManager,
    LimitedKernelManager,
    MaximumKernelsException,
    PooledKernelManager
)

from .utils import async_shutdown_all_direct, TestAsyncKernelManager, TestKernelManager

class CombinedManager(PooledKernelManager, LimitedKernelManager):
    pass


# Test that it works as normal with default config
class TestCombinedManager(TestKernelManager):
    __test__ = True

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        km = CombinedManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all()


# Test that it works with a max that is larger than pool size
class TestCombinedManagerApplied(TestKernelManager):
    __test__ = True

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        c.LimitedKernelManager.max_kernels = 4
        c.CombinedManager.kernel_pool_size = 2
        c.CombinedManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        km = CombinedManager(config=c)
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
            for kid in kids:
                self.assertNotIn(kid, km)

            # Cycle again to assure the pool survives that
            kids = []
            for i in range(4):
                kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            self.assertEqual(len(km._pool), 0)

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
            # shutdown again is okay, because we have no kernels
            km.shutdown_all()


class AsyncCombinedManager(AsyncPooledKernelManager, LimitedKernelManager):
    pass


# Test that it works as normal with default config
class TestAsyncCombinedManager(TestAsyncKernelManager):
    __test__ = True

    @asynccontextmanager
    async def _get_tcp_km(self):
        c = Config()
        km = AsyncCombinedManager(config=c)
        try:
            yield km
        finally:
            await km.shutdown_all()


# Test that it works with a max that is larger than pool size
class TestAsyncCombinedManagerApplied(TestAsyncKernelManager):
    __test__ = True

    @asynccontextmanager
    async def _get_tcp_km(self):
        c = Config()
        c.LimitedKernelManager.max_kernels = 4
        c.AsyncCombinedManager.kernel_pool_size = 2
        c.AsyncCombinedManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        km = AsyncCombinedManager(config=c)
        try:
            yield km
        finally:
            await km.shutdown_all()

    @gen_test(timeout=20)
    async def test_exceed_pool_size(self):
        async with self._get_tcp_km() as km:
            self.assertEqual(len(km._pool), 2)
            kids = []
            for i in range(4):
                kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)
                self.assertEqual(len(km._pool), 2)

            await async_shutdown_all_direct(km)
            for kid in kids:
                self.assertNotIn(kid, km)

            # Cycle again to assure the pool survives that
            kids = []
            for i in range(4):
                kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)
                self.assertEqual(len(km._pool), 2)

            await km.shutdown_all()
            for kid in kids:
                self.assertNotIn(kid, km)

    @gen_test(timeout=20)
    async def test_breach_max(self):
        async with self._get_tcp_km() as km:
            kids = []
            for i in range(4):
                kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            with self.assertRaises(MaximumKernelsException):
                await km.start_kernel(stdout=PIPE, stderr=PIPE)
                await asyncio.gather(km._pool)

            # Remove and add one to make sure we correctly recovered
            await km.shutdown_kernel(kid)
            self.assertNotIn(kid, km)
            kids.pop()

            kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
            kids.append(kid)

            await km.shutdown_all()
            for kid in kids:
                self.assertNotIn(kid, km)
            # shutdown again is okay, because we have no kernels
            km.shutdown_all()