# -*- coding: utf-8 -*-
import json
#import time
import datetime
import requests
import redis.asyncio as aioredis
#from zoneinfo import ZoneInfo
from enum import Enum

import asyncio
import websockets

#import nest_asyncio
#nest_asyncio.apply()

import sys
sys.path.append('expadvlib')
import bars
from const import TIMEFRAME, DATAFEEDER, TIMEZONE_NY
from indicators import *

WS_URL = "ws://34.61.153.252:8111/ws"
REDIS_HOST    = "redis" #"localhost"
REDIS_PORT    = 6379
REDIS_CHANNEL = "stocks"
redis_pool    = aioredis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
redis_client  = aioredis.Redis(connection_pool=redis_pool)


class BaseEA :
    MODE = Enum("MODE", [("LIVE", 0), ("TEST", 1)])
    # DATA_FEEDER = Enum("DATA_FEEDER", [("WEBSOCKET", 0), ("REDIS", 1)])
    def __init__(self):
        self.__mode = self.MODE.LIVE
        self.datafeeder = DATAFEEDER.REDIS
    
    async def AsyncRun(self, datafeeder=DATAFEEDER.REDIS) :
        self.__mode = self.MODE.LIVE
        self.datafeeder = datafeeder
        # match datafeeder :
        #     case 'websocket':
        #         self.datafeeder = self.DATA_FEEDER.WEBSOCKET
        #     case 'redis' :
        #         self.datafeeder = self.DATA_FEEDER.REDIS
        
        await self.OnStart()
        await self._LoopLive()
        
    async def OnStart(self) :
        pass
    
    async def OnUpdate(self) :
        pass
    
    async def OnBar(self) :
        pass
    
    async def _LoopLive(self) :
        match self.datafeeder :
            case DATAFEEDER.WEBSOCKET :
                while True:
                    try:
                        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as websocket:
                            print("Connected to JTNC DataFeeder")
                        
                            async for message in websocket:
                                if message:
                                    self.message = json.loads(message)
                                    await self.OnUpdate()
                                    await self.OnBar()
                            
                    except websockets.ConnectionClosed as e:
                        print(f"WebSocket disconnected: {e}. Reconnecting in 5 seconds...")
                        await asyncio.sleep(5)
                    
                    except Exception as e:
                        print(f"Unexpected error: {e}. Retrying in 5 seconds...")
                        await asyncio.sleep(5)
            case DATAFEEDER.REDIS :
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(REDIS_CHANNEL)

                async for message in pubsub.listen():
                    if message["type"] == "message" :

                        self.message = json.loads(message["data"])
                        await self.OnUpdate()
                        await self.OnBar()
                        
                        # try :
                        #     self.message = json.loads(message["data"])
                        #     await self.OnUpdate()
                        #     await self.OnBar()
                        # except Exception as e :
                        #     print(f"Error on Redis Mode : {e}")
    
    def _LoopTest(self) :
        pass
    
