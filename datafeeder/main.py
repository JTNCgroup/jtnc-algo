import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.security import HTTPAuthorizationCredentials
import rel
import json
import math
import datetime
import asyncio
import requests
import websockets
import redis.asyncio as aioredis

from pydantic import BaseModel
from starlette.websockets import WebSocketState

from common.expadvlib.const import TIMEZONE_NY
from common import auth

#REST_URL = 'https://api.polygon.io/v3/reference/stocks/contracts'
WS_URL_STOCKS   = 'wss://socket.polygon.io/stocks'
WS_URL_OPTIONS  = 'wss://socket.polygon.io/options'
API_KEY_STOCKS  = os.getenv("POLYGON_API_STOCKS")
API_KEY_OPTIONS = os.getenv("POLYGON_API_OPTIONS")

app = FastAPI()
connected_clients_stocks = set()
connected_clients_options = set()


REDIS_HOST    = "redis" #"localhost"
REDIS_PORT    = 6379
REDIS_CHANNEL_STOCKS  = "stocks"
REDIS_CHANNEL_OPTIONS = "options"
redis_pool    = aioredis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
redis_client  = aioredis.Redis(connection_pool=redis_pool)

def get_itm_symbol(ticker, price, spread_offset = 5) :
    url    = f'https://api.polygon.io/v3/snapshot/options/{ticker}'
    params = {'apiKey'   : API_KEY_OPTIONS,
              'limit' : 250,
              #'contract_type' : 'call',
              'strike_price.gte' : math.floor(price-15),
              'strike_price.lte' : math.ceil(price+15),
              'expiration_date' : datetime.datetime.now(tz=TIMEZONE_NY).strftime('%Y-%m-%d'),
              }
    
    try :
        r = requests.get(url=url, params=params)
    except Exception as e :
        return {'status' : 'error',
                'error'  : f'{repr(e)}'}
    
    if not r.ok :
        return {"status" : 'error',
                "error" : "cannot retrieve option chain symbol", 
                "received_data" : r.json()}
    
    s = r.json()

    if 'results' not in s :
        return {"status" : "error",
                "error" : "cannot retrieve data"}
    
    s = s['results']

    call_symbols = [(x['details']['strike_price'], x['details']['ticker'], x['last_quote']['midpoint']) for x in s if x['details']['contract_type'] == 'call']
    put_symbols = [(x['details']['strike_price'], x['details']['ticker'], x['last_quote']['midpoint']) for x in s if x['details']['contract_type'] == 'put']

    nearest_call = sorted([(price - x[0], x[1], x[2]) for x in call_symbols if price-x[0]>0])[0][1:]
    nearest_put  = sorted([(x[0] - price, x[1], x[2]) for x in put_symbols if x[0]-price>0])[0][1:]

    spread_second_leg_call = sorted([(price - x[0] + spread_offset, x[1], x[2]) for x in call_symbols if price-x[0]+spread_offset>0])[0][1:]
    spread_second_leg_put  = sorted([(price - x[0] + spread_offset, x[1], x[2]) for x in put_symbols if price-x[0]+spread_offset>0])[0][1:]

    return {'status' : 'ok',
            'call' : {'symbol' : nearest_call[0][2:], 'price': nearest_call[1]},
            'put' : {'symbol' : nearest_put[0][2:], 'price': nearest_put[1]},
            'spread_second_leg_call' : {'symbol' : spread_second_leg_call[0][2:], 'price': spread_second_leg_call[1]},
            'spread_second_leg_put'  : {'symbol' : spread_second_leg_put[0][2:], 'price': spread_second_leg_put[1]},
            }

@app.get("/")
async def root(user: str = Depends(auth.verify_token)) : 
   return {"message" : "Hello World!"}

@app.post("/create_user", response_model=auth.Token)
def create_user(user: auth.UserCreate, db=Depends(auth.get_db)) :
    token = auth.create_user_with_jwt(db, user.username)
    return {"access_token": token}

@app.post("/rotate_token", response_model=auth.Token)
def rotate_token(user: auth.UserCreate, db=Depends(auth.get_db)):
    new_token = auth.rotate_jwt(db, user.username)
    return {"access_token": new_token}

@app.post("/api")
async def restapi_price(request: Request, user=Depends(auth.verify_token)) :
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

@app.post("/tradingview")
async def tradingview_alert(request:Request) :
    data   = await request.json()
    ticker = data['ticker']
    price  = data['price']
    side   = data['side']

    # Get Option Symbol
    option_symbols = get_itm_symbol(ticker=ticker, price=price, spread_offset=5)
    if option_symbols['status'] == 'error' :
        return option_symbols
    
    # Send Order
    url = "https://us-central1-quantum-flo-auto-algo-d3c2b.cloudfunctions.net/new_order"
    buy_offset = 0.05
    sell_offset = 0.03

    match side :
        case 'buy' :
            payload = {"symbol": ticker.upper(),
                       "single_leg": {
                           "order": {"option_symbol": option_symbols['call']['symbol'],
                                     "type": "limit",
                                     "side": "buy_to_open",
                                     "quantity": 1,
                                     "price": option_symbols['call']['price'] + buy_offset,
                                     "tif": "day"},
                                     "class": "options"},
                        "spread" : {"legs" : [{"options_symbol" : option_symbols['call']['symbol'],
                                               "side" : "buy_to_open",
                                               "quantity": 1},
                                              {"options_symbol" : option_symbols['spread_second_leg_call']['symbol'],
                                               "side" : "sell_to_open",
                                               "quantity": 1}],
                        "class" : "multileg",
                        "price" : option_symbols['call']['price'] - option_symbols['spread_second_leg_call']['price'],
                        "type" : "limit",
                        "tif" : "day"}
                       }
        case 'sell' :
            payload = {"symbol": ticker.upper(),
                       "single_leg": {
                           "order": {"option_symbol": option_symbols['put']['symbol'],
                                     "type": "limit",
                                     "side": "buy_to_open",
                                     "quantity": 1,
                                     "price": option_symbols['put']['price'] + sell_offset,
                                     "tif": "day"},
                                     "class": "options"},
                       "spread" : {"legs" : [{"options_symbol" : option_symbols['put']['symbol'],
                                               "side" : "sell_to_open",
                                               "quantity": 1},
                                              {"options_symbol" : option_symbols['spread_second_leg_put']['symbol'],
                                               "side" : "buy_to_open",
                                               "quantity": 1}],
                                    "class" : "multileg",
                                    "price" : option_symbols['spread_second_leg_put']['price'] - option_symbols['put']['price'],
                                    "type"  : "limit",
                                    "tif"   : "day"}
                       }
    
    r = requests.post(url=url, json=payload)


    return r.json()

    



