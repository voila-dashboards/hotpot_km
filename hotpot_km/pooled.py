# coding: utf-8

# Copyright (c) Vidar Tonaas Fauske.
# Distributed under the terms of the Modified BSD License.
"""Hotpot - Jupyter kernel manager helpers

This module contains
"""

import asyncio

from jupyter_client.multikernelmanager import AsyncMultiKernelManager

from traitlets import Bool, Dict, Float, Integer, List, Unicode, observe
from nbclient.util import run_sync, ensure_async



from .client_helper import ExecClient
from .limited import LimitedKernelManager, MaximumKernelsException
from .py_snippets import (
    python_update_cwd_code,
    python_update_env_code,
    python_init_import_code,
)


async def _wait_before(delay, aw):
    await asyncio.sleep(delay)
    return await aw

async def _await_then_kill(km, aw_id):
    return await km.get_kernel(await aw_id).shutdown_kernel()


def _ensure_event_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


class PooledKernelManager(LimitedKernelManager, AsyncMultiKernelManager):
    kernel_pools = Dict(Integer(0), config=True,
        help="Mapping from kernel name to the number of started kernels to keep on standby",
    )

    pool_kwargs = Dict(Dict(), config=True,
        help="Mapping from kernel name to the arguments passed to kernel_start when pre-warming"
    )

    strict_pool_names = Bool(config=True,
        help="Whether to allow starting kernels with other names than those explicitly listed in kernel_pools"
    )

    strict_pool_kwargs = Bool(config=True,
        help="Whether to allow starting kernels with other kwargs than those explicitly listed in pool_kwargs"
    )

    fill_delay = Float(1, config=True,
        help="Wait time before re-filling the pool after a kernel is used"
    )

    initialization_code = Dict(config=True,
        help='Code that gets executed at startup'
    )

    python_imports = List(Unicode(), [], config=True,
        help='List of Python modules/packages to import'
    )

    wait_at_startup = Bool(False, config=True,
        help="Wait till all kernels pools are filled at startup"
    )

    _pools = Dict()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        awaitable = self.fill_if_needed(delay=0)
        loop = _ensure_event_loop()
        if self.wait_at_startup:
            loop.run_until_complete(awaitable)
        else:
            loop.create_task(awaitable)
        self.observe(self._pool_size_changed, 'kernel_pools')
        self._discarded = []

    def _pool_size_changed(self, change):
        self.unfill_as_needed()
        self.fill_if_needed()

    def _should_use_pool(self, kernel_name, kwargs, only_if_available=True):
        """Verify name and kwargs, and check whether we should use the pool"""
        if "kernel_id" in kwargs:
            return False

        if self.strict_pool_names and kernel_name not in self.kernel_pools:
            raise ValueError("Cannot start kernel with name %r" % (kernel_name,))
        if self.strict_pool_kwargs and (
            kernel_name not in self.pool_kwargs or
            kwargs != self.pool_kwargs[kernel_name]
        ):
            raise ValueError("Cannot start kernel with kwargs %r" % (kwargs,))

        if only_if_available:
            return len(self._pools.get(kernel_name, ())) > 0
        else:
            return self.kernel_pools

    def unfill_as_needed(self):
        """Kills extra kernels in pool"""
        tasks = []
        for name, target in self.kernel_pools.items():
            pool = self._pools.get(name, [])
            self._pools[name] = pool
            for i in range(len(pool) - target):
                task = asyncio.create_task(_await_then_kill(self, pool.pop(0)))
                self._discarded.append(task)

    async def fill_if_needed(self, delay=None):
        """Start kernels until pool is full"""
        delay = delay if delay is not None else self.fill_delay
        all_tasks = []
        for name, target in self.kernel_pools.items():
            pool = self._pools.get(name, [])
            self._pools[name] = pool
            for i in range(target - len(pool)):
                kw = self.pool_kwargs.get(name, {})
                fut = super().start_kernel(kernel_name=name, **kw)
                # Start the work on the loop immediately, so it is ready when needed:
                task = asyncio.create_task(_wait_before(
                    delay,
                    self._initialize(name, fut)
                ))
                all_tasks.append(task)
                pool.append(task)
        await asyncio.gather(*all_tasks)

    async def _pop_pooled_kernel(self, kernel_name, kwargs):
        fut = self._pools[kernel_name].pop(0)
        return  await self._update_kernel(kernel_name, fut, kwargs)

    async def start_kernel(self, kernel_name=None, **kwargs):
        if kernel_name is None:
            kernel_name = self.default_kernel_name
        self.log.debug("Starting kernel: %s", kernel_name)
        kernel_id = None
        while kernel_id is None and self._should_use_pool(kernel_name, kwargs):
            try:
                kernel_id = await self._pop_pooled_kernel(kernel_name, kwargs)
            except MaximumKernelsException:
                pass
        if kernel_id is None:
            kernel_id = await super().start_kernel(kernel_name=kernel_name, **kwargs)

        asyncio.create_task(self.fill_if_needed())
        return kernel_id

    async def shutdown_kernel(self, kernel_id, *args, **kwargs):
        for pool in self._pools.values():
            for i, f in enumerate(pool):
                try:
                    if f.done() and f.result() == kernel_id:
                        pool.pop(i)
                        break
                except Exception as e:
                    if not isinstance(e, MaximumKernelsException):
                        self.log.exception("Kernel failed starting up")
                    pool.pop(i)
        return await super().shutdown_kernel(kernel_id, *args, **kwargs)

    async def shutdown_all(self, *args, **kwargs):
        await super().shutdown_all(*args, **kwargs)
        # Parent doesn't correctly add all created kernels until they have completed startup:
        for pool in self._pools.values():
            # The iteration gets confused if we don't copy pool
            for fut in tuple(pool):
                try:
                    kid = await fut
                except Exception as e:
                    if not isinstance(e, MaximumKernelsException):
                        self.log.exception("Kernel failed starting up")
                    continue
                if kid in self:
                    await self.shutdown_kernel(kid, *args, **kwargs)
        try:
            asyncio.gather(*self._discarded)
        except Exception as e:
            if not isinstance(e, MaximumKernelsException):
                self.log.exception("Kernel failed starting up")
        self._pools = {}
        self._discarded = []


    async def _update_kernel(self, kernel_name, kernel_id_future, kwargs):
        # Make sure that the kernel is in a state that matches kwargs
        # Currently supported is a python kernel, and the path/cwd and env arguments
        if kernel_name in ("python3", "python") and kwargs:
            # Avoid client overhead if not needed:
            if 'path' in kwargs or 'cwd' in kwargs or 'env' in kwargs:
                kernel_id = await kernel_id_future
                kernel = self.get_kernel(kernel_id)
                client = ExecClient(kernel)
                async with client.setup_kernel():
                    if 'path' in kwargs:
                        kwargs['cwd'] = self.cwd_for_path(kwargs.pop('path'))
                    if 'cwd' in kwargs:
                        cwd = kwargs.pop('cwd')
                        code = python_update_cwd_code.format(cwd=cwd)
                        self.log.debug("Updating preheated kernel CWD using")
                        await client.execute(code)
                    if 'env' in kwargs:
                        env = kwargs.pop('env')
                        code = python_update_env_code.format(env=env)
                        self.log.debug("Updating preheated kernel env vars")
                        await client.execute(code)
        if kwargs:
            self.log.debug("Unknown kwargs: %s", list(kwargs.keys()))

        return await kernel_id_future

    async def _initialize(self, kernel_name, kernel_id_future):
        """Run any configured initialization code in the kernel"""
        kernel_id = await kernel_id_future
        extension = None
        language = None

        kernel = self.get_kernel(kernel_id)

        try:
            language_to_extensions = {'python': 'py'}
            language = kernel.kernel_spec_manager.get_all_specs()[kernel_name]['spec']['language']
            extension = language_to_extensions[language]
        except Exception:
            pass

        py_imports = language == 'python' and self.python_imports

        if not extension and not py_imports:
            # Save some effort
            return kernel_id

        self.log.info("Initializing kernel: %s", kernel_name)

        client = ExecClient(kernel)

        from jupyter_core.paths import jupyter_config_path
        from pathlib import Path
        async with client.setup_kernel():
            if extension:
                for base_path in map(Path, jupyter_config_path()):
                    path = base_path / f'voila_kernel_pool_init_{kernel_name}.{extension}'
                    if path.exists():
                        with open(path) as f:
                            self.log.debug('Running %s for initializing kernel', path)
                            code = f.read()
                        await client.execute(code)
            if py_imports:
                code = python_init_import_code.format(modules=self.python_imports)
                await client.execute(code)
        self.log.debug("Initialized kernel: %s", kernel_name)
        return kernel_id



__all__ = [
    'PooledKernelManager',
]
