"""Single command to start Personal Agent"""
import asyncio
from pathlib import Path
from nanobot.main import Application


async def main():
    app = Application()
    try:
        await app.start(host="0.0.0.0", port=8765)
        # Keep running forever
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
