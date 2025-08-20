from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
import rel
import json
import asyncio
import requests
import websockets
import redis.asyncio as aioredis

from pydantic import BaseModel
from starlette.websockets import WebSocketState

#REST_URL = 'https://api.polygon.io/v3/reference/stocks/contracts'
WS_URL   = 'wss://socket.polygon.io/stocks'
API_KEY  = "VI6KWvmzTp5sDsDUfwZbJapZHoWOSFbb"

app = FastAPI()
connected_clients = set()

REDIS_HOST    = "redis" #"localhost"
REDIS_PORT    = 6379
REDIS_CHANNEL = "stocks"
redis_pool    = aioredis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
redis_client  = aioredis.Redis(connection_pool=redis_pool)

@app.get("/")
async def root() : 
   return {"message" : "Hello World!"}

@app.post("/api")
async def restapi_price(request: Request) :
    try:
        data = await request.json()
        
        url    = data['url']
        params = data['params']
        r = requests.get(url=url, params=params)
        if not r.ok :
           return {"status": "error", "message": r.json()}
        return {"status": "success", "received_data": r.json()}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.websocket("/ws")
async def websocket_price(websocket: WebSocket) :
    await websocket.accept()
    connected_clients.add(websocket)
    print("Client connected")

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("Client disconnected")

async def polygon_listener() :
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as websocket:
                print("Connected to Polygon WS")
                
                await websocket.send(json.dumps({"action": "auth", "params": API_KEY}))
                await websocket.send(json.dumps({"action": "subscribe", "params": "A.*"}))
                print(f"Sent payload\n\n")
                
                async for message in websocket:
                    if message:
                        await redis_client.publish(REDIS_CHANNEL, message)
        
        except websockets.ConnectionClosed as e:
            print(f"WebSocket disconnected: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def redis_listener() :
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"]
            disconnected = []
            for ws in connected_clients:
                if ws.application_state == WebSocketState.CONNECTED:
                    try:
                        await ws.send_text(data)
                    except Exception as e:
                        print(f"⚠️ Error sending to client, removing: {e}")
                        disconnected.append(ws)
                else :
                    disconnected.append(ws)
            
            for ws in disconnected:
                connected_clients.remove(ws)

@app.on_event("startup")
def startup_event() :
    asyncio.create_task(polygon_listener())
    asyncio.create_task(redis_listener())