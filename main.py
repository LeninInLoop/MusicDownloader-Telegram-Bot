from run import Bot
import asyncio

async def main():
    await Bot.initialize()
    await Bot.run()

asyncio.run(main())