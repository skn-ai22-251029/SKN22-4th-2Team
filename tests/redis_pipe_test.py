import asyncio
import redis.asyncio as redis

async def test():
    r = redis.from_url('redis://localhost:6379/1')
    try:
        async with r.pipeline(transaction=True) as pipe:
            res1 = await pipe.set('a', 1)
            res2 = await pipe.expire('a', 60)
            print("Successfully awaited")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