@app.websocket("/ws/stocks")
async def websocket_stocks(websocket: WebSocket) :
    token = websocket.headers.get("Authorization")
    if token is None:
        await websocket.close(code=1008)
        return
    try:
        if not token.lower().startswith("bearer") :
            await websocket.close(code=1008)
            return
        token = token.split(" ", 1)[1]
        token = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        db_gen = auth.get_db()
        db = next(db_gen)
        user = auth.verify_token(token, db=db)
    except:
        await websocket.close(code=1008)
        return
    await websocket.accept()

    connected_clients_stocks.add(websocket)
    print("Stock! Client connected!")

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connected_clients_stocks.remove(websocket)
        print("Client disconnected")

@app.websocket("/ws/options")
async def websocket_options(websocket: WebSocket) :
    token = websocket.headers.get("Authorization")
    if token is None:
        await websocket.close(code=1008)
        return
    try:
        if not token.lower().startswith("bearer") :
            await websocket.close(code=1008)
            return
        token = token.split(" ", 1)[1]
        token = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        db_gen = auth.get_db()
        db = next(db_gen)
        user = auth.verify_token(token, db=db)
    except Exception as e:
        print(f"Exception, {repr(e)}")
        await websocket.close(code=1008)
        return
    await websocket.accept()

    connected_clients_options.add(websocket)
    print("Stock! Client connected!")

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connected_clients_options.remove(websocket)
        print("Client disconnected")

async def polygon_stocks_listener() :
    while True:
        try:
            async with websockets.connect(WS_URL_STOCKS, ping_interval=20, ping_timeout=10) as websocket:
                print("Connected to Polygon WS for STOCKS")
                
                await websocket.send(json.dumps({"action": "auth", "params": API_KEY_STOCKS}))
                await websocket.send(json.dumps({"action": "subscribe", "params": "A.*"}))
                print(f"Sent payload")
                
                async for message in websocket:
                    if message:
                        #print('STOCKS', message, sep='\t')
                        await redis_client.publish(REDIS_CHANNEL_STOCKS, message)
        
        except websockets.ConnectionClosed as e:
            print(f"Stocks WebSocket disconnected: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        
        except Exception as e:
            print(f"Stocks Unexpected error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def polygon_options_listener() :
    while True:
        try:
            async with websockets.connect(WS_URL_OPTIONS, ping_interval=20, ping_timeout=10) as websocket:
                print("Connected to Polygon WS for OPTIONS")
                await websocket.send(json.dumps({"action": "auth", "params": API_KEY_OPTIONS}))
                await websocket.send(json.dumps({"action": "subscribe", "params": "A.*"}))
                print(f"Sent payload")
                
                async for message in websocket:
                    if message:
                        #print('OPTIONS', message, sep='\t')
                        await redis_client.publish(REDIS_CHANNEL_OPTIONS, message)
        
        except websockets.ConnectionClosed as e:
            print(f"Options WebSocket disconnected: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        
        except Exception as e:
            print(f"Options Unexpected error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def redis_stock_listener() :
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL_STOCKS)
    
    async for message in pubsub.listen() :
        if message["type"] == "message" :
            data = message["data"]
            disconnected = []
            for ws in connected_clients_stocks:
                if ws.application_state == WebSocketState.CONNECTED:
                    try :
                        await ws.send_text(data)
                    except Exception as e:
                        print(f"⚠️ Error sending to client, removing: {e}")
                        disconnected.append(ws)
                else :
                    disconnected.append(ws)
            
            for ws in disconnected:
                connected_clients_stocks.remove(ws)

async def redis_options_listener() :
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL_OPTIONS)
    
    async for message in pubsub.listen() :
        if message["type"] == "message" :
            data = message["data"]
            disconnected = []
            for ws in connected_clients_options:
                if ws.application_state == WebSocketState.CONNECTED:
                    try :
                        await ws.send_text(data)
                    except Exception as e:
                        print(f"⚠️ Error sending to client, removing: {e}")
                        disconnected.append(ws)
                else :
                    disconnected.append(ws)
            
            for ws in disconnected:
                connected_clients_options.remove(ws)

@app.on_event("startup")
def startup_event() :
    asyncio.create_task(polygon_stocks_listener())
    asyncio.create_task(redis_stock_listener())
    asyncio.create_task(polygon_options_listener())
    asyncio.create_task(redis_options_listener())