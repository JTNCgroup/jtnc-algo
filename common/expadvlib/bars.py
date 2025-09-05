import time
import math
import datetime
import asyncio

from zoneinfo import ZoneInfo
import numpy as np

from const import TIMEFRAME, TIMEZONE_NY
from functions import TimeFloor
from enum import Enum

class BaseCandle :
    def __init__(self, keys = ['t', 'o', 'h', 'l', 'c', 'v']) :
        self._Time   = np.array([], dtype=int)
        self._Open   = np.array([], dtype=float)
        self._High   = np.array([], dtype=float)
        self._Low    = np.array([], dtype=float)
        self._Close  = np.array([], dtype=float)
        self._Volume = np.array([], dtype=float)
        self._rates  = 0
        self._keys   = keys
        self._as_series = False
    
    def _NewBar(self, t, bar) :
        self._Time   = np.append(self._Time, t)
        self._Open   = np.append(self._Open, bar[self._keys[1]])
        self._High   = np.append(self._High, bar[self._keys[2]])
        self._Low    = np.append(self._Low, bar[self._keys[3]])
        self._Close  = np.append(self._Close, bar[self._keys[4]])
        self._Volume = np.append(self._Volume, bar[self._keys[5]])
        self._rates += 1

    def _UpdateBar(self, bar) :
        if self._High[-1] < bar[self._keys[2]] :
            self._High[-1] = bar[self._keys[2]]
        if self._Low[-1] > bar[self._keys[3]] :
            self._Low[-1] = bar[self._keys[3]]
        self._Close[-1] = bar[self._keys[4]]
        self._Volume[-1] += bar[self._keys[5]]

    def _ReplaceBar(self, i, bar) :
        self._Open[i]   = bar[self._keys[1]]
        self._High[i]   = bar[self._keys[2]]
        self._Low[i]    = bar[self._keys[3]]
        self._Close[i]  = bar[self._keys[4]]
        self._Volume[i] = bar[self._keys[5]]
    
    def ArraySetAsSeries(self, flag:bool) :
        self._as_series = True

    def Time(self, key=None) :
        if key is None :
            key = slice(None)
        if self._as_series :
            return self._Time[::-1][key]
        return self._Time[key]
        
    def Open(self, key=None) :
        if key is None :
            key = slice(None)
        if self._as_series :
            return self._Open[::-1][key]
        return self._Open[key]
        
    def High(self, key=None) :
        if key is None :
            key = slice(None)
        if self._as_series :
            return self._High[::-1][key]
        return self._High[key]
    
    def Low(self, key=None) :
        if key is None :
            key = slice(None)
        if self._as_series :
            return self._Low[::-1][key]
        return self._Low[key]
    
    def Close(self, key=None) :
        if key is None :
            key = slice(None)
        if self._as_series :
            return self._Close[::-1][key]
        return self._Close[key]

    def Volume(self, key=None) :
        if key is None :
            key = slice(None)
        if self._as_series :
            return self._Volume[::-1][key]
        return self._Volume[key]

    def Nrates(self) :
        return self._rates

    def GetBar(self, key=None) :
        if key is None :
            key = slice(None)
        if self._as_series :
            return {'Time': self._Time[::-1][key],
                    'Open' : self._Open[::-1][key],
                    'High' : self._High[::-1][key],
                    'Low' : self._Low[::-1][key],
                    'Close' : self._Close[::-1][key],
                    'Volume' : self._Volume[::-1][key]}
        return {'Time': self._Time[key],
                'Open' : self._Open[key],
                'High' : self._High[key],
                'Low' : self._Low[key],
                'Close' : self._Close[key],
                'Volume' : self._Volume[key]}

class CandleSticks(BaseCandle) :
    def __init__(self, keys = ['t', 'o', 'h', 'l', 'c', 'v']) :
        super().__init__(keys)

    def __sortbytime(self, x) :
        return x[self._keys[0]]
        
    def OnBar(self, bars) :
        if isinstance(bars, dict) :
            bars = [bars, ]

        bars.sort(key=self.__sortbytime)
        for bar in bars :
            t = bar[self._keys[0]]/1000
            i = self._FindIndex(t)
            if i is None :
                self._NewBar(t, bar)
            else :
                self._ReplaceBar(i, bar)

    def _FindIndex(self, t) :
        for i in range(self._rates-1) :
            if self._Time[self._rates-i-1] == t :
                return self._rates-i-1
        return None

