
import asyncio
from contextlib import asynccontextmanager
from unittest import mock
from pathlib import Path
from subprocess import PIPE
from tempfile import TemporaryDirectory
from unittest import TestCase

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
import pytest
from tornado.testing import AsyncTestCase, gen_test
from traitlets.config.loader import Config

from ..client_helper import ExecClient
from .. import (
    PooledKernelManager,
    PooledMappingKernelManager,
    MaximumKernelsException,
)

from .utils import async_shutdown_all_direct


class TestInitializePooled(AsyncTestCase):

    # This is a snaity check for test_imports
    @gen_test(timeout=20)
    async def test_imports_not_used(self):
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.strict_pool_names = True
        c.python_imports = []
        km = PooledKernelManager(config=c)

        try:
            kid = await km.start_kernel()
            kernel = km.get_kernel(kid)
            self.assertIsNotNone(kernel)

            client = ExecClient(kernel, _store_outputs=True)
            async with client.setup_kernel():
                await client.execute('import sys\nprint("turtle" in sys.modules)')
            self.assertEqual(client._outputs, [{
                'name': 'stdout', 'output_type': 'stream', 'text': 'False\n'
            }])
        finally:
            await km.shutdown_all()

    @gen_test(timeout=20)
    async def test_imports(self):
        c = Config()
        c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
        c.PooledKernelManager.strict_pool_names = True
        c.PooledKernelManager.python_imports = ["turtle"]
        # Need mapping to resolve kernel language
        km = PooledKernelManager(config=c)

        try:
            kid = await km.start_kernel()
            kernel = km.get_kernel(kid)
            self.assertIsNotNone(kernel)

            client = ExecClient(kernel, _store_outputs=True)
            async with client.setup_kernel():
                await client.execute('import sys\nprint("turtle" in sys.modules)')
            self.assertEqual(client._outputs, [{
                'name': 'stdout', 'output_type': 'stream', 'text': 'True\n'
            }])
        finally:
            await km.shutdown_all()

    @pytest.mark.xfail() # initialize happens before update, so this won't work
    @gen_test(timeout=20)
    async def test_cwd_import(self):
        with TemporaryDirectory() as tmp_dir:
            # create a lcoal py module in cwd to test import
            foo_mod = Path(tmp_dir) / "foo_module.py"
            foo_mod.write_text("foo = 1")

            c = Config()
            c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
            c.PooledKernelManager.strict_pool_names = True
            c.PooledKernelManager.python_imports = ["foo_module"]
            km = PooledKernelManager(config=c)

            try:
                kid = await km.start_kernel(cwd=tmp_dir)
                kernel = km.get_kernel(kid)
                self.assertIsNotNone(kernel)

                client = ExecClient(kernel, _store_outputs=True)
                async with client.setup_kernel():
                    await client.execute('import sys\nprint("foo_module" in sys.modules)')
                self.assertEqual(client._outputs, [{
                    'name': 'stdout', 'output_type': 'stream', 'text': 'True\n'
                }])
            finally:
                await km.shutdown_all()


    @gen_test(timeout=20)
    async def test_file_init(self):
        with TemporaryDirectory() as tmp_dir:
            c = Config()
            c.PooledKernelManager.kernel_pools = {NATIVE_KERNEL_NAME: 1}
            c.PooledKernelManager.strict_pool_names = True
            # Need mapping manager to resolve init files:
            km = PooledKernelManager(config=c)

            with mock.patch("jupyter_core.paths.jupyter_config_path") as jcp:
                jcp.return_value = [tmp_dir]
                # create a lcoal py module in cwd to test import
                foo_mod = Path(tmp_dir) / f"voila_kernel_pool_init_{NATIVE_KERNEL_NAME}.py"
                foo_mod.write_text("foo = 1")

                try:
                    kid = await km.start_kernel()
                    kernel = km.get_kernel(kid)
                    self.assertIsNotNone(kernel)

                    client = ExecClient(kernel, _store_outputs=True)
                    async with client.setup_kernel():
                        await client.execute('print(foo)')
                    self.assertEqual(client._outputs, [{
                        'name': 'stdout', 'output_type': 'stream', 'text': '1\n'
                    }])
                finally:
                    await km.shutdown_all()
