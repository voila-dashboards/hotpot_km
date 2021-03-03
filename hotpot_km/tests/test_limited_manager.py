
from contextlib import asynccontextmanager
from subprocess import PIPE

from tornado.testing import gen_test
from traitlets.config.loader import Config

from .. import (
    LimitedKernelManager,
    MaximumKernelsException,
)

from .utils import TestAsyncKernelManager


# Test that it works as normal with default config
class TestLimitedKernelManager(TestAsyncKernelManager):
    __test__ = True

    @asynccontextmanager
    async def _get_tcp_km(self):
        c = Config()
        km = LimitedKernelManager(config=c)
        try:
            yield km
        finally:
            await km.shutdown_all(now=True)


# Test that it works with a max of 4
class TestLimitedKernelManagerApplied(TestAsyncKernelManager):
    __test__ = True

    @asynccontextmanager
    async def _get_tcp_km(self):
        c = Config()
        c.LimitedKernelManager.max_kernels = 4
        km = LimitedKernelManager(config=c)
        try:
            yield km
        finally:
            await km.shutdown_all()

    @gen_test(timeout=20)
    async def test_touch_max(self):
        async with self._get_tcp_km() as km:
            kids = []
            for i in range(4):
                kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            # Remove and add one to make sure we don't count closed kernels
            await km.shutdown_kernel(kid)
            self.assertNotIn(kid, km)
            kids.pop()

            kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
            kids.append(kid)

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