class AggregateBar(BaseCandle) :
    def __init__(self, timeframe : TIMEFRAME, keys = ['t', 'o', 'h', 'l', 'c', 'v']) :
        super().__init__(keys)
        self._timeframe = 60*timeframe.value

    def OnBar(self, bar) :
        #ftime = self._TimeFloor(bar[self._keys[0]]/1000)
        ftime = TimeFloor(bar[self._keys[0]]/1000, self._timeframe, True)
        if self._rates == 0 :
            self._NewBar(ftime, bar)
            return
        
        if self._Time[-1] == np.int64(ftime) :
            self._UpdateBar(bar)
        else :
            self._NewBar(ftime, bar)
    
    # def _TimeFloor(self, t) :
    #     return np.int64(math.floor(t/self._timeframe)*self._timeframe)

# class BaseEA :
#     MODE = Enum('MODE', [('LIVE', 0), ('TEST',1)])
#     def __init__(self, polygon_apikey=None) :
#         self.__timeframe = 60
#         self.__polygon_apikey = polygon_apikey
#         self.__mode = None
        
#     def Run(self) :
#         self.__mode = BaseEA.MODE.LIVE
#         self.OnStart()
#         self._LoopLive()

#     def AsyncRun(self) :
#         self.__mode = BaseEA.MODE.LIVE
#         self.OnStart()
#         task = asyncio.create_task(self._AsyncLoopLive())
#         task
        
#     def Simulate(self, dfs, keys=['t', 'o', 'h', 'l', 'c', 'v']) :
#         '''
#         dfs = dictionary of data {"ticker" : DataFrame, ...}
#         '''
#         self.__mode = self.MODE.TEST
#         self._PrepareData(dfs, keys)
#         self.OnStart()
#         self._LoopTest()
    
#     def OnStart(self) :
#         pass
    
#     def OnUpdate(self) :
#         pass
    
#     def OnBar(self) :
#         pass

#     def _PrepareData(self, dfs, keys=['t', 'o', 'h', 'l', 'c', 'v']) :
#         self.__data = dict()
#         for ticker in dfs :
#             df = dfs[ticker].copy()
#             df = df.rename(columns={keys[0]:'t', keys[1]:'o', keys[2]:'h', keys[3]:'l', keys[4]:'c', keys[5]:'v'})
#             df = df[['t', 'o', 'h', 'l', 'c', 'v']]
#             df['t'] = df['t'].apply(lambda x: np.int64(1000*x.timestamp()))
#             self.__data[ticker] = df.to_dict('records')

#     def _LoopTest(self) :
#         ticker = list(self.__data.keys())[0]
#         n = len(self.__data[ticker])
#         for self.__i in range(n) :
#             self.OnUpdate()
#             self.OnBar()
#         del self.__i, self.__data
        
#     def _LoopLive(self) :
#         prev_time = int(TimeFloor(time.time(), self.__timeframe, True))
#         while True :
#             self.__curr_time = int(TimeFloor(time.time(), self.__timeframe, True))
#             if self.__curr_time != prev_time :
#                 self.OnUpdate()
#                 self.OnBar()
#                 prev_time = self.__curr_time
        
#             t_sleep = max(0.01, math.floor(99*(self.__timeframe - (time.time() - self.__curr_time)))/100)
#             time.sleep(t_sleep)
    
#     async def _AsyncLoopLive(self) :
#         prev_time = int(TimeFloor(time.time(), self.__timeframe, True))
#         print(f"Start Time : {prev_time}")
#         #for _ in range(10) :
#         while True :
#             self.__curr_time = int(TimeFloor(time.time(), self.__timeframe, True))
#             if self.__curr_time != prev_time :
#                 self.OnUpdate()
#                 self.OnBar()
#                 print(f"Run : {prev_time}\t{self.__curr_time}")
#                 prev_time = self.__curr_time
        
#             t_sleep = max(0.01, math.floor(99*(self.__timeframe - (time.time() - self.__curr_time)))/100)
#             print(f"Time Sleep : {t_sleep}")
#             await asyncio.sleep(t_sleep)
    
#     def GetData(self, ticker) :
#         #if self.__mode == self.MODE.LIVE :
#         #    return GetPolygonStockCandle(ticker, self.__curr_time-3*self.__timeframe, self.__curr_time+2*self.__timeframe, api_key=self.__polygon_apikey)
#         if self.__mode == self.MODE.TEST :
#             return self.__data[ticker][self.__i]