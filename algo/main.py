from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Literal
import rel
import asyncio
import nest_asyncio

from EA_01 import *

nest_asyncio.apply()

app = FastAPI()

class Levels(BaseModel) :
   id     : int
   time   : str
   symbol : Literal["SPX", "SPY", "QQQ"]
   side   : Literal["long", "short"]
   level  : float
   target : float
   type   : Literal["breakout", "reversal"]

class LevelID(BaseModel) :
   id : int

@app.get("/")
async def root() :
   return {"message" : "Hello Algo!"}

@app.post("/qfaa_levels")
async def new_levels(levels: List[Levels]) :
   x = [{'id'    : level.id,
         'time'  : level.time,
         'symbol': level.symbol,
         'side'  : level.side,
         'level' : level.level,
         'target': level.target,
         'type'  : level.type} for level in levels]
   
   print(levels)
   print(x)
   EA.add_level(x)
   return {'message' : 'levels are added',
           'levels' : EA.get_level()}

@app.get("/qfaa_levels")
async def new_levels() :
   return EA.get_level()

@app.delete("/qfaa_levels")
async def delete_level(level_id : LevelID) :
   if level_id == -1 :
      EA.clear_level()
      return {'message' : 'all levels are removed.'}
   EA.delete_level(level_id)
   return {'message' : 'level with {level_id} is removed.'}


@app.on_event("startup")
def startup_event() :
   global EA
   EA = TestEA("SPY")
   loop = asyncio.get_event_loop()
   loop.create_task(EA.AsyncRun())