from run.Bot import Bot
import asyncio

async def main():
    Bot.initialize()
    await Bot.run()

asyncio.run(main())