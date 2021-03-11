
import asyncio

async def wait_before(delay, aw):
    await asyncio.sleep(delay)
    return await aw

async def await_then_kill(km, aw_id):
    return await km.shutdown_kernel(await aw_id)


def ensure_event_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop
