import numpy as np
from enum import Enum
from const import TIMEFRAME, MODE_MA

# class TIMEFRAME(Enum) :
#     M1  = 1
#     M2  = 2
#     M5  = 5
#     M10 = 10
#     M15 = 15
#     M30 = 30
#     H1  = 60

# class MODE_MA(Enum) :
#     SMA = 0
#     EMA = 1
#     WMA = 2
#     RMA = 3

class BaseIndicator :
    def __init__(self) :
        self._values = np.array([], dtype=float)
        self._as_series = False

    def ArraySetAsSeries(self, flag:bool) :
        self._as_series = bool(flag)
    
    def __getitem__(self, key) :
        if self._values.ndim == 1 :
            if self._as_series :
                return self._values[::-1][key]
            return self._values[key]
        
        if self._as_series :
            if isinstance(key, int) :
                return self._values[key, ::-1]
            if isinstance(key, slice) :
                return self._values[:, ::-1][:, key]
            if isinstance(key, tuple) :
                if isinstance(key[0], slice) :
                    return self._values[key[0], ::-1][:, key[1]]
                if isinstance(key[0], int) :
                    return self._values[key[0], ::-1][key[1]]
        
        if isinstance(key, (int, tuple)) :
            return self._values[key]
        if isinstance(key, slice) :
            return self._values[:, key]
    
    def __len__(self) :
        if self._values.ndim==1 :
            return len(self._values)
        return self._values.shape[1]

# class AggregateBar :
#     def __init__(self, timeframe : TIMEFRAME, keys = ['t', 'o', 'h', 'l', 'c', 'v']) :
#         self._timeframe = 60*timeframe.value
#         self._Time   = np.array([], dtype=int)
#         self._Open   = np.array([], dtype=float)
#         self._High   = np.array([], dtype=float)
#         self._Low    = np.array([], dtype=float)
#         self._Close  = np.array([], dtype=float)
#         self._Volume = np.array([], dtype=float)
#         self._rates  = 0
#         self._keys   = keys
#         self._as_series = False

#     def OnBar(self, bar) :
#         ftime = self._TimeFloor(bar[self._keys[0]]/1000)
#         if self._rates == 0 :
#             self._NewBar(ftime, bar)
#             return
        
#         if self._Time[-1] == np.int64(ftime) :
#             self._UpdateBar(bar)
#         else :
#             self._NewBar(ftime, bar)
    
#     def _TimeFloor(self, t) :
#         return np.int64(math.floor(t/self._timeframe)*self._timeframe)
    
#     def _NewBar(self, t, bar) :
#         self._Time   = np.append(self._Time, t)
#         self._Open   = np.append(self._Open, bar[self._keys[1]])
#         self._High   = np.append(self._High, bar[self._keys[2]])
#         self._Low    = np.append(self._Low, bar[self._keys[3]])
#         self._Close  = np.append(self._Close, bar[self._keys[4]])
#         self._Volume = np.append(self._Volume, bar[self._keys[5]])
#         self._rates += 1
        
#     def _UpdateBar(self, bar) :
#         if self._High[-1] < bar[self._keys[2]] :
#             self._High[-1] = bar[self._keys[2]]
#         if self._Low[-1] > bar[self._keys[3]] :
#             self._Low[-1] = bar[self._keys[3]]
#         self._Close[-1] = bar[self._keys[4]]
#         self._Volume[-1] += bar[self._keys[5]]

#     def ArraySetAsSeries(self, flag:bool) :
#         self._as_series = True
    
#     def Open(self, key) :
#         if self._as_series :
#             return self._Open[::-1][key]
#         return self._Open[key]
        
#     def High(self, key) :
#         if self._as_series :
#             return self._High[::-1][key]
#         return self._High[key]
            
#     def Low(self, key) :
#         if self._as_series :
#             return self._Low[::-1][key]
#         return self._Low[key]
    
#     def Close(self, key) :
#         if self._as_series :
#             return self._Close[::-1][key]
#         return self._Close[key]

#     def Volume(self, key) :
#         if self._as_series :
#             return self._Volume[::-1][key]
#         return self._Volume[key]

#     def Nrates(self) :
#         return self._rates

#     def GetBar(self, key) :
#         if self._as_series :
#             return {'Time': self._Time[::-1][key],
#                     'Open' : self._Open[::-1][key],
#                     'High' : self._High[::-1][key],
#                     'Low' : self._Low[::-1][key],
#                     'Close' : self._Close[::-1][key],
#                     'Volume' : self._Volume[::-1][key]}
#         return {'Time': self._Time[key],
#                 'Open' : self._Open[key],
#                 'High' : self._High[key],
#                 'Low' : self._Low[key],
#                 'Close' : self._Close[key],
#                 'Volume' : self._Volume[key]}

class MovingAverage(BaseIndicator) :
    def __init__(self, period : int, 
                 mode_ma : MODE_MA) :
        super().__init__()
        self._period = period
        self._mode   = mode_ma
        
        match self._mode :
            case MODE_MA.EMA :
                self._factor = 2.0/(1.0 + self._period)
            case MODE_MA.WMA :
                self._weight = np.arange(1, period+1)
                self._factor = np.sum(self._weight)
            
    def OnCalculate(self, price) :    
        if len(self) <= 0 :
            self._values = np.full(len(price), np.nan)
            if (self._mode in (MODE_MA.SMA, MODE_MA.WMA)) :
                start = self._period-1
            elif (self._mode in (MODE_MA.EMA, MODE_MA.RMA)) :
                self._values[0] = price[0]
                start = 1
        else :
            if len(self) > len(price) :
                return
            start = len(self)
            if len(self) < len(price) :
                self._values = np.hstack([self._values, np.full(len(price)-len(self._values), np.nan)])
            if (start < self._period-1) and (self._mode in (MODE_MA.SMA, MODE_MA.WMA)) :
                start = self._period-1
        
        match self._mode :
            case MODE_MA.SMA :
                for i in range(start, len(price)) :
                    self._values[i] = np.mean(price[i-self._period+1:i+1])
            case MODE_MA.EMA :
                for i in range(start, len(price)) :
                    self._values[i] = self._factor*price[i] + (1-self._factor)*self._values[i-1]
            case MODE_MA.WMA :
                for i in range(start, len(price)) :
                    self._values[i] = np.sum(self._weight*price[i-self._period+1:i+1])/self._factor
            case MODE_MA.RMA :
                for i in range(start, len(price)) :
                    self._values[i] = ((self._period-1)*self._values[i-1] + price[i])/self._period

class RSI(BaseIndicator) :
    def __init__(self, period : int) :
        super().__init__()
        self._period = period
        self._buffer_gain = np.array([])
        self._buffer_loss = np.array([])
        
    def OnCalculate(self, price) :
        if len(self) <= 0 :
            self._values      = np.full(len(price), np.nan)
            self._buffer_gain = np.full(len(price), np.nan)
            self._buffer_loss = np.full(len(price), np.nan)
            self._buffer_gain[0] = 0
            self._buffer_loss[0] = 0
            start = 1
        else :
            if len(self) > len(price) :
                return
            
            start = len(self)
            if len(self) < len(price) :
                self._buffer_gain = np.hstack([self._buffer_gain, np.full(len(price)-len(self), np.nan)])
                self._buffer_loss = np.hstack([self._buffer_loss, np.full(len(price)-len(self), np.nan)])
                self._values      = np.hstack([self._values, np.full(len(price)-len(self), np.nan)])
        
        for i in range(start, len(price)) :
            self._UpdateRMA(i, price[i]-price[i-1])
            self._values[i] = self._buffer_gain[i]/(self._buffer_gain[i] - self._buffer_loss[i])
    
    def _UpdateRMA(self, i, dx) :
        if dx>0 :
            self._buffer_gain[i] = (dx + (self._period-1)*self._buffer_gain[i-1])/self._period
            self._buffer_loss[i] = (self._period-1)*self._buffer_loss[i-1]/self._period
        elif dx<0 :
            self._buffer_gain[i] = (self._period-1)*self._buffer_gain[i-1]/self._period
            self._buffer_loss[i] = (dx + (self._period-1)*self._buffer_loss[i-1])/self._period
        else :
            self._buffer_gain[i] = (self._period-1)*self._buffer_gain[i-1]/self._period
            self._buffer_loss[i] = (self._period-1)*self._buffer_loss[i-1]/self._period

class PriceChannel(BaseIndicator) :
    '''
    price_channel[0] = upper band
    price_channel[1] = lower band
    '''
    def __init__(self, period : int) :
        super().__init__()
        self._period = period
        
    def OnCalculate(self, high, low) :
        if len(self) <= 0 :
            self._values = np.full((2, len(high)), np.nan)
            start = self._period-1
        else :
            if len(self) > len(high) :
                return
            
            start = len(self)
            if len(self) < len(high) :
                self._values = np.hstack([self._values, np.full((2, len(high)-len(self)), np.nan)])
            if (start < self._period-1) :
                start = self._period-1
                
        for i in range(start, len(high)) :
            self._values[0, i] = np.max(high[i-self._period+1:i+1])
            self._values[1, i] = np.min(low[i-self._period+1:i+1])

class Stochastic(BaseIndicator) :
    '''
    stoch[0] = stoch_k
    stoch[1] = stoch_d
    '''
    def __init__(self, 
                 period_k  : int,
                 period_d  : int,
                 smoothing : int) :
        super().__init__()
        self._period_k  = period_k
        self._period_d  = period_d
        self._smoothing = smoothing
        
    def OnCalculate(self, high, low, close) :
        if len(self) <= 0 :
            self._stoch   = np.full(len(close), np.nan)
            self._channel = np.full((2, len(close)), np.nan)
            self._values  = np.full((2, len(close)), np.nan)
            start = 1
            #print(len(self._stoch), self._channel.shape, self._values.shape)
        else :
            if len(self) > len(close) :
                return
            start = len(self)
            if len(self) < len(close) :
                self._stoch   = np.hstack([self._stoch, np.full(len(close)-len(self), np.nan)])
                self._channel = np.hstack([self._channel, np.full((2, len(close)-len(self)), np.nan)])
                self._values  = np.hstack([self._values, np.full((2, len(close)-len(self)), np.nan)])
                #print(len(self._stoch), self._channel.shape, self._values.shape)
        
        for i in range(start, len(high)) :
            self._CalculatePriceChannel(i, high, low)
            self._stoch[i]     = (close[i] - self._channel[1, i])/(self._channel[0, i] - self._channel[1, i])
            self._values[0, i] = self._CalculateSMA(i, self._stoch, self._smoothing)
            self._values[1, i] = self._CalculateSMA(i, self._values[0], self._period_d)

    def _CalculatePriceChannel(self, i, high, low) :
        if i<self._period_k :
            return
        self._channel[0, i] = np.max(high[i-self._period_k+1:i+1])
        self._channel[1, i] = np.min(low[i-self._period_k+1:i+1])
    
    def _CalculateSMA(self, i, price, period) :
        return np.mean(price[i-period+1:i+1])

class ATR(BaseIndicator) :
    def __init__(self, period:int) :
        super().__init__()
        self._period = period

    def OnCalculate(self, high, low, close) :
        if len(self) <= 0 :
            self._tr     = np.full(len(close), np.nan)
            self._values = np.full(len(close), np.nan)
            self._values[0] = high[0]-low[0]
            start = 1
        else :
            if len(self) > len(close) :
                return
            
            start = len(self)
            if len(self) < len(close) :
                self._tr     = np.hstack([self._tr, np.full(len(close)-len(self), np.nan)])
                self._values = np.hstack([self._values, np.full(len(close)-len(self), np.nan)])

        for i in range(start, len(close)) :
            if np.isnan(self._values[i-1]) :
                self._values[i-1] = self._tr[i-1]
            
            self._tr[i] = max([high[i]-low[i], abs(low[i]-close[i-1]), abs(high[i]-close[i-1])])
            self._values[i] = (self._tr[i] + (self._period-1)*self._values[i-1])/self._period

class ChandelierExit(BaseIndicator) :
    '''
    onCalculate(high, low, close)
    chandelier[0] = Long Exit
    chandelier[1] = Short Exit
    '''
    def __init__(self, range_period : int = 22, atr_period : int = 22, multiple : float = 3.0) :
        super().__init__()
        self._range_period = range_period
        self._atr_period   = atr_period
        self._multiple     = multiple
        self._max_period = max(range_period, atr_period)
        
    def OnCalculate(self, high, low, close) :
        if len(self) <= 0 :
            self._upperband = np.full(len(close), np.nan)
            self._lowerband = np.full(len(close), np.nan)
            self._tr        = np.full(len(close), np.nan)
            self._atr       = np.full(len(close), np.nan)
            
            self._values = np.full((2, len(high)), np.nan)
            start = self._max_period-1
        else :
            if len(self) > len(high) :
                return
            
            start = len(self)
            if len(self) < len(high) :
                self._upperband = np.hstack([self._upperband, np.full(len(close)-len(self), np.nan)])
                self._lowerband = np.hstack([self._lowerband, np.full(len(close)-len(self), np.nan)])
                self._tr        = np.hstack([self._tr, np.full(len(close)-len(self), np.nan)])
                self._atr       = np.hstack([self._atr, np.full(len(close)-len(self), np.nan)])
                self._values = np.hstack([self._values, np.full((2, len(close)-len(self)), np.nan)])
            
            if (start < self._max_period-1) :
                start = self._max_period-1
        
        for i in range(start, len(close)) :
            # ATR
            if np.isnan(self._atr[i-1]) :
                self._atr[i-1] = self._tr[i-1]
            self._tr[i]  = max([high[i]-low[i], abs(low[i]-close[i-1]), abs(high[i]-close[i-1])])
            self._atr[i] = (self._tr[i] + (self._atr_period-1)*self._atr[i-1])/self._atr_period

            # Price Channel
            self._upperband[i] = np.max(high[i-self._range_period+1:i+1])
            self._lowerband[i] = np.min(low[i-self._range_period+1:i+1])

            # Chandelier Exit
            self._values[0, i] = self._upperband[i] - self._multiple*self._atr[i]
            self._values[1, i] = self._lowerband[i] + self._multiple*self._atr[i]

            if close[i-1] > self._values[0, i] :
                self._values[0, i] = max(self._values[0, i], self._values[0, i-1])
            if close[i-1] < self._values[1, i] :
                self._values[1, i] = min(self._values[1, i], self._values[1, i-1])