#senbit web api 访问和处理

import hmac
import time
import hashlib
import requests
from urllib.parse import quote_plus
from pprint import pprint as pp
import logging
from logging import exception, handlers

class Exchange_web_api(object):

    def __init__(self,site,key_common_access,key_common_secret,key_trade_access,key_trade_secret):
        #web-api的网址和KEY
        self.__site = site
        self.__key_common_access = key_common_access
        self.__key_common_secret = key_common_secret
        self.__key_trade_access = key_trade_access
        self.__key_trade_secret = key_trade_secret
        
        #这个web-api的get请求数量
        self.__get_count = 0
        #这个web-api的pos请求数量
        self.__post_count = 0
        #这个web-api的delete请求数量
        self.__delete_count = 0

        #本地与服务器时间差,用于矫正时间戳
        self.__timestamp_gap = 0

        self.__HEADERS = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'}

    #设置本地时间和服务器时间差
    def setTimestampGap(self, gap ):
        self.__timestamp_gap = gap
        return
    
    #获取与服务器相等的、可用的时间戳
    def get_time_str(self):
        return str(int(time.time()*1000 + self.__timestamp_gap ))

    def get_quote(self,_):
        return quote_plus(_)

    
    #通用的签名函数，签名需要按照字母顺序排列
    def get_sign_params(self,p_params,p_key):
        sorted_key_list = sorted(p_params)
        #print(sorted_key_list)
    
        sign_query = ''
        for v in sorted_key_list:
            if(p_params[v] is not None):
                if(sign_query == ''):
                    sign_query = ''.join([v,'=',str(p_params[v])])
                else:
                    sign_query = ''.join([sign_query,'&',v,'=',str(p_params[v])])
        
        print(sign_query)
        sign_result = hmac.new(bytes(p_key, 'utf-8'), bytes(sign_query, 'utf-8'), digestmod=hashlib.sha256).hexdigest()

        return sign_result

    #通用的签名函数，签名需要按照字母顺序排列
    def get_sign(self,time_str, path, method, market):
        sign_query = '_=%s&access=%s&method=%s&path=%s&symbol=%s'%(time_str, self.__key_common_access, method, self.get_quote(path), self.get_quote(market))
        print(sign_query)
        sign_result = hmac.new(bytes(self.__key_common_secret, 'utf-8'), bytes(sign_query, 'utf-8'), digestmod=hashlib.sha256).hexdigest()

        return sign_result

    #读取所有订单方法所需要的签名，注意参数要按照字母顺序排列好签名
    def get_sign_read_order(self,time_str,path,method,page,params):
        sign_query = '_=%s&access=%s&method=%s&path=%s&state=%s'%(time_str,self.__key_common_access,method, self.get_quote(path),params['state'])

        if page != '':
            sign_query ='_=%s&access=%s&method=%s&page=%s&path=%s&state=%s'%(time_str,self.__key_common_access,method,page,self.get_quote(path),params['state'])
            #sign_query = sign_query + '&page={}'.format(params['page'])

        if(params['symbol'] != ''):
            sign_query =  sign_query + '&symbol={}'.format(self.get_quote(params['symbol']))
        
        if(params['type'] != ''):
            sign_query =  sign_query + '&type={}'.format(params['type'])

        print(sign_query)


        sign_result = hmac.new(bytes(self.__key_common_secret, 'utf-8'), bytes(sign_query, 'utf-8'), digestmod=hashlib.sha256).hexdigest()

        return sign_result

    #从senbit读取已经在挂的订单，需要签名方法
    def call_api_get_read_orders(self,p_state,p_symbol,p_type,p_page):
        time_str = self.get_time_str()

        method = 'GET'
        path = '/api/x/v1/order/order'
        url = '%s%s'%(self.__site, path)

        sign = self.get_sign_read_order(time_str,path, method,p_page,{'state': p_state,'symbol': p_symbol,'type': p_type } )
        params = {
            '_': time_str,
            'access': self.__key_common_access,
            'sign': sign,
            'state': p_state,
            'symbol': p_symbol,
            'type': p_type,
            'page': p_page,

        }
        pp(params)

        _ = requests.get(url, params=params, headers=self.__HEADERS)
        ret = {
            "status_code": _.status_code,
            "json": _.json()
        }
        return ret

    
    #获取服务器的时间戳
    def call_api_timestamp(self):
        path = '/api/x/v1/common/timestamp'
        url = '%s%s'%(self.__site, path)


        _ = requests.get(url, headers=self.__HEADERS)
        ret = {
            "status_code": _.status_code,
            "json": _.json()
        }
        return ret

    
    #获取报价API
    def call_api_tickers(self,market):
        time_str = self.get_time_str()

        method = 'GET'
        path = '/api/x/v1/market/tickers'
        url = '%s%s'%(self.__site, path)

        sign_params = {
            '_': time_str,
            'access': self.__key_common_access,
            'symbol': self.get_quote(market),
            'method': method,
            'path': self.get_quote(path)
        }

        sign = self.get_sign_params(sign_params,self.__key_common_secret)
        params = {
            '_': time_str,
            'access': self.__key_common_access,
            'sign': sign,
            'symbol': market,
        }

        _ = requests.get(url, params=params, headers=self.__HEADERS)
        ret = {
            "status_code": _.status_code,
            "json": _.json()
        }
        return ret

    #挂单签名方法
    def get_sign_place_order(self,time_str, path, method):
        sign_query = '_=%s&access=%s&method=%s&path=%s'%(time_str, self.__key_trade_access, method, self.get_quote(path))
        sign_result = hmac.new(bytes(self.__key_trade_secret, 'utf-8'), bytes(sign_query, 'utf-8'), digestmod=hashlib.sha256).hexdigest()

        return sign_result

    #挂单方法API
    def call_api_place_order(self,symbol, _type, price, amount):
        time_str = self.get_time_str()

        method = 'POST'
        path = '/api/x/v1/order/order'
        url = '%s%s'%(self.__site, path)

        sign = self.get_sign_place_order(time_str, path, method)
        params = {
            '_': time_str,
            'access': self.__key_trade_access ,
            'sign': sign,
        }
        post_data = {
            'symbol': symbol,
            'type': _type,
            'price': price,
            'amount': amount,
        }

        _ = requests.request(method, url, params=params, data=post_data, headers=self.__HEADERS)
        try:
            ret = {
            "status_code": _.status_code,
            "json": _.json()
            }

        except:
            ret = {
            "status_code": "701",
            "json": ""
            }

        
        return ret

    #撤单签名方法
    def get_sign_cancel_order(self,time_str, path, method, market):
        sign_query = '_=%s&access=%s&method=%s&path=%s&symbol=%s'%(time_str,self.__key_trade_access, method, self.get_quote(path), self.get_quote(market))
        sign_result = hmac.new(bytes(self.__key_trade_secret, 'utf-8'), bytes(sign_query, 'utf-8'), digestmod=hashlib.sha256).hexdigest()

        return sign_result

    #撤单的方法
    def call_api_cancel_order(self,symbol, orderid):
        time_str = self.get_time_str()

        method = 'DELETE'
        path = '/api/x/v1/order/order/{}'.format(orderid)
        url = '%s%s'%(self.__site, path)

        sign = self.get_sign_cancel_order(time_str, path, method, symbol)
        params = {
            '_': time_str,
            'access': self.__key_trade_access,
            'sign': sign,
            'symbol': symbol,
        }

        _ = requests.request(method, url, params=params, headers=self.__HEADERS)
        ret = {
            "status_code": _.status_code,
        }
        return ret




    
        

    #获取kline
    def call_api_get_market_kline(self,p_symbol,p_period,p_from=None,p_direction=None,p_max=None):
        
        time_str = self.get_time_str()

        method = 'GET'
        path = '/api/x/v1/market/kline'
        url = '%s%s'%(self.__site, path)

        sign_params = {
            '_': time_str,
            'access': self.__key_common_access,
            'symbol': self.get_quote(p_symbol),
            'period': p_period,
            'from':p_from,
            'direction':p_direction,
            'max':p_max,
            'method':method,
            'path':self.get_quote(path)
        }
        sign = self.get_sign_params(sign_params,self.__key_common_secret)

        request_params = {
            '_': time_str,
            'access': self.__key_common_access,
            'sign':sign,
            'symbol': p_symbol,
            'period': p_period,
        }
        if(p_from is not None):
            request_params['from'] = p_from
        if(p_direction is not None):
            request_params['direction'] = p_direction
        if(p_max is not None):
            request_params['max'] = p_max

        try:
            _ = requests.get(url, params=request_params, headers=self.__HEADERS)
            print(_.url)
            ret = {
            "status_code": _.status_code,
            "json": _.json()
            }

        except:
            ret = {
            "status_code": "701",
            "json": ""
            }

        return ret


    #获取市场深度的API
    def call_api_get_market_depth(self,market):
        time_str = self.get_time_str()

        method = 'GET'
        path = '/api/x/v1/market/depth'
        url = '%s%s'%(self.__site, path)

        sign = self.get_sign(time_str, path, method, market)
        params = {
            '_': time_str,
            'access': self.__key_common_access,
            'sign': sign,
            'symbol': market,
        }
        
        try:
            _ = requests.get(url, params=params, headers=self.__HEADERS)
            ret = {
            "status_code": _.status_code,
            "json": _.json()
            }

        except:
            ret = {
            "status_code": "701",
            "json": ""
            }

        return ret

    #获取余额方法的签名
    def get_sign_balace(self,time_str, path, method):
        sign_query = '_=%s&access=%s&method=%s&path=%s'%(time_str, self.__key_common_access , method, self.get_quote(path))
        sign_result = hmac.new(bytes(self.__key_common_secret, 'utf-8'), bytes(sign_query, 'utf-8'), digestmod=hashlib.sha256).hexdigest()

        return sign_result

    #获取余额的API
    def call_api_get_acount_balance(self,currency):
        time_str = self.get_time_str()

        method = 'GET'
        path = '/api/x/v1/account/balance/{}'.format(currency)
        url = '%s%s'%(self.__site, path)

        sign = self.get_sign_balace(time_str, path, method)
        params = {
            '_': time_str,
            'access': self.__key_common_access,
            'sign': sign,
            #'currency': currency,
        }

        try:
            _ = requests.get(url, params=params, headers=self.__HEADERS)
            ret = {
            "status_code": _.status_code,
            "json": _.json()
            }

        except:
            ret = {
            "status_code": "701",
            "json": ""
            }
            
        return ret


