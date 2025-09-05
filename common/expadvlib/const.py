from enum import Enum
from zoneinfo import ZoneInfo

TIMEZONE_NY = ZoneInfo('America/New_York')

class TIMEFRAME(Enum) :
    M1  = 1
    M2  = 2
    M5  = 5
    M10 = 10
    M15 = 15
    M30 = 30
    H1  = 60

class MODE_MA(Enum) :
    SMA = 0
    EMA = 1
    WMA = 2
    RMA = 3

class DATAFEEDER(Enum) :
    WEBSOCKET = 0
    REDIS     = 1