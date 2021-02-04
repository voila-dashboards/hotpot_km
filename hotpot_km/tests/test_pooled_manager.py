
from contextlib import contextmanager
from subprocess import PIPE
from unittest import TestCase

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
import pytest
from traitlets.config.loader import Config

from .. import (
    PooledKernelManager,
    MaximumKernelsException,
)

from .utils import shutdown_all_direct, TestKernelManager

# Test that it works as normal with default config
class TestPooledKernelManagerUnused(TestKernelManager):
    __test__ = True

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        km = PooledKernelManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all()


# Test that it works with an unstrict pool
class TestPooledKernelManagerApplied(TestKernelManager):
    __test__ = True

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 2
        c.PooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        km = PooledKernelManager(config=c)
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
                self.assertEqual(len(km._pool), 2)

            shutdown_all_direct(km)
            for kid in kids:
                self.assertNotIn(kid, km)

            # Cycle again to assure the pool survives that
            kids = []
            for i in range(4):
                kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
                self.assertIn(kid, km)
                kids.append(kid)
                self.assertEqual(len(km._pool), 2)

            km.shutdown_all()
            for kid in kids:
                self.assertNotIn(kid, km)


# Test that it works with an strict pool
class TestPooledKernelManagerStrict(TestCase):

    @contextmanager
    def _get_tcp_km(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 2
        c.PooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        km = PooledKernelManager(config=c)
        try:
            yield km
        finally:
            km.shutdown_all()

    def test_strict_name_correct(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 1
        c.PooledKernelManager.pool_kernel_name = NATIVE_KERNEL_NAME
        c.PooledKernelManager.strict_pool_names = True
        km = PooledKernelManager(config=c)

        try:
            kid = km.start_kernel(kernel_name=NATIVE_KERNEL_NAME, stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)

        finally:
            km.shutdown_all()
        self.assertNotIn(kid, km)

    def test_strict_name_incorrect(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 1
        c.PooledKernelManager.pool_kernel_name = NATIVE_KERNEL_NAME
        c.PooledKernelManager.strict_pool_names = True
        km = PooledKernelManager(config=c)

        try:
            with self.assertRaisesRegex(ValueError, 'Cannot start kernel with name'):
                kid = km.start_kernel(kernel_name='foo', stdout=PIPE, stderr=PIPE)
            self.assertEqual(len(km), 1)
        finally:
            km.shutdown_all()

    def test_strict_kwargs_correct(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 1
        c.PooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        c.PooledKernelManager.strict_pool_kwargs = True
        km = PooledKernelManager(config=c)

        try:
            kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
        finally:
            km.shutdown_all()
        self.assertNotIn(kid, km)

    def test_strict_kwargs_incorrect(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 1
        c.PooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        c.PooledKernelManager.strict_pool_kwargs = True
        km = PooledKernelManager(config=c)

        try:
            with self.assertRaisesRegex(ValueError, 'Cannot start kernel with kwargs'):
                kid = km.start_kernel()
            self.assertEqual(len(km), 1)
        finally:
            km.shutdown_all()

    def test_both_strict_correct(self):
        c = Config()
        c.PooledKernelManager.kernel_pool_size = 1
        c.PooledKernelManager.pool_kernel_name = NATIVE_KERNEL_NAME
        c.PooledKernelManager.strict_pool_names = True
        c.PooledKernelManager.pool_kwargs = dict(stdout=PIPE, stderr=PIPE)
        c.PooledKernelManager.strict_pool_kwargs = True
        km = PooledKernelManager(config=c)

        try:
            kid = km.start_kernel(kernel_name=NATIVE_KERNEL_NAME, stdout=PIPE, stderr=PIPE)
            self.assertIn(kid, km)
        finally:
            km.shutdown_all()
        self.assertNotIn(kid, km)
