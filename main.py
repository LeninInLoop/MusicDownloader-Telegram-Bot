from run import Bot
from utils import asyncio


async def main():
    await Bot.initialize()
    await Bot.run()


asyncio.run(main())
