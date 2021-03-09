# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# This file is a paired down version of nbclient, so that
# it just a wrapper around jupyter_client that responds correctly to
# certain events.

import atexit
import collections
import datetime
import base64
import signal
from textwrap import dedent

from async_generator import asynccontextmanager
from contextlib import contextmanager

from time import monotonic
from queue import Empty
import asyncio
import typing as t

from traitlets.config.configurable import LoggingConfigurable
from traitlets import List, Unicode, Bool, Enum, Any, Type, Dict, Integer, default

from nbformat.v4 import output_from_msg
from jupyter_client import KernelManager
from jupyter_client.client import KernelClient

from nbclient.util import run_sync, ensure_async


class ControlSignal(Exception):
    pass

class ExecTimeoutError(TimeoutError, ControlSignal):
    pass

class ExecutionError(ControlSignal):
    def __init__(
            self,
            traceback: str,
            ename: str,
            evalue: str) -> None:
        super().__init__(traceback)
        self.traceback = traceback
        self.ename = ename
        self.evalue = evalue

    def __reduce__(self) -> tuple:
        return type(self), (self.traceback, self.ename, self.evalue)

    def __str__(self) -> str:
        s = self.__unicode__()
        if not isinstance(s, str):
            s = s.encode('utf8', 'replace')
        return s

    def __unicode__(self) -> str:
        return self.traceback

    @classmethod
    def from_msg(
            cls,
            msg: Dict):
        """Instantiate from message contents (message is either execute_reply or error)
        """
        tb = '\n'.join(msg.get('traceback', []))
        return cls(
            traceback=tb,
            ename=msg.get('ename', '<Error>'),
            evalue=msg.get('evalue', ''),
        )



class DeadKernelError(RuntimeError):
    pass

def timestamp() -> str:
    return datetime.datetime.utcnow().isoformat() + 'Z'


