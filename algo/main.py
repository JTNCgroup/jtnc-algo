from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Literal
import rel
import asyncio

from pydantic import BaseModel

from EA_01 import *

app = FastAPI()

class Levels(BaseModel) :
   id     : int
   time   : str
   symbol : Literal["SPX", "SPY", "QQQ"]
   side   : Literal["long", "short"]
   level  : float
   target : float
   type   : Literal["breakout", "reversal"]

@app.get("/")
async def root() :
   return {"message" : "Hello World!"}

@app.post("/qfaa_levels")
async def new_levels(levels: List[Levels]) :   
   x = [{'id'    : level.id,
         'time'  : level.time,
         'symbol': level.symbol,
         'side'  : level.side,
         'level' : level.level,
         'target': level.target,
         'type'  : level.type} for level in levels]
   EA.add_level(x)
   return EA.get_level()

@app.get("/qfaa_levels")
async def new_levels() :
   return EA.get_level()

@app.on_event("startup")
def startup_event() :
   global EA
   EA = TestEA()
   loop = asyncio.get_event_loop()
   loop.create_task(EA.AsyncRun())