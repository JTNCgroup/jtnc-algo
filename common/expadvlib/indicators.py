import numpy as np
from enum import Enum
from const import TIMEFRAME, MODE_MA

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
        
        eps = np.finfo(float).eps
        for i in range(start, len(high)) :
            self._CalculatePriceChannel(i, high, low)
            denom = (self._channel[0, i] - self._channel[1, i])
            
            if denom > eps :
                self._stoch[i] = (close[i] - self._channel[1, i])/denom
            else :
                self._stoch[i] = 0.5
            
            self._values[0, i] = self._CalculateSMA(i, self._stoch, self._smoothing)
            self._values[1, i] = self._CalculateSMA(i, self._values[0], self._period_d)

    def _CalculatePriceChannel(self, i, high, low) :
        if i<self._period_k :
            return
        self._channel[0, i] = np.nanmax(high[i-self._period_k+1:i+1])
        self._channel[1, i] = np.nanmin(low[i-self._period_k+1:i+1])
    
    def _CalculateSMA(self, i, price, period) :
        if all(np.isnan(price[i-period+1:i+1])) :
            return np.nan
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

class KernelRegression(BaseIndicator) :
    def __init__(self, h=8.0, r=8.0, n=25) :
        '''
        h = band-width (kernel size)
        r = smoothness
        n = size of kernel array
        '''
        
        super().__init__()
        self._period = n
        self._weight = self._gen_weight(h, r, n)
        
    def OnCalculate(self, price) :
        if len(self) <= 0 :
            self._values = np.full(len(price), np.nan)
            start = self._period-1
            
        else :
            if len(self) > len(price) :
                return
            start = len(self)
            if len(self) < len(price) :
                self._values = np.hstack([self._values, np.full(len(price)-len(self._values), np.nan)])
            if (start < self._period-1) :
                start = self._period-1
        
        for i in range(start, len(price)) :
            self._values[i] = np.sum(self._weight*price[i-self._period+1:i+1])

    def _gen_weight(self, h, r, n) :
        w = np.array([(1.0 + (i**2 / ((h**2)*2*r)))**(-r) for i in reversed(range(n))])
        w /= np.sum(w)
        return w
class JTNCZscoreVWAP(BaseIndicator) :
    def __init__(self, period=180) :
        super().__init__()
        self._period=period

    def OnCalculate(self, price, volume) :
        if len(self) <= 0 :
            self._pv     = price*volume
            self._devs   = np.full(len(price), np.nan)
            self._values = np.full(len(price), np.nan)
            start = self._period-1
            
        else :
            if len(self) > len(price) :
                return
                
            start = len(self)
            if (start < self._period-1) :
                start = self._period-1
                self._pv = price*volume
            
            if len(self) < len(price) :
                self._pv     = np.hstack([self._pv, np.full(len(price)-len(self._pv), np.nan)])
                self._devs   = np.hstack([self._devs, np.full(len(price)-len(self._devs), np.nan)])
                self._values = np.hstack([self._values, np.full(len(price)-len(self._values), np.nan)])
        
        for i in range(start, len(price)) :
            j = slice(i-self._period+1, i+1)
            self._pv[i] = price[i]*volume[i]
            mean = np.sum(self._pv[j])/np.sum(volume[j])
            self._devs[i] = price[i] - mean
            vwapsd = np.sqrt(np.mean(np.power(self._devs[j], 2)))
            
            if i>=2*self._period-2 :
                self._values[i] = self._devs[i]/vwapsd if vwapsd!= 0 else 0

