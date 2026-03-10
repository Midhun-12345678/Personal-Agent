import asyncio, json, websockets

TOKEN = "BS1KqcZGvTyGwjXP_zj2wIxG-1CdOzgGoH5wXtKm9wY"
URI = f"ws://localhost:8765/ws/{TOKEN}"

# Flow: first message triggers Q1, then each answer gets next question
# Message 1: any text -> triggers "What's your name?"
# Message 2: your name -> triggers "What do you do for work?"
# Message 3: profession -> triggers "What are your goals?"
# Message 4: goals -> triggers "Morning or evening person?"
# Message 5: schedule -> triggers "Anything to always remember?"
# Message 6: preferences -> triggers completion message

CONVERSATION = [
    ("hi", "Expect: What's your name?"),
    ("Midhun", "Expect: Nice to meet you Midhun! What do you do for work?"),
    ("Software Engineer building AI products", "Expect: What are your top goals?"),
    ("Launch my personal AI assistant to the public", "Expect: Morning or evening person?"),
    ("Morning person, 9am to 6pm", "Expect: Anything to always remember?"),
    ("Be direct, take action, no fluff", "Expect: Perfect! I know enough..."),
]

async def test():
    async with websockets.connect(URI) as ws:
        welcome = await ws.recv()
        print(f"Connected: {welcome}")
        print()

        for message, expectation in CONVERSATION:
            await asyncio.sleep(1)
            await ws.send(json.dumps({"type": "message", "content": message}))
            print(f"Sent:   {message}")
            print(f"Hint:   {expectation}")
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(response)
                print(data)
                print(f"Agent:  {data['content']}")
                print()
            except asyncio.TimeoutError:
                print("TIMEOUT - no response in 30s")
                break

asyncio.run(test())