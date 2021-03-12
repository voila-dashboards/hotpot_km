
import asyncio
import threading
import uuid
import multiprocessing as mp

import pytest
from subprocess import PIPE
from unittest import TestCase

from jupyter_client import KernelManager
from jupyter_client.tests.utils import skip_win32
from jupyter_client.localinterfaces import localhost


def shutdown_all_direct(km):
    kids = km.list_kernel_ids()
    futs = []
    for kid in kids:
        km.shutdown_kernel(kid)


class TestKernelManager(TestCase):
    # Prevent the base class from being collected directly
    __test__ = False

    # static so picklable for multiprocessing on Windows
    @staticmethod
    def _run_lifecycle(km, test_kid=None):
        if test_kid:
            kid = km.start_kernel(stdout=PIPE, stderr=PIPE, kernel_id=test_kid)
            assert kid == test_kid
        else:
            kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
        assert km.is_alive(kid)
        assert kid in km
        assert kid in km.list_kernel_ids()
        km.restart_kernel(kid, now=True)
        assert km.is_alive(kid)
        assert kid in km.list_kernel_ids()
        km.interrupt_kernel(kid)
        k = km.get_kernel(kid)
        assert isinstance(k, KernelManager)
        km.shutdown_kernel(kid, now=True)
        assert kid not in km, f'{kid} not in {km}'

    def _run_cinfo(self, km, transport, ip):
        kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
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
        km.shutdown_kernel(kid, now=True)
        self.assertNotIn(kid, km)

    def test_tcp_lifecycle(self):
        self.raw_tcp_lifecycle()

    def test_tcp_lifecycle_with_kernel_id(self):
        self.raw_tcp_lifecycle(test_kid=str(uuid.uuid4()))

    def test_shutdown_all(self):
        with self._get_tcp_km() as km:
            kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
            km.shutdown_all()
            self.assertNotIn(kid, km)
            # shutdown again is okay, because we have no kernels
            km.shutdown_all()

    def test_tcp_cinfo(self):
        with self._get_tcp_km() as km:
            self._run_cinfo(km, 'tcp', localhost())

    def test_start_sequence_tcp_kernels(self):
        """Ensure that a sequence of kernel startups doesn't break anything."""
        with self._get_tcp_km() as km:
            self._run_lifecycle(km)
        with self._get_tcp_km() as km:
            self._run_lifecycle(km)
        with self._get_tcp_km() as km:
            self._run_lifecycle(km)

    def tcp_lifecycle_with_loop(self):
        # Ensure each thread has an event loop
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.raw_tcp_lifecycle()

    # static so picklable for multiprocessing on Windows
    @classmethod
    def raw_tcp_lifecycle(cls, test_kid=None):
        # Since @gen_test creates an event loop, we need a raw form of
        # test_tcp_lifecycle that assumes the loop already exists.
        with cls._get_tcp_km() as km:
            cls._run_lifecycle(km, test_kid=test_kid)

    @pytest.mark.skip("Parallel use is currently not properly vetted, fails often")
    def test_start_parallel_thread_kernels(self):
        self.raw_tcp_lifecycle()

        thread = threading.Thread(target=self.tcp_lifecycle_with_loop)
        thread2 = threading.Thread(target=self.tcp_lifecycle_with_loop)
        try:
            thread.start()
            thread2.start()
        finally:
            thread.join()
            thread2.join()

    @pytest.mark.skip("Parallel use is currently not properly vetted, fails often")
    def test_start_parallel_process_kernels(self):
        self.raw_tcp_lifecycle()

        thread = threading.Thread(target=self.tcp_lifecycle_with_loop)
        proc = mp.Process(target=self.raw_tcp_lifecycle)

        try:
            thread.start()
            proc.start()
        finally:
            proc.join()
            thread.join()

        assert proc.exitcode == 0