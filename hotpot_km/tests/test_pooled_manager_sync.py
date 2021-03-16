from contextlib import contextmanager
from subprocess import PIPE
from unittest import TestCase

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
import pytest
from traitlets.config.loader import Config

from .. import (
    SyncPooledKernelManager,
    MaximumKernelsException,
)
from .utils_sync import shutdown_all_direct, TestKernelManager


# Test that it works as normal with default config
class TestSyncPooledKernelManagerUnused(TestKernelManager):
    __test__ = True

    # static so picklable for multiprocessing on Windows
    @staticmethod
    @contextmanager
    def _get_tcp_km():
        c = Config()
        km = SyncPooledKernelManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all(now=True)


# Test that it works with an unstrict pool
class TestSyncPooledKernelManagerApplied(TestKernelManager):
    __test__ = True

    # static so picklable for multiprocessing on Windows
    @staticmethod
    @contextmanager
    def _get_tcp_km():
        c = Config()
        c.SyncLimitedKernelManager.max_kernels = 4
        c.SyncPooledKernelManager.fill_delay = 0
        c.SyncPooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 2}
        c.SyncPooledKernelManager.pool_kwargs = {NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)}
        km = SyncPooledKernelManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all(now=True)

    def test_exceed_pool_size(self):
        with self._get_tcp_km() as km:
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 2)
            kids = []
            for i in range(4):
                kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            shutdown_all_direct(km)
            for kid in kids:
                self.assertNotIn(kid, km)

            # Cycle again to assure the pool survives that
            kids = []
            for i in range(4):
                kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)

            km.shutdown_all()
            for kid in kids:
                self.assertNotIn(kid, km)

    def test_decrease_pool_size(self):
        with self._get_tcp_km() as km:
            km.kernel_pools = {NATIVE_KERNEL_NAME: 1}
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 1)

    def test_increase_pool_size(self):
        with self._get_tcp_km() as km:
            km.kernel_pools = {NATIVE_KERNEL_NAME: 3}
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 3)

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


# Test that it works with an strict pool
class TestSyncPooledKernelManagerStrict(TestCase):
    def test_strict_name_correct(self):
        c = Config()
        c.SyncPooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.SyncPooledKernelManager.strict_pool_names = True
        km = SyncPooledKernelManager(config=c)

        try:
            kid = km.start_kernel(kernel_name=NATIVE_KERNEL_NAME, stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)

        finally:
            km.shutdown_all()
        self.assertNotIn(kid, km)

    def test_strict_name_incorrect(self):
        c = Config()
        c.SyncPooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.SyncPooledKernelManager.strict_pool_names = True
        km = SyncPooledKernelManager(config=c)

        try:
            with self.assertRaisesRegex(ValueError, "Cannot start kernel with name"):
                kid = km.start_kernel(kernel_name="foo", stdout=PIPE, stderr=PIPE)
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 1)
        finally:
            km.shutdown_all()

    def test_strict_kwargs_correct(self):
        c = Config()
        c.SyncPooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.SyncPooledKernelManager.pool_kwargs = {NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)}
        c.SyncPooledKernelManager.strict_pool_kwargs = True
        km = SyncPooledKernelManager(config=c)

        try:
            kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
        finally:
            km.shutdown_all()
        self.assertNotIn(kid, km)

    def test_strict_kwargs_incorrect(self):
        c = Config()
        c.SyncPooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.SyncPooledKernelManager.pool_kwargs = {NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)}
        c.SyncPooledKernelManager.strict_pool_kwargs = True
        km = SyncPooledKernelManager(config=c)

        try:
            with self.assertRaisesRegex(ValueError, "Cannot start kernel with kwargs"):
                kid = km.start_kernel()
            self.assertEqual(len(km._pools[NATIVE_KERNEL_NAME]), 1)
        finally:
            km.shutdown_all()

    def test_both_strict_correct(self):
        c = Config()
        c.SyncPooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.SyncPooledKernelManager.strict_pool_names = True
        c.SyncPooledKernelManager.pool_kwargs = {NATIVE_KERNEL_NAME: dict(stdout=PIPE, stderr=PIPE)}
        c.SyncPooledKernelManager.strict_pool_kwargs = True
        km = SyncPooledKernelManager(config=c)

        try:
            kid = km.start_kernel(kernel_name=NATIVE_KERNEL_NAME, stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
        finally:
            km.shutdown_all()
        self.assertNotIn(kid, km)