class JTNCZscoreVWAPRangeV2(BaseIndicator) :
    '''
    OnCalculate(high, low, close, volume)
    Output
    0 : High
    1 : Low
    2 : Mid
    3 : QHi
    4 : QLo
    5 : Range
    6 : PRLOC
    '''
    
    def __init__(self, period=180, cross_ab=2.0, cross_be=-2.0) :
        super().__init__()
        self._cross_ab = cross_ab
        self._cross_be = cross_be
        self._period = period

        self._zv = JTNCZscoreVWAP(self._period)

    def Reset(self) :
        self._zHi     = np.full(len(close), np.nan)
        self._zLo     = np.full(len(close), np.nan)
        self._zBar    = np.full(len(close), np.nan)
        self._c_above = np.full(len(close), False)
        self._c_below = np.full(len(close), False)
        self._fractalHi = np.zeros(len(close))
        self._fractalLo = np.zeros(len(close))
        self._price_low = np.zeros(len(close))
        self._price_high = np.zeros(len(close))
        
        self._values = np.full((7, len(close)), np.nan)
        
    def OnCalculate(self, high, low, close, volume) :
        self._zv.OnCalculate(close, volume)
        
        start = len(self)
        if len(self)<=0:
            self.Reset()
            self._values = np.full((7, len(close)), np.nan)
            start = 1

        if len(self) < len(close) :
            self._zHi    = np.hstack([self._zHi, np.full(len(close)-len(self._zHi), np.nan)])
            self._zLo    = np.hstack([self._zLo, np.full(len(close)-len(self._zLo), np.nan)])
            self._zBar   = np.hstack([self._zBar, np.full(len(close)-len(self._zBar), np.nan)])
            self._c_above = np.hstack([self._c_above, np.full(len(close)-len(self._c_above), False)])
            self._c_below = np.hstack([self._c_below, np.full(len(close)-len(self._c_below), False)])

            self._fractalHi  = np.hstack([self._fractalHi, np.full(len(close)-len(self._fractalHi), np.nan)])
            self._fractalLo  = np.hstack([self._fractalLo, np.full(len(close)-len(self._fractalLo), np.nan)])
            self._price_low  = np.hstack([self._price_low, np.full(len(close)-len(self._price_low), np.nan)])
            self._price_high = np.hstack([self._price_High, np.full(len(close)-len(self._price_high), np.nan)])
            
            self._values = np.hstack([self._values, np.full((7, len(close)-len(self)), np.nan)])

        
        for i in range(start, len(close)) :
            if (self._zv[i-1] is None) or (self._zv[i] is None) or np.isnan(self._zv[i-1]) or np.isnan(self._zv[i]) :
                continue

            self._zHi[i]  = self._zHi[i-1]
            self._zLo[i]  = self._zLo[i-1]
            self._zBar[i] = self._zBar[i-1]
            self._c_above[i] = self._c_above[i-1]
            self._c_below[i] = self._c_below[i-1]
            self._fractalHi[i] = self._fractalHi[i-1]
            self._fractalLo[i] = self._fractalLo[i-1]
            self._price_low[i] = self._price_low[i-1]
            self._price_high[i] = self._price_high[i-1]
            
            if ((self._zv[i-1] <= self._cross_ab) and (self._zv[i] > self._cross_ab)) or (self._c_above[i] and self._zv[i] > self._zHi[i]) :
                self._zHi[i] = self._zv[i]
            if ((self._zv[i-1] >= self._cross_be) and (self._zv[i] < self._cross_be)) or (self._c_below[i] and self._zv[i] < self._zLo[i]) :
                self._zLo[i] = self._zv[i]
            
            if (self._zv[i-1] <= self._cross_ab) and (self._zv[i] > self._cross_ab) :
                self._c_above[i] = True
            elif (self._zv[i] <= self._cross_ab) and not (self._c_above[i] and self._zv[i-2]<=self._cross_ab and self._zv[i-1]>self._cross_ab) :
                self._c_above[i] = False
            
            if (self._zv[i-1] >= self._cross_be) and (self._zv[i] < self._cross_be) :
                self._c_below[i] = True
            elif (self._zv[i] >= self._cross_be) and not (self._c_below[i] and self._zv[i-2]>=self._cross_be and self._zv[i-1]<self._cross_be) :
                self._c_below[i] = False
            
            if (self._zHi[i]!=0) and (self._zv[i-1]==self._zHi[i]) and (self._zv[i]<self._zHi[i]) and (high[i]>self._price_low[i]) :
                self._zHi[i] = self._zv[i-1]
                self._fractalHi[i] = high[i-1]
                self._zBar[i] = i
            
            if (self._zLo[i]!=0) and (self._zv[i-1]==self._zLo[i]) and (self._zv[i]>self._zLo[i]) and (low[i]<self._price_high[i]) :
                self._zLo[i] = self._zv[i-1]
                self._fractalLo[i] = low[i-1]
                self._zBar[i] = i

            self._price_high[i] = self._fractalHi[i] if self._fractalHi[i]!=0 else self._price_high[i]
            self._price_low[i]  = self._fractalLo[i] if self._fractalLo[i]!=0 else self._price_low[i]
        
            if (self._price_high[i]!=0) and (self._price_low[i]!=0) :
                self._values[0, i] = self._price_high[i]
                self._values[1, i] = self._price_low[i]
                self._values[2, i] = (self._price_high[i] + self._price_low[i])/2
                self._values[5, i] = self._price_high[i] - self._price_low[i]
                self._values[3, i] = self._price_high[i] - 0.25*self._values[5, i]
                self._values[4, i] = self._price_low[i]  + 0.25*self._values[5, i]

                hlc3 = (high[i] + low[i] + close[i])/3
                self._values[6, i] = 1 if (hlc3 > self._values[3][i]) else (-1 if hlc3 < self._values[4][i] else 0)

