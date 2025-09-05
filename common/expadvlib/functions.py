import math
import datetime
import requests

from const import TIMEZONE_NY

def TimeFloor(t, timeframe, return_timestamp=False) :
    s = t
    if isinstance(s, (int, float)) :
        s = datetime.datetime.fromtimestamp(s, tz=TIMEZONE_NY)
    
    if s.tzinfo != TIMEZONE_NY :
        s = s.astimezone(TIMEZONE_NY)

    start = (s - datetime.timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
    dt = math.floor((s - start).total_seconds()/timeframe)*timeframe
    s = start + datetime.timedelta(seconds=dt)

    if return_timestamp :
        return s.timestamp()
    if isinstance(t, (int, float)) :
        return s
    return s.astimezone(t.tzinfo)

def GetPolygonStockCandle(ticker, start, end, multiplier=1, timespan='minute', adjust=False, sort='desc', limit=50000, api_key=None) :
    url    = f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start}/{end}'
    params = {'adjust' : adjust,
              'sort' : sort,
              'limit' : limit,
              'apiKey' : api_key}
    r = requests.get(url, params=params)
    if r.ok :
        res = r.json()
        if 'results' in res :
            res = res['results']
            return res