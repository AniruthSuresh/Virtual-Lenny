import asyncio
import websockets
import json

async def test():
    uri = "wss://lp22uvez09.execute-api.ap-southeast-2.amazonaws.com/prod"
    async with websockets.connect(uri) as ws:

        await ws.send(json.dumps({"message": "What's Lovable's key strategy for growth according to Elena Verna"}))
        
        print("Lenny: ", end="", flush=True)
        while True:
            res = json.loads(await ws.recv())
            if res["type"] == "chunk":
                print(res["content"], end="", flush=True)
            elif res["type"] == "done":
                break

asyncio.run(test())