class JTNCMarketStateIndicator(BaseIndicator) :
    '''
    Output
    0 : High
    1 : QHi
    2 : QLo
    3 : Low
    4 : State
    5 : Uptrend Pullback
    6 : Downtrend Pullback
    7 : Uptrend Deterioration
    8 : Downtrend Deterioration
    '''
    def __init__(self, zv_periods=(10, 30, 60, 180)) :
        super().__init__()
        
        self._periods = tuple(sorted(zv_periods))
        self._zv = [JTNCZscoreVWAPRangeV2(period=i) for i in zv_periods]
        self._pr = [KernelRegression(h=20.0, r=8.0, n=25) for _ in range(len(zv_periods))]
        self._n  = len(zv_periods)
        
    def OnCalculate(self, open_, high, low, close, volume) :
        for i in range(len(self._zv)) :
            self._zv[i].OnCalculate(high, low, close, volume)
            self._pr[i].OnCalculate(self._zv[i][6, :])
        
        start = len(self)
        if len(self)<=0 :
            self._zvr    = [np.full(len(close), np.nan) for _ in range(self._n-1)]
            self._zvr3   = {x:np.full(len(close), np.nan) for x in ('Mid', 'QLo', 'QHi', 'PRLoc')}
            self._last_trend_dir = np.full(len(close), np.nan)
            self._values = np.full((9, len(close)), np.nan)
            start = 1

        if len(self) < len(close) :
            self._last_trend_dir = np.hstack([self._last_trend_dir, np.full((5, len(close)-len(self)), np.nan)])
            self._values = np.hstack([self._values, np.full((9, len(close)-len(self)), np.nan)])
            for i in range(len(self._zv)) :
                self._zvr[i] = np.hstack([self._zvr[i], np.full(len(close), np.nan)])
            for x in ('Mid', 'QLo', 'QHi', 'PRLoc') :
                self._zvr3[x] = np.hstack([self._zvr3[x], np.full(len(close), np.nan)])
            
        for i in range(start, len(close)) :
            
            nz_range  = [x[5][i] != 0 for x in self._zv]
            zv3_range = self._zv[3][5][i] if ((self._zv[self._n-1][0][i]!=0) and \
                                              (self._zv[self._n-1][1][i]!=0) and \
                                              (~np.isnan(self._zv[self._n-1][0][i])) and \
                                              (~np.isnan(self._zv[self._n-1][1][i]))) else 0
            nz_range[3] = int(zv3_range!=0)

            for j in range(self._n-1) :
                self._zvr[j][i]    = self._zv[j][2, i]*nz_range[j]
            
            self._zvr3['Mid'][i]   = self._zv[self._n-1][2, i]*nz_range[j]
            self._zvr3['QHi'][i]   = self._zv[self._n-1][3, i]*nz_range[j]
            self._zvr3['QLo'][i]   = self._zv[self._n-1][4, i]*nz_range[j]
            self._zvr3['PRLoc'][i] = self._zv[self._n-1][6, i]*nz_range[j]

            avg_mid  = np.mean([self._zvr[j][i] for j in range(self._n-1)], axis=0)
            hlc3     = (high[i] + low[i] + close[i])/3
            
            bias = 2*(hlc3 > avg_mid).astype(int) - 1

            self._last_trend_dir[i] = self._last_trend_dir[i-1]
            
            uptrend_base   = self._pr[self._n-1][i] > 0.5
            downtrend_base = self._pr[self._n-1][i] < -0.5
            
            zv3_prloc = self._zv[self._n-1][6, i]
            # if (zv3_prloc is None) or np.isnan(zv3_prloc) :
            #     continue
            
            if (zv3_prloc > 0) :
                self._values[0, i] = self._zv[self._n-1][0, i] #self._zvr3['High'][i]
            if (zv3_prloc >= 0) :
                self._values[1, i] = self._zvr3['QHi'][i]
            if (zv3_prloc <= 0) :
                self._values[2, i] = self._zvr3['QLo'][i]
            if (zv3_prloc < 0) :
                self._values[3, i] = self._zv[self._n-1][1, i] # self._zvr3['Low'][i]

            
            if np.isfinite(self._values[0, i]) and np.isfinite(self._values[1, i]) :
                self._values[4, i] = 1
            elif np.isfinite(self._values[1, i]) and np.isfinite(self._values[2, i]) :
                self._values[4, i] = 0
            elif np.isfinite(self._values[2, i]) and np.isfinite(self._values[3, i]) :
                self._values[4, i] = -1
            
            if (self._pr[3][i-1] <= 0.5 and self._pr[3][i]>0.5) :
                self._last_trend_dir[i] = 1
            elif (self._pr[3][i-1] >= -0.5 and self._pr[3][i]<-0.5) :
                self._last_trend_dir[i] = -1
            else :
                self._last_trend_dir[i] = self._last_trend_dir[i-1]
            
            self._values[5, i] = ((uptrend_base   or ((self._last_trend_dir[i]== 1) and not downtrend_base)) & (self._pr[2][i] <  1)) & (hlc3 > self._zvr3['QHi'][i])
            self._values[6, i] = ((downtrend_base or ((self._last_trend_dir[i]==-1) and not uptrend_base))   & (self._pr[2][i] > -1)) & (hlc3 < self._zvr3['QLo'][i])
            self._values[7, i] = uptrend_base   & (self._pr[0][i]< 1) & (self._pr[1][i]< 1) & (self._pr[2][i]< 1)
            self._values[8, i] = downtrend_base & (self._pr[0][i]>-1) & (self._pr[1][i]>-1) & (self._pr[3][i]>-1)

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