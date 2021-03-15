
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from subprocess import PIPE
from tempfile import TemporaryDirectory
from unittest import TestCase

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
import pytest
from tornado.testing import AsyncTestCase, gen_test
from traitlets.config.loader import Config

from ..client_helper import ExecClient
try:
    from .. import (
        PooledKernelManager,
        PooledMappingKernelManager,
        MaximumKernelsException,
    )
except ImportError:
    pass

from .utils import async_shutdown_all_direct


class TestUpdatePooled(AsyncTestCase):
    @gen_test
    async def test_kernel_ok(self):
        # Just test that we can start a kernel and communicate with it.
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.strict_pool_names = True
        km = PooledKernelManager(config=c)

        kid = await km.start_kernel()
        kernel = km.get_kernel(kid)
        self.assertIsNotNone(kernel)

        try:
            client = ExecClient(kernel, _store_outputs=True)
            async with client.setup_kernel():
                await client.execute('import os\nprint(os.environ.get("VARFOO"))')
            self.assertEqual(client._outputs, [{
                'name': 'stdout', 'output_type': 'stream', 'text': 'None\n'
            }])
        finally:
            await km.shutdown_all()

    @gen_test
    async def test_env(self):
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.strict_pool_names = True
        km = PooledKernelManager(config=c)

        try:
            kid = await km.start_kernel(env={'VARFOO': 'BARBAR'})
            kernel = km.get_kernel(kid)
            self.assertIsNotNone(kernel)

            client = ExecClient(kernel, _store_outputs=True)
            async with client.setup_kernel():
                await client.execute('import os\nprint(os.environ.get("VARFOO"))')
            self.assertEqual(client._outputs, [{
                'name': 'stdout', 'output_type': 'stream', 'text': 'BARBAR\n'
            }])
        finally:
            await km.shutdown_all()

    @gen_test
    async def test_cwd(self):
        with TemporaryDirectory() as tmp_dir:
            c = Config()
            c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
            c.PooledKernelManager.strict_pool_names = True
            km = PooledKernelManager(config=c)

            # create a local py module in cwd to test import
            foo_mod = Path(tmp_dir) / "foo_module.py"
            foo_mod.write_text("foo = 1")

            try:
                kid = await km.start_kernel(cwd=tmp_dir)
                kernel = km.get_kernel(kid)
                self.assertIsNotNone(kernel)

                client = ExecClient(kernel, _store_outputs=True)
                async with client.setup_kernel():
                    await client.execute('import foo_module\nprint(foo_module.__file__)')
                self.assertEqual(client._outputs, [{
                    'name': 'stdout', 'output_type': 'stream', 'text': f'{foo_mod.resolve()}\n'
                }])
            finally:
                await km.shutdown_all()
