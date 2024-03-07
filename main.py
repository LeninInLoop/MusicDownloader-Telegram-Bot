from run.bot import Bot
import asyncio, os

async def main():
    await Bot.initialize()
    await Bot.run()

asyncio.run(main())