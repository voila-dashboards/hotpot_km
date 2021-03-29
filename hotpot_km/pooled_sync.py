# coding: utf-8

# Copyright (c) Vidar Tonaas Fauske.
# Distributed under the terms of the Modified BSD License.
"""Hotpot - Jupyter kernel manager helpers

This module contains
"""

import asyncio

from jupyter_client.multikernelmanager import MultiKernelManager
from traitlets import Bool, Dict, Float, Integer, List, Unicode, observe

from .async_utils import ensure_event_loop, just_run
from .client_helper import ExecClient, DeadKernelError
from .limited import SyncLimitedKernelManager, MaximumKernelsException
from .py_snippets import (
    python_update_cwd_code,
    python_update_env_code,
    python_init_import_code,
)


async def _wait_before(delay, aw):
    await asyncio.sleep(delay)
    return await aw


def _ensure_event_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


class SyncPooledKernelManager(SyncLimitedKernelManager):
    kernel_pools = Dict(
        Integer(0),
        config=True,
        help="Mapping from kernel name to the number of started kernels to keep on standby",
    )

    pool_kwargs = Dict(
        Dict(),
        config=True,
        help="Mapping from kernel name to the arguments passed to kernel_start when pre-warming",
    )

    strict_pool_names = Bool(
        config=True,
        help="Whether to allow starting kernels with other names than those explicitly listed in kernel_pools",
    )

    strict_pool_kwargs = Bool(
        config=True,
        help="Whether to allow starting kernels with other kwargs than those explicitly listed in pool_kwargs",
    )

    fill_delay = Float(
        1,
        config=True,
        help="Wait time before re-filling the pool after a kernel is used",
    )

    initialization_code = Dict(config=True, help="Code that gets executed at startup")

    python_imports = List(
        Unicode(), [], config=True, help="List of Python modules/packages to import"
    )

    _pools = Dict()
    _init_futs = Dict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fill_if_needed(delay=0)
        self.observe(self._pool_size_changed, "kernel_pools")
        self._discarded = []

    def _pool_size_changed(self, change):
        self.unfill_as_needed()
        self.fill_if_needed()

    def _should_use_pool(self, kernel_name, kwargs):
        """Verify name and kwargs, and check whether we should use the pool"""
        if "kernel_id" in kwargs:
            return False

        if self.strict_pool_names and kernel_name not in self.kernel_pools:
            raise ValueError("Cannot start kernel with name %r" % (kernel_name,))
        if self.strict_pool_kwargs and (
            kernel_name not in self.pool_kwargs or kwargs != self.pool_kwargs[kernel_name]
        ):
            raise ValueError("Cannot start kernel with kwargs %r" % (kwargs,))

        return len(self._pools.get(kernel_name, ())) > 0

    def unfill_as_needed(self):
        """Kills extra kernels in pool"""
        tasks = []
        for name, target in self.kernel_pools.items():
            pool = self._pools.get(name, [])
            self._pools[name] = pool
            for i in range(len(pool) - target):
                kernel_id = pool.pop(0)
                self.shutdown_kernel(kernel_id)

    def fill_if_needed(self, delay=None):
        """Start kernels until pool is full"""
        loop = ensure_event_loop()
        for name, target in self.kernel_pools.items():
            pool = self._pools.get(name, [])
            self._pools[name] = pool
            for i in range(target - len(pool)):
                kw = self.pool_kwargs.get(name, {})
                kernel_id = just_run(super().start_kernel(kernel_name=name, **kw))
                # Todo: use delay
                # Start the work on the loop immediately, so it is ready when needed:
                self._init_futs[kernel_id] = loop.create_task(self._initialize(name, kernel_id))
                pool.append(kernel_id)

    async def wait_for_pool(self):
        await asyncio.gather(*self._init_futs.values())

    async def _pop_pooled_kernel(self, kernel_name, kwargs):
        self.log.debug("Using kernel from pool: %s", kernel_name)
        kernel_id = self._pools[kernel_name].pop(0)
        await self._init_futs.pop(kernel_id)
        return await self._update_kernel(kernel_name, kernel_id, kwargs)

    def start_kernel(self, kernel_name=None, **kwargs):
        if kernel_name is None:
            kernel_name = self.default_kernel_name
        self.log.debug("Starting kernel: %s", kernel_name)
        kernel_id = kwargs.get("kernel_id")
        while kernel_id is None and self._should_use_pool(kernel_name, kwargs):
            try:
                kernel_id = just_run(self._pop_pooled_kernel(kernel_name, kwargs))
            except DeadKernelError:
                pass
        if kernel_id is None or kwargs.get("kernel_id") is not None:
            kernel_id = just_run(super().start_kernel(kernel_name=kernel_name, **kwargs))

        try:
            self.fill_if_needed()
        except MaximumKernelsException:
            pass
        return kernel_id

    def restart_kernel(self, kernel_id, **kwargs):
        km = self.get_kernel(kernel_id)
        kernel_name = km.kernel_name
        just_run(super().restart_kernel(kernel_id, **kwargs))
        just_run(self._update_kernel(kernel_name, kernel_id, km._launch_args))
        just_run(self._initialize(kernel_name, kernel_id))

    def shutdown_kernel(self, kernel_id, *args, **kwargs):
        if kernel_id in self._init_futs:
            self._init_futs.pop(kernel_id).cancel()
        return super().shutdown_kernel(kernel_id, *args, **kwargs)

    def shutdown_all(self, *args, **kwargs):
        for pool in self._pools.values():
            # The iteration gets confused if we don't copy pool
            for kernel_id in tuple(pool):
                self.shutdown_kernel(kernel_id, *args, **kwargs)
        for kernel_id in self.list_kernel_ids():
            self.shutdown_kernel(kernel_id, *args, **kwargs)
        self._pools = {}
        self._init_futs = {}

    async def _update_kernel(self, kernel_name, kernel_id, kwargs):
        base_kws = self.pool_kwargs.get(kernel_name)
        if base_kws:
            new_kws = {}
            for k, v in kwargs.items():
                if k not in base_kws:
                    new_kws[k] = v
                elif base_kws[k] != kwargs[k]:
                    new_kws[k] = v
        else:
            new_kws = kwargs

        # Make sure that the kernel is in a state that matches kwargs
        # Currently supported is a python kernel, and the path/cwd and env arguments
        if kernel_name in ("python3", "python") and new_kws:
            # Avoid client overhead if not needed:
            if "path" in new_kws or "cwd" in new_kws or "env" in new_kws:
                kernel = self.get_kernel(kernel_id)
                client = ExecClient(kernel)
                async with client.setup_kernel():
                    if "path" in new_kws:
                        new_kws["cwd"] = self.cwd_for_path(new_kws.pop("path"))
                    if "cwd" in new_kws:
                        cwd = new_kws.pop("cwd")
                        code = python_update_cwd_code.format(cwd=cwd)
                        self.log.debug("Updating preheated kernel CWD using")
                        await client.execute(code)
                    if "env" in new_kws:
                        env = new_kws.pop("env")
                        code = python_update_env_code.format(env=env)
                        self.log.debug("Updating preheated kernel env vars")
                        await client.execute(code)
        if new_kws:
            self.log.debug("Unknown kwargs: %s", list(new_kws.keys()))

        return kernel_id

    async def _initialize(self, kernel_name, kernel_id):
        """Run any configured initialization code in the kernel"""
        extension = None
        language = None

        kernel = self.get_kernel(kernel_id)

        try:
            language_to_extensions = {"python": "py"}
            language = kernel.kernel_spec_manager.get_all_specs()[kernel_name]["spec"]["language"]
            extension = language_to_extensions[language]
        except Exception:
            pass

        py_imports = language == "python" and self.python_imports

        if not extension and not py_imports:
            # Save some effort
            return kernel_id

        self.log.info("Initializing kernel: %s", kernel_id)

        client = ExecClient(kernel)

        from jupyter_core.paths import jupyter_config_path
        from pathlib import Path

        async with client.setup_kernel():
            if extension:
                for base_path in map(Path, jupyter_config_path()):
                    path = base_path / f"kernel_pool_init_{kernel_name}.{extension}"
                    if path.exists():
                        with open(path) as f:
                            self.log.debug("Running %s for initializing kernel", path)
                            code = f.read()
                        await client.execute(code)
            if py_imports:
                code = python_init_import_code.format(modules=self.python_imports)
                await client.execute(code)
        self.log.info("Initialized kernel: %s", kernel_id)
        return kernel_id


__all__ = [
    "SyncPooledKernelManager",
]
