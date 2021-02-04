
import asyncio
from contextlib import asynccontextmanager
from subprocess import PIPE
from unittest import TestCase

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
import pytest
from tornado.testing import AsyncTestCase, gen_test
from traitlets.config.loader import Config

from .. import (
    AsyncPooledKernelManager,
    MaximumKernelsException,
)

from .utils import TestAsyncKernelManager

async def async_shutdown_all_direct(km):
    kids = km.list_kernel_ids()
    futs = []
    for kid in kids:
        await km.shutdown_kernel(kid)

# Test that it works as normal with default config
class TestAsyncPooledKernelManagerUnused(TestAsyncKernelManager):
    __test__ = True

    @asynccontextmanager
    async def _get_tcp_km(self):
        c = Config()
        km = AsyncPooledKernelManager(config=c)
        try:
            yield km
        finally:
            await km.shutdown_all(now=True)


# Test that it works with an unstrict pool
class TestAsyncPooledKernelManagerApplied(TestAsyncKernelManager):
    __test__ = True

    @asynccontextmanager
    async def _get_tcp_km(self):
        c = Config()
        c.AsyncPooledKernelManager.kernel_pool_size = 2
        c.AsyncPooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        km = AsyncPooledKernelManager(config=c)
        try:
            yield km
        finally:
            # Wait for pool, so safe to shut down
            for fut in km._pool:
                await fut
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


# Test that it works with an strict pool
class TestAsyncPooledKernelManagerStrict(AsyncTestCase):

    @asynccontextmanager
    async def _get_tcp_km(self):
        c = Config()
        c.AsyncPooledKernelManager.kernel_pool_size = 2
        c.AsyncPooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        km = AsyncPooledKernelManager(config=c)
        try:
            yield km
        finally:
            await km.shutdown_all()

    @gen_test
    async def test_strict_name_correct(self):
        c = Config()
        c.AsyncPooledKernelManager.kernel_pool_size = 1
        c.AsyncPooledKernelManager.pool_kernel_name = NATIVE_KERNEL_NAME
        c.AsyncPooledKernelManager.strict_pool_names = True
        km = AsyncPooledKernelManager(config=c)

        try:
            kid = await km.start_kernel(kernel_name=NATIVE_KERNEL_NAME, stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)

        finally:
            await km.shutdown_all()
        self.assertNotIn(kid, km)

    @gen_test
    async def test_strict_name_incorrect(self):
        c = Config()
        c.AsyncPooledKernelManager.kernel_pool_size = 1
        c.AsyncPooledKernelManager.pool_kernel_name = NATIVE_KERNEL_NAME
        c.AsyncPooledKernelManager.strict_pool_names = True
        km = AsyncPooledKernelManager(config=c)

        try:
            with self.assertRaisesRegex(ValueError, 'Cannot start kernel with name'):
                kid = await km.start_kernel(kernel_name='foo', stdout=PIPE, stderr=PIPE)
            self.assertEqual(len(km._pool), 1)
        finally:
            await km.shutdown_all()

    @gen_test
    async def test_strict_kwargs_correct(self):
        c = Config()
        c.AsyncPooledKernelManager.kernel_pool_size = 1
        c.AsyncPooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        c.AsyncPooledKernelManager.strict_pool_kwargs = True
        km = AsyncPooledKernelManager(config=c)

        try:
            kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
        finally:
            await km.shutdown_all()
        self.assertNotIn(kid, km)

    @gen_test
    async def test_strict_kwargs_incorrect(self):
        c = Config()
        c.AsyncPooledKernelManager.kernel_pool_size = 1
        c.AsyncPooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        c.AsyncPooledKernelManager.strict_pool_kwargs = True
        km = AsyncPooledKernelManager(config=c)

        try:
            with self.assertRaisesRegex(ValueError, 'Cannot start kernel with kwargs'):
                kid = await km.start_kernel()
            self.assertEqual(len(km._pool), 1)
        finally:
            await km.shutdown_all()

    @gen_test
    async def test_both_strict_correct(self):
        c = Config()
        c.AsyncPooledKernelManager.kernel_pool_size = 1
        c.AsyncPooledKernelManager.pool_kernel_name = NATIVE_KERNEL_NAME
        c.AsyncPooledKernelManager.strict_pool_names = True
        c.AsyncPooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        c.AsyncPooledKernelManager.strict_pool_kwargs = True
        km = AsyncPooledKernelManager(config=c)

        try:
            kid = await km.start_kernel(kernel_name=NATIVE_KERNEL_NAME, stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
        finally:
            await km.shutdown_all()
        self.assertNotIn(kid, km)