class ExecClient(LoggingConfigurable):
    """
    A client for executing code on a Jupyter kernel
    """

    timeout: int = Integer(
        None,
        allow_none=True,
        help=dedent(
            """
            The time to wait (in seconds) for output from executions.
            If an execution takes longer, a TimeoutError is raised.

            ``None`` or ``-1`` will disable the timeout. If ``timeout_func`` is set,
            it overrides ``timeout``.
            """
        ),
    ).tag(config=True)

    startup_timeout: int = Integer(
        60,
        help=dedent(
            """
            The time to wait (in seconds) for the kernel to start.
            If kernel startup takes longer, a RuntimeError is
            raised.
            """
        ),
    ).tag(config=True)

    iopub_timeout: int = Integer(
        4,
        allow_none=False,
        help=dedent(
            """
            The time to wait (in seconds) for IOPub output. This generally
            doesn't need to be set, but on some slow networks (such as CI
            systems) the default timeout might not be long enough to get all
            messages.
            """
        ),
    ).tag(config=True)

    shell_timeout_interval: int = Integer(
        5,
        allow_none=False,
        help=dedent(
            """
            The time to wait (in seconds) for Shell output before retrying.
            This generally doesn't need to be set, but if one needs to check
            for dead kernels at a faster rate this can help.
            """
        ),
    ).tag(config=True)


    def __init__(
            self,
            km: KernelManager = None,
            _store_outputs: bool = False, # for testing purposes
            **kw) -> None:
        """Initializes the execution manager.

        Parameters
        ----------
        km : KernelManager (optional)
            Optional kernel manager. If none is provided, a kernel manager will
            be created.
        """
        super().__init__(**kw)
        self.km: KernelManager = km
        self.kc: t.Optional[KernelClient] = None
        self._store_outputs = _store_outputs
        self._outputs = []

    async def _cleanup_kernel(self) -> None:
        assert self.km is not None
        try:
            # Queue the manager to kill the process, and recover gracefully if it's already dead.
            if await ensure_async(self.km.is_alive()):
                await ensure_async(self.km.shutdown_kernel())
        except RuntimeError as e:
            # The error isn't specialized, so we have to check the message
            if 'No kernel is running!' not in str(e):
                raise
        finally:
            # Remove any state left over even if we failed to stop the kernel
            await ensure_async(self.km.cleanup_resources())
            if getattr(self, "kc") and self.kc is not None:
                await ensure_async(self.kc.stop_channels())
                self.kc = None
                self.km = None

    _sync_cleanup_kernel = run_sync(_cleanup_kernel)

    async def start_new_kernel_client(self) -> KernelClient:
        """Creates a new kernel client.

        Returns
        -------
        kc : KernelClient
            Kernel client as created by the kernel manager ``km``.
        """
        assert self.km is not None
        self.kc = self.km.client()
        await ensure_async(self.kc.start_channels())
        try:
            await ensure_async(self.kc.wait_for_ready(timeout=self.startup_timeout))
        except RuntimeError:
            await self._cleanup_kernel()
            raise
        self.kc.allow_stdin = False
        return self.kc

    @asynccontextmanager
    async def setup_kernel(self) -> t.AsyncGenerator:
        """
        Context manager for setting up the kernel to execute a notebook.

        This assigns the Kernel Client(``self.kc``) if missing .

        When control returns from the yield it stops the client's zmq channels.

        Handlers for SIGINT and SIGTERM are also added to cleanup in case of unexpected shutdown.
        """

        # self._sync_cleanup_kernel uses run_async, which ensures the ioloop is running again.
        # This is necessary as the ioloop has stopped once atexit fires.
        atexit.register(self._sync_cleanup_kernel)

        def on_signal():
            asyncio.ensure_future(self._cleanup_kernel())
            atexit.unregister(self._sync_cleanup_kernel)

        loop = asyncio.get_event_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, on_signal)
            loop.add_signal_handler(signal.SIGTERM, on_signal)
        except (NotImplementedError, RuntimeError):
            # NotImplementedError: Windows does not support signals.
            # RuntimeError: Raised when add_signal_handler is called outside the main thread
            pass

        try:
            if self.kc:
                msg_id = await ensure_async(self.kc.kernel_info())
                await self.wait_for_reply(msg_id)
            else:
                await self.start_new_kernel_client()
            yield
        finally:
            atexit.unregister(self._sync_cleanup_kernel)
            try:
                loop.remove_signal_handler(signal.SIGINT)
                loop.remove_signal_handler(signal.SIGTERM)
            except (NotImplementedError, RuntimeError):
                pass

    async def execute(
            self,
            source: str,
            **kwargs) -> t.Optional[dict]:
        """
        Executes code. Requires that a setup_kernel context is held.

        Parameters
        ----------
        source :
            The source code to execute.
        kwargs :
            Any option for ``self.kernel_manager_class.start_kernel()``. Because
            that defaults to AsyncKernelManager, this will likely include options
            accepted by ``jupyter_client.AsyncKernelManager.start_kernel()``,
            which includes ``cwd``.

            ``reset_kc`` if True, the kernel client will be reset and a new one
            will be created (default: False).

        Returns
        -------
        The execute reply message, or None if skipped bc of empty code.

        Raises
        ------
        CellExecutionError
            If execution failed and should raise an exception, this will be raised
            with defaults about the failure.
        """

        assert self.kc is not None
        if not source.strip():
            self.log.debug("Skipping empty code")
            return None

        self.log.debug("Executing code")

        parent_msg_id = await ensure_async(
            self.kc.execute(
                source,
                store_history=False,
            )
        )
        exec_timeout = self._get_timeout()

        task_poll_kernel_alive = asyncio.ensure_future(
            self._poll_kernel_alive()
        )
        task_poll_output_msg = asyncio.ensure_future(
            self._poll_output_msg(parent_msg_id)
        )
        self.task_poll_for_reply = asyncio.ensure_future(
            self._poll_for_reply(
                parent_msg_id, exec_timeout, task_poll_output_msg, task_poll_kernel_alive
            )
        )
        try:
            exec_reply = await self.task_poll_for_reply
        except asyncio.CancelledError:
            # can only be cancelled by task_poll_kernel_alive when the kernel is dead
            task_poll_output_msg.cancel()
            raise DeadKernelError("Kernel died")
        except Exception as e:
            # Best effort to cancel request if it hasn't been resolved
            try:
                # Check if the task_poll_output is doing the raising for us
                if not isinstance(e, ControlSignal):
                    task_poll_output_msg.cancel()
            finally:
                raise

        self._check_raise_for_error(exec_reply)
        return exec_reply

    async def _poll_for_reply(
            self,
            msg_id: str,
            timeout: t.Optional[int],
            task_poll_output_msg: asyncio.Future,
            task_poll_kernel_alive: asyncio.Future) -> t.Dict:

        assert self.kc is not None
        new_timeout: t.Optional[float] = None
        if timeout is not None:
            deadline = monotonic() + timeout
            new_timeout = float(timeout)
        while True:
            try:
                msg = await ensure_async(self.kc.shell_channel.get_msg(timeout=new_timeout))
                if msg['parent_header'].get('msg_id') == msg_id:
                    try:
                        await asyncio.wait_for(task_poll_output_msg, self.iopub_timeout)
                    except (asyncio.TimeoutError, Empty):
                        if self.raise_on_iopub_timeout:
                            task_poll_kernel_alive.cancel()
                            raise ExecTimeoutError("Timeout waiting for IOPub output")
                        else:
                            self.log.warning("Timeout waiting for IOPub output")
                    task_poll_kernel_alive.cancel()
                    return msg
                else:
                    if new_timeout is not None:
                        new_timeout = max(0, deadline - monotonic())
            except Empty:
                # received no message, check if kernel is still alive
                assert timeout is not None
                task_poll_kernel_alive.cancel()
                await self._check_alive()
                await self._handle_timeout(timeout)

    async def _poll_output_msg(self, parent_msg_id: str) -> None:

        assert self.kc is not None
        while True:
            msg = await ensure_async(self.kc.iopub_channel.get_msg(timeout=None))
            if msg['parent_header'].get('msg_id') == parent_msg_id:
                if self.process_message(msg):
                    return

    async def _poll_kernel_alive(self) -> None:
        while True:
            await asyncio.sleep(1)
            try:
                await self._check_alive()
            except DeadKernelError:
                assert self.task_poll_for_reply is not None
                self.task_poll_for_reply.cancel()
                return

    def _get_timeout(self) -> int:
        timeout = self.timeout

        if not timeout or timeout < 0:
            timeout = None

        return timeout

    async def _handle_timeout(
            self,
            timeout: int) -> None:

        self.log.error("Timeout waiting for execute reply (%is)." % timeout)
        if self.interrupt_on_timeout:
            self.log.error("Interrupting kernel")
            assert self.km is not None
            await ensure_async(self.km.interrupt_kernel())
        else:
            raise ExecTimeoutError("Execution timed out")

    async def _check_alive(self) -> None:
        assert self.kc is not None
        if not await ensure_async(self.kc.is_alive()):
            self.log.error("Kernel died while waiting for execute reply.")
            raise DeadKernelError("Kernel died")

    async def wait_for_reply(
            self,
            msg_id: str) -> t.Optional[t.Dict]:

        assert self.kc is not None
        # wait for finish, with timeout
        timeout = self._get_timeout()
        cummulative_time = 0
        while True:
            try:
                msg = await ensure_async(
                    self.kc.shell_channel.get_msg(
                        timeout=self.shell_timeout_interval
                    )
                )
            except Empty:
                await self._check_alive()
                cummulative_time += self.shell_timeout_interval
                if timeout and cummulative_time > timeout:
                    await self._handle_timeout(timeout)
                    break
            else:
                if msg['parent_header'].get('msg_id') == msg_id:
                    return msg
        return None

    def _check_raise_for_error(
            self,
            exec_reply: t.Optional[t.Dict]) -> None:

        if exec_reply is None:
            return None

        exec_reply_content = exec_reply['content']
        if exec_reply_content['status'] != 'error':
            return None

        raise ExecutionError.from_msg(exec_reply_content)


    def process_message(self, msg: t.Dict) -> bool:
        """
        Processes a kernel message, updates cell state, and returns the
        resulting output object that was appended to cell.outputs.

        The input argument *cell* is modified in-place.

        Parameters
        ----------
        msg : dict
            The kernel message being processed.

        Returns
        -------
        Whether the message indicates computation completeness.

        """
        msg_type = msg['msg_type']
        self.log.debug("msg_type: %s", msg_type)
        content = msg['content']
        if msg_type == 'status':
            if content['execution_state'] == 'idle':
                return True
        elif (
            self._store_outputs and
            msg_type not in ['clear_output', 'comm', 'execute_input', 'update_display_data']
        ):
            # Assign output as our processed "result"
            self.output(self._outputs, msg)
        return False

    def output(
            self,
            outs: t.List,
            msg: t.Dict) -> t.Optional[t.List]:

        try:
            out = output_from_msg(msg)
        except ValueError:
            self.log.error("unhandled iopub msg: " + msg['msg_type'])
            return

        outs.append(out)
