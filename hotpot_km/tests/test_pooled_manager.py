
import asyncio
from contextlib import asynccontextmanager
from subprocess import PIPE
from unittest import TestCase

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
import pytest
from tornado.testing import AsyncTestCase, gen_test
from traitlets.config.loader import Config

try:
    from .. import (
        PooledKernelManager,
        MaximumKernelsException,
    )
except ImportError:
    pass

from .utils import async_shutdown_all_direct, TestAsyncKernelManager

# Test that it works as normal with default config
class TestPooledKernelManagerUnused(TestAsyncKernelManager):
    __test__ = True

    # static so picklable for multiprocessing on Windows
    @staticmethod
    @asynccontextmanager
    async def _get_tcp_km():
        c = Config()
        km = PooledKernelManager(config=c)
        try:
            yield km
        finally:
            await km.shutdown_all(now=True)


# Test that it works with an unstrict pool
class TestPooledKernelManagerApplied(TestAsyncKernelManager):
    __test__ = True

    # static so picklable for multiprocessing on Windows
    @staticmethod
    @asynccontextmanager
    async def _get_tcp_km():
        c = Config()
        c.LimitedKernelManager.max_kernels = 4
        c.PooledKernelManager.fill_delay = 0
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 2}
        c.PooledKernelManager.pool_kwargs = {NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)}
        km = PooledKernelManager(config=c)
        try:
            await km.wait_for_pool()
            yield km
        finally:
            await km.shutdown_all()

    @gen_test(timeout=60)
    async def test_exceed_pool_size(self):
        async with self._get_tcp_km() as km:
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 2)
            kids = []
            for i in range(4):
                kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            await async_shutdown_all_direct(km)
            for kid in kids:
                self.assertNotIn(kid, km)

            # Cycle again to assure the pool survives that
            kids = []
            for i in range(4):
                kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            await km.shutdown_all()
            for kid in kids:
                self.assertNotIn(kid, km)

    @gen_test
    async def test_decrease_pool_size(self):
        async with self._get_tcp_km() as km:
            km.kernel_pools = {NATIVE_KERNEL_NAME: 1}
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 1)
            # km.shutdown_kernel is not reentrant, so await:
            await asyncio.gather(*km._discarded)

    @gen_test
    async def test_increase_pool_size(self):
        async with self._get_tcp_km() as km:
            km.kernel_pools = {NATIVE_KERNEL_NAME: 3}
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 3)

    @gen_test(timeout=60)
    async def test_breach_max(self):
        async with self._get_tcp_km() as km:
            kids = []
            for i in range(4):
                kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            with self.assertRaises(MaximumKernelsException):
                await km.start_kernel(stdout=PIPE, stderr=PIPE)

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
            await km.shutdown_all()



# Test that it works with an strict pool
class TestPooledKernelManagerStrict(AsyncTestCase):

    @gen_test
    async def test_strict_name_correct(self):
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.strict_pool_names = True
        km = PooledKernelManager(config=c)

        try:
            kid = await km.start_kernel(kernel_name=NATIVE_KERNEL_NAME, stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)

        finally:
            await km.shutdown_all()
        self.assertNotIn(kid, km)

    @gen_test
    async def test_strict_name_incorrect(self):
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.strict_pool_names = True
        km = PooledKernelManager(config=c)

        try:
            with self.assertRaisesRegex(ValueError, 'Cannot start kernel with name'):
                kid = await km.start_kernel(kernel_name='foo', stdout=PIPE, stderr=PIPE)
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 1)
        finally:
            await km.shutdown_all()

    @gen_test
    async def test_strict_kwargs_correct(self):
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.pool_kwargs = {NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)}
        c.PooledKernelManager.strict_pool_kwargs = True
        km = PooledKernelManager(config=c)

        try:
            kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
        finally:
            await km.shutdown_all()
        self.assertNotIn(kid, km)

    @gen_test
    async def test_strict_kwargs_incorrect(self):
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.pool_kwargs = {NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)}
        c.PooledKernelManager.strict_pool_kwargs = True
        km = PooledKernelManager(config=c)

        try:
            with self.assertRaisesRegex(ValueError, 'Cannot start kernel with kwargs'):
                kid = await km.start_kernel()
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 1)
        finally:
            await km.shutdown_all()

    @gen_test
    async def test_both_strict_correct(self):
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.strict_pool_names = True
        c.PooledKernelManager.pool_kwargs = {NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)}
        c.PooledKernelManager.strict_pool_kwargs = True
        km = PooledKernelManager(config=c)

        try:
            kid = await km.start_kernel(kernel_name=NATIVE_KERNEL_NAME, stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
        finally:
            await km.shutdown_all()
        self.assertNotIn(kid, km)