#用于 class test
def main_run():
    
    #从本地数据库中读取api-key，也可以直接输入-start
    from senbit import senbit_db_api
 
    conn,c = senbit_db_api.open_sqlite_db(senbit_db_api.get_db_fullpath("senbit/db.sqlite3"))

    pSITE = senbit_db_api.get_value_by_Key(c,'SITE')
    print(pSITE)
    pKEY_COMMON_ACCESS = senbit_db_api.get_value_by_Key(c,'KEY_COMMON_ACCESS')
    pKEY_COMMON_SECRET= senbit_db_api.get_value_by_Key_crypto(c,'KEY_COMMON_SECRET')
    pKEY_TRADE_ACCESS= senbit_db_api.get_value_by_Key(c,'KEY_TRADE_ACCESS')
    pKEY_TRADE_SECRET= senbit_db_api.get_value_by_Key_crypto(c,'KEY_TRADE_SECRET')

    conn.commit()
    conn.close()
    #从本地数据库中读取api-key，也可以直接输入-start

    #生成一个senbit web api object 对象
    swao = Exchange_web_api(pSITE,pKEY_COMMON_ACCESS,pKEY_COMMON_SECRET,pKEY_TRADE_ACCESS,pKEY_TRADE_SECRET)

    print('-----test start--------')

    ret = swao.call_api_timestamp()

    status_code = ret.get('status_code')
    if status_code == 200:
        senbittimestamp = ret.get('json', {}).get('unix')
        swao.setTimestampGap(int((senbittimestamp - time.time())*1000))
    else:
        swao.setTimestampGap(0)

    ret = swao.call_api_tickers('CNYS/USDT')
    print(ret)
    
    ret = swao.call_api_tickers('CNYS/USDT')
    print(ret)

    ret = swao.call_api_get_market_kline('CNYS/USDT',p_period = 60,p_from=int(time.time()*1000),p_max=20)
    print(ret)
    time.sleep(100)

    '''
    #log.logger.info(ret)
    ret = swao.call_api_tickers('CNYS/USDT')
    log.logger.info(ret)
    
    ret = swao.call_api_get_market_depth('CNYS/USDT')
    log.logger.info(ret)

    ret = swao.call_api_get_read_orders('wait','CNYS/USDT','sell',1)
    log.logger.info(ret)

    ret = swao.call_api_get_acount_balance('USDT')
    log.logger.info(ret)

    print('END')

    k = 0
    j = 0
    y = 0

    while True:
        time.sleep( 200 )
        y = y+1
        print("第{}次".format(y))
    '''

if __name__ == "__main__":
    main_run()


