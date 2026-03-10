"""Single command to start Personal Agent"""
import asyncio
import os
from pathlib import Path
from nanobot.main import Application


async def main():
    app = Application()
    port = int(os.environ.get("PORT", 8765))
    try:
        await app.start(host="0.0.0.0", port=port)
        # Keep running forever
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