class TestEA(BaseEA) :
    def __init__(self,
                 ticker,
                 period_rsi        = 14,
                 period_stoch_k    = 3,
                 period_stoch_d    = 3,
                 period_atr        = 12,
                 period_donchian   = 12,
                 period_chandelier_range = 22, 
                 period_chandelier_atr   = 22, 
                 period_chandelier_multiple = 3.0
                 ) :
        
        super().__init__()
        self.ticker         = ticker
        self.period_rsi     = period_rsi
        self.period_stoch_k = period_stoch_k
        self.period_stoch_d = period_stoch_d
        self.period_atr     = period_atr
        
        self.period_donchian         = period_donchian
        self.period_chandelier_range = period_chandelier_range
        self.period_chandelier_atr   = period_chandelier_atr
        self.period_chandelier_multiple = period_chandelier_multiple
        
        self.levels = []
        
        self.__is_updated = False
        self.order = None
        
    async def OnStart(self) :
        self.bar_m1 = bars.AggregateBar(TIMEFRAME.M1, keys=['s', 'o', 'h', 'l', 'c', 'v'])
        self.bar_m5 = bars.AggregateBar(TIMEFRAME.M5, keys=['s', 'o', 'h', 'l', 'c', 'v'])
        self.rsi   = RSI(self.period_rsi)
        self.stoch = Stochastic(self.period_stoch_k, self.period_stoch_d, 1)
        self.atr   = ATR(self.period_atr)
        
        self.donchian   = PriceChannel(self.period_donchian)
        self.chandelier = ChandelierExit(self.period_chandelier_range, self.period_chandelier_atr, self.period_chandelier_multiple)
        
        # Initialize Indicators
        b = self.DownloadData()
        for bar in b :
            bar['s'] = bar['t']
            self.bar_m1.OnBar(bar)
            self.bar_m5.OnBar(bar)
        
        await self._UpdateInd()

        #self.display_data()
        #exit()
        
    def display_data(self) :
        print(f'time           : {datetime.datetime.fromtimestamp(self.bar_m1.Time(-1), TIMEZONE_NY)}')
        print(f'bar            : {self.bar_m1.Open(-1)} {self.bar_m1.High(-1)} {self.bar_m1.Low(-1)} {self.bar_m1.Close(-1)}')
        print(f'Number of bars : {self.bar_m1.Nrates()}')
        print()
        
    async def _UpdateInd(self) :
        self.rsi.OnCalculate(self.bar_m1.Close())
        self.stoch.OnCalculate(self.rsi[:], self.rsi[:], self.rsi[:])
        self.atr.OnCalculate(self.bar_m5.High(), self.bar_m5.Low(), self.bar_m5.Close())
        
        self.donchian.OnCalculate(self.bar_m1.High(), self.bar_m1.Low())
        self.chandelier.OnCalculate(self.bar_m1.High(), self.bar_m1.Low(), self.bar_m1.Close())
    
    async def OnUpdate(self) :
        for m in self.message :
            if m['sym'] == self.ticker :
                previous_rates = self.bar_m1.Nrates()
                self.bar_m1.OnBar(m)
                self.bar_m5.OnBar(m)
                
                await self._UpdateInd()
                
                if self.bar_m1.Nrates() > previous_rates :
                    self.__is_updated = True
                else :
                    self.__is_updated = False
    
    async def OnBar(self) :
        if (not self.__is_updated) or (self.bar_m1.Nrates()<=0) or (self.bar_m5.Nrates()<=0) :
            return
        
        self.display_data()

        # Exit Rule
        self.exit_rule()
        
        # Entry Rule
        self.entry_rule()
        
        # Reset Daily Levels at 16:00 East-Coast Time
        self.reset_daily_level()

        self.__is_updated = False
    
    def exit_rule(self) :
        if self.order is None :
            return
        
        if (self.order['side'] == 'buy') :
            if (self.bar_m1.Close(-1) - self.order['entry']) > 0.5 :
                self.exit_type = 'chandelier'
            
            match self.exit_type :
                case 'donchian' :
                    if self.order['sl'] < self.donchian[1][-1] :
                        self.order['sl'] = self.donchian[1][-1]
                case 'chandelier' :
                    if self.order['sl'] < self.chandelier[0][-1] :
                        self.order['sl'] = self.chandelier[0][-1]
            
            if self.bar_m1.Close(-1) < self.order['sl'] :
                # TODO : Exit
                self.order = None
        
        elif (self.order['side'] == 'sell') :
            if (self.order['entry']-self.bar_m1.Close()) > 0.5 :
                self.exit_type = 'chandelier'
            
            match self.exit_type :
                case 'donchian' :
                    if self.order['sl'] > self.donchian[0][-1] :
                        self.order['sl'] = self.donchian[0][-1]
                case 'chandelier' :
                    if self.order['sl'] > self.chandelier[1][-1] :
                        self.order['sl'] = self.chandelier[1][-1]
            
            if self.bar_m1.Close(-1) > self.order['sl'] :
                # TODO : Exit
                self.order = None
    
    def entry_rule(self) :
        # TODO : Check if strategy pausing
        
        if self.bar_m1.Nrates() < max(self.period_stoch_k, self.period_atr) :
            return

        rsi_up = self.stoch[0][-1] > self.stoch[1][-1]
        rsi_dn = self.stoch[0][-1] < self.stoch[1][-1]
        
        for row in self.levels :
            side   = row['side']
            type_  = row['type']
            level  = row['level']
            target = row['target']
            
            buf = [(level + self.atr[i], level - self.atr[i]) for i in (-1, -2, -3)]
            near_recent = any([self._in_region(*x) for x in buf])
            
            if not near_recent :
                continue
            
            long_breakout  = (side=='long' and type_ =='breakout')
            short_reversal = (side=='short' and type_ =='reversal')
            short_breakout = (side=='short' and type_=='breakout')
            long_reversal  = (side=='long' and type_=='reversal')
            
            if long_breakout or short_reversal :
                break_ = self.bar_m1[-1] > level
                rsi_cross_recent = self._crossunder(self.stoch[0][-2:], self.stoch[1][-2:]) or \
                                   self._crossunder(self.stoch[0][-3:-1], self.stoch[1][-3:-1])
                                   
                signal_long  = long_breakout and near_recent and rsi_up and break_
                signal_short = short_reversal and near_recent and rsi_cross_recent and (self.bar_m1 < level)
                
            elif short_breakout or long_reversal :
                break_ = self.bar_m1[-1] < level
                rsi_cross_recent = self._crossover(self.stoch[0][-2:], self.stoch[1][-2:]) or \
                                   self._crossunder(self.stoch[0][-3:-1], self.stoch[1][-3:-1])
                signal_short = short_breakout and near_recent and rsi_dn and break_
                signal_long  = long_reversal and near_recent and rsi_cross_recent and (self.bar_m1[-1] > level)
                
            if signal_long :
                # TODO : Limit Buy
                self.order = {'entry' : self.bar_m1.Close(-1), 
                              'side' : 'buy',
                              'exit_type' : 'donchian',
                              'sl' : self.donchian[1][-1],
                              'tp' : target
                              }
                
            elif signal_short :
                # TODO : Limit Short
                self.order = {'entry' : self.bar_m1.Close(-1), 
                              'side'  : 'sell',
                              'exit_type' : 'donchian',
                              'sl' : self.donchian[0][-1],
                              'tp' : target
                              }
        
        
    def DownloadData(self) :
        API_KEY = "VI6KWvmzTp5sDsDUfwZbJapZHoWOSFbb"
        
        multiplier = 1
        timespan   = 'minute'
        
        end   = datetime.datetime.now().date()
        start = end - datetime.timedelta(days=60)
        
        url = f'https://api.polygon.io/v2/aggs/ticker/{self.ticker}/range/{multiplier}/{timespan}/{start}/{end}'
        params = {'adjusted' : False,
                  'sort'     : 'asc',
                  'limit'    : 50000,
                  'apiKey'   : API_KEY}
        
        match self.datafeeder :
            case DATAFEEDER.WEBSOCKET :
                params = {'url' : url,
                        'params' : params}
                
                r = requests.post('http://34.61.153.252:8111/api', json=params)

                if r.ok :
                    s = r.json()
                    if 'results' in s['received_data'] :
                        return s['received_data']['results']
            
            case DATAFEEDER.REDIS :
                r = requests.get(url=url, params=params)
                if r.ok :
                    s = r.json()
                    if 'results' in s :
                        return s['results']
        
    @staticmethod
    def _crossover(a, b) :
        return (a[-2]<b[-2]) and (a[-1]>b[-1])
    
    @staticmethod
    def _crossunder(a, b) :
        return (a[-2]>b[-2]) and (a[-1]<b[-1])
    
    def _in_region(self, top, bot) :
        return (self.bar_m1.Low(-1) < top) and (self.bar_m1.High(-1) > bot)
    
    def add_level(self, levels) :
        ids = [x['level'] for x in self.levels]
        for level in levels :
            if (level['symbol'] != self.ticker) or (level['id'] in ids)  :
                continue
            
            self.levels.append(level)
    
    def delete_level(self, level_id) :
        for i in range(len(self.levels)) :
            if self.levels[i]['id'] == level_id :
                del self.levels[i]
                return

    def get_level(self) :
        return self.levels
    
    def clear_level(self) :
        self.levels = []

    def reset_daily_level(self) :
        time_reset = datetime.datetime.now(tz=TIMEZONE_NY).replace(hour=16, minute=0, second=0, microsecond=0)

        for i in range(len(self.levels)-1, -1, -1) :
            time_level = datetime.datetime.fromisoformat(self.levels[i]['time']).replace(tzinfo=TIMEZONE_NY)
            if time_level < time_reset :
                print('delete, ', time_level)
                del self.levels[i]

if __name__ == '__main__' :
    EA = TestEA('SPY')
    asyncio.run(EA.AsyncRun(DATAFEEDER.REDIS))
    
