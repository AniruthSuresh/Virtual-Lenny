# import asyncio
# import websockets
# import json

# async def test():
#     uri = "wss://lp22uvez09.execute-api.ap-southeast-2.amazonaws.com/prod"
#     async with websockets.connect(uri) as ws:

#         await ws.send(json.dumps({"message": "How does investing in influencer marketing impact word-of-mouth referrals for the company's new subscribers?"}))
        
#         print("Lenny: ", end="", flush=True)
#         while True:
#             res = json.loads(await ws.recv())
#             if res["type"] == "chunk":
#                 print(res["content"], end="", flush=True)
#             elif res["type"] == "done":
#                 break

# asyncio.run(test())

import asyncio
import websockets
import json

async def test():
    uri = "wss://lp22uvez09.execute-api.ap-southeast-2.amazonaws.com/prod"
    # Use ping_interval=None to prevent the client from timing out during the model's 20s cold start
    async with websockets.connect(uri, ping_interval=None) as ws:

        payload = {"message": "How does Jen Abel attribute the success of her enterprise deals?"}
        await ws.send(json.dumps(payload))
        
        print("Lenny: ", end="", flush=True)
        
        while True:
            try:
                raw_res = await ws.recv()
                res = json.loads(raw_res)
                
                msg_type = res.get("type")

                if msg_type == "chunk":
                    print(res["content"], end="", flush=True)
                
                elif msg_type == "evaluation":
                    score_data = res["score"]
                    print(f"\n\n--- Evaluation Metrics ---")
                    print(f"🎯 Overall RAG Score: {score_data['overall']}% ({score_data['grade']})")
                    print(f"📊 Breakdown: {json.dumps(score_data['breakdown'], indent=2)}")
                
                elif msg_type == "done":
                    print("\n[End of message]")
                    break
                
                elif msg_type == "error":
                    print(f"\n❌ Backend Error: {res.get('message')}")
                    break

            except json.JSONDecodeError:
                print(f"\n❌ Received non-JSON message: {raw_res}")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                break

asyncio.run(test())