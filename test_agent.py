import asyncio, json, websockets

TOKEN = "BS1KqcZGvTyGwjXP_zj2wIxG-1CdOzgGoH5wXtKm9wY"
URI = f"ws://localhost:8765/ws/{TOKEN}"

TASKS = [
    "What do you know about me?",
    "Search the web for the latest news about OpenAI and give me 3 bullet points",
    "Create a file called todo.txt in my workspace with 3 tasks I should do today based on my goals",
    "What is the current date and time? Use a shell command to find out",
]

async def test():
    async with websockets.connect(URI) as ws:
        welcome = await ws.recv()
        print(f"Connected: {welcome}\n")

        # Send all tasks
        for i, task in enumerate(TASKS, 1):
            print(f"{'='*60}")
            print(f"Sending TEST {i}: {task[:60]}")
            await ws.send(json.dumps({"type": "message", "content": task}))
            await asyncio.sleep(0.5)

        print(f"\n{'='*60}")
        print("All tasks sent. Waiting for responses (90s)...")
        print(f"{'='*60}\n")

        # Collect all responses
        responses = {}
        deadline = asyncio.get_event_loop().time() + 90

        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 5))
                data = json.loads(raw)

                if data.get("type") == "ping":
                    continue  # ignore keepalive
                elif data.get("type") in ("response", "message"):
                    content = data.get("content", "")
                    idx = len(responses) + 1
                    responses[idx] = content
                    print(f"RESPONSE {idx}:")
                    print(content)
                    print()
                    if len(responses) >= len(TASKS):
                        print("All responses received!")
                        break
            except asyncio.TimeoutError:
                continue

        if len(responses) < len(TASKS):
            print(f"Only got {len(responses)}/{len(TASKS)} responses before timeout")

asyncio.run(test())