import os
import math
import datetime
import requests
from expadvlib.const import TIMEZONE_NY

API_KEY_STOCKS  = os.getenv("POLYGON_API_STOCKS")
API_KEY_OPTIONS = os.getenv("POLYGON_API_OPTIONS")

def get_current_option_itm(ticker, price, spread_offset = 5) :
    url    = f'https://api.polygon.io/v3/snapshot/options/{ticker}'
    params = {'apiKey'   : API_KEY_OPTIONS,
              'limit' : 250,
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

    call_symbols = [(x['details']['strike_price'], x['details']['ticker'], x['last_quote']['midpoint'], x['last_quote']['bid'], x['last_quote']['ask']) for x in s if x['details']['contract_type'] == 'call']
    put_symbols = [(x['details']['strike_price'], x['details']['ticker'], x['last_quote']['midpoint'], x['last_quote']['bid'], x['last_quote']['ask']) for x in s if x['details']['contract_type'] == 'put']
    
    nearest_call = sorted([(price - x[0], x[1], x[2], x[3], x[4]) for x in call_symbols if price-x[0]>0])[0][1:]
    nearest_put  = sorted([(x[0] - price, x[1], x[2], x[3], x[4]) for x in put_symbols if x[0]-price>0])[0][1:]

    spread_second_leg_call = sorted([(price - x[0] + spread_offset, x[1], x[2], x[3], x[4]) for x in call_symbols if (price - x[0] + spread_offset)>0])[0][1:]
    spread_second_leg_put  = sorted([(price - x[0] - spread_offset, x[1], x[2], x[3], x[4]) for x in put_symbols if (price - x[0] - spread_offset)>0])[0][1:]

    return {'status' : 'ok',
            'call' : {'symbol': nearest_call[0][2:],
                      'mid': nearest_call[1], 
                      'bid': nearest_call[2],
                      'ask': nearest_call[3]},
            'put' : {'symbol': nearest_put[0][2:],
                     'mid': nearest_put[1],
                     'bid': nearest_put[2],
                     'ask': nearest_put[3]},
            'spread_second_leg_call' : {'symbol': spread_second_leg_call[0][2:],
                                        'mid': spread_second_leg_call[1],
                                        'bid': spread_second_leg_call[2],
                                        'ask': spread_second_leg_call[3]},
            'spread_second_leg_put'  : {'symbol': spread_second_leg_put[0][2:],
                                        'mid': spread_second_leg_put[1],
                                        'bid': spread_second_leg_put[2],
                                        'ask': spread_second_leg_put[3]},
            }