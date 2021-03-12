
import asyncio
import threading
import uuid
import multiprocessing as mp

import pytest
from subprocess import PIPE
from tornado.testing import AsyncTestCase, gen_test
from unittest import TestCase

from jupyter_client import KernelManager
from jupyter_client.ioloop import IOLoopKernelManager
from jupyter_client.tests.utils import skip_win32
from jupyter_client.localinterfaces import localhost

from ..async_utils import ensure_async

try:
    from jupyter_client import AsyncKernelManager
except ImportError:
    pass

async def async_shutdown_all_direct(km):
    kids = km.list_kernel_ids()
    futs = []
    for kid in kids:
        await km.shutdown_kernel(kid)


class TestAsyncKernelManager(AsyncTestCase):
    # Prevent the base class from being collected directly
    __test__ = False

    # static so picklable for multiprocessing on Windows
    @staticmethod
    async def _run_lifecycle(km, test_kid=None):
        if test_kid:
            kid = await km.start_kernel(stdout=PIPE, stderr=PIPE, kernel_id=test_kid)
            assert kid == test_kid
        else:
            kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
        assert await km.is_alive(kid)
        assert kid in km
        assert kid in km.list_kernel_ids()
        await km.restart_kernel(kid, now=True)
        assert await km.is_alive(kid)
        assert kid in km.list_kernel_ids()
        await km.interrupt_kernel(kid)
        k = km.get_kernel(kid)
        assert isinstance(k, KernelManager)
        await km.shutdown_kernel(kid, now=True)
        assert kid not in km, f'{kid} not in {km}'

    async def _run_cinfo(self, km, transport, ip):
        kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
        k = km.get_kernel(kid)
        cinfo = km.get_connection_info(kid)
        self.assertEqual(transport, cinfo['transport'])
        self.assertEqual(ip, cinfo['ip'])
        self.assertTrue('stdin_port' in cinfo)
        self.assertTrue('iopub_port' in cinfo)
        stream = km.connect_iopub(kid)
        stream.close()
        self.assertTrue('shell_port' in cinfo)
        stream = km.connect_shell(kid)
        stream.close()
        self.assertTrue('hb_port' in cinfo)
        stream = km.connect_hb(kid)
        stream.close()
        await ensure_async(km.shutdown_kernel(kid, now=True))
        self.assertNotIn(kid, km)

    @gen_test
    async def test_tcp_lifecycle(self):
        await self.raw_tcp_lifecycle()

    @gen_test
    async def test_tcp_lifecycle_with_kernel_id(self):
        await self.raw_tcp_lifecycle(test_kid=str(uuid.uuid4()))

    @gen_test(timeout=20)
    async def test_shutdown_all(self):
        async with self._get_tcp_km() as km:
            kid = await km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
            await ensure_async(km.shutdown_all())
            self.assertNotIn(kid, km)
            # shutdown again is okay, because we have no kernels
            await ensure_async(km.shutdown_all())

    @gen_test
    async def test_tcp_cinfo(self):
        async with self._get_tcp_km() as km:
            await self._run_cinfo(km, 'tcp', localhost())

    @gen_test(timeout=20)
    async def test_start_sequence_tcp_kernels(self):
        """Ensure that a sequence of kernel startups doesn't break anything."""
        async with self._get_tcp_km() as km:
            await self._run_lifecycle(km)
        async with self._get_tcp_km() as km:
            await self._run_lifecycle(km)
        async with self._get_tcp_km() as km:
            await self._run_lifecycle(km)

    def tcp_lifecycle_with_loop(self):
        # Ensure each thread has an event loop
        asyncio.set_event_loop(asyncio.new_event_loop())
        asyncio.get_event_loop().run_until_complete(self.raw_tcp_lifecycle())

    # static so picklable for multiprocessing on Windows
    @classmethod
    async def raw_tcp_lifecycle(cls, test_kid=None):
        # Since @gen_test creates an event loop, we need a raw form of
        # test_tcp_lifecycle that assumes the loop already exists.
        async with cls._get_tcp_km() as km:
            await cls._run_lifecycle(km, test_kid=test_kid)

    # static so picklable for multiprocessing on Windows
    @classmethod
    def raw_tcp_lifecycle_sync(cls, test_kid=None):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Forked MP, make new loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(cls.raw_tcp_lifecycle(test_kid=test_kid))

    @pytest.mark.skip("Parallel use is currently not properly vetted, fails often")
    @gen_test
    async def test_start_parallel_thread_kernels(self):
        await self.raw_tcp_lifecycle()

        thread = threading.Thread(target=self.tcp_lifecycle_with_loop)
        thread2 = threading.Thread(target=self.tcp_lifecycle_with_loop)
        try:
            thread.start()
            thread2.start()
        finally:
            thread.join()
            thread2.join()

    @pytest.mark.skip("Parallel use is currently not properly vetted, fails often")
    @gen_test
    async def test_start_parallel_process_kernels(self):
        await self.raw_tcp_lifecycle()

        thread = threading.Thread(target=self.tcp_lifecycle_with_loop)
        proc = mp.Process(target=self.raw_tcp_lifecycle_sync)

        try:
            thread.start()
            proc.start()
        finally:
            proc.join()
            thread.join()

        assert proc.exitcode == 0