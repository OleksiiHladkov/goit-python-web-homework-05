import logging
import platform
import sys
import aiohttp
import asyncio
from datetime import datetime, timedelta
from time import time


logging.basicConfig(level=logging.INFO)


class ApiClient:
    def __init__(self, request: aiohttp, session: aiohttp.ClientSession):
        self.request = request
        self.session = session

    async def get_data(self, url: str) -> dict:
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error status: {response.status} for {url}")
        except aiohttp.ClientConnectionError as error:
            print(f'Connection error: {url}', str(error))

        return None


def parsing_user_argv(default_argv: list|None == None) -> dict:
    cur_argv = default_argv if default_argv else sys.argv
    
    result = {"status": False, "message": "Unknown exeption"}
    
    try:
        days = int(cur_argv[1])

        if days > 10:
            result["status"] = False
            result["message"] = "Number of days can't be more than 10"
            return result

        result["status"] = True
        result["days"] = days
    except ValueError:
        result["status"] = False
        result["message"] = "First parameter mast be integer"
        return result
    except IndexError:
        result["status"] = False
        result["message"] = "Enter number of days in first parameter"
        return result

    currency_list = []
    last_index = len(cur_argv) - 1
    current_index = 2
    if current_index > last_index:
        currency_list = ["USD", "EUR"]
    else:
        while current_index <= last_index:
            currency_list.append(cur_argv[current_index].upper())
            current_index += 1

    result["currency_list"] = currency_list

    return result


def get_period(days_count) -> list[str]:
    period = []
    curent_date = datetime.now()
    
    start_period = curent_date + timedelta(days=1)

    count = 1

    while count <= days_count:
        start_period -= timedelta(days=1)
        period.append(start_period.strftime("%d.%m.%Y"))
        count += 1

    return period


async def response_handler(period: list[str]) -> list[dict]:
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async with aiohttp.ClientSession() as session:
        api_client = ApiClient(aiohttp, session)

        result = []
            
        for date in period:
            data = await api_client.get_data(f"https://api.privatbank.ua/p24api/exchange_rates?json&date={date}")
            result.append(data)

        return result
    

async def main(default_argv: list|None == None) -> str:   
    param = parsing_user_argv(default_argv)

    if not param.get("status", False):
        return param.get("message")
    
    perod = get_period(param.get("days"))
    currency_list = param.get("currency_list")
    
    data = await response_handler(perod)
    
    exchange = []
    for date_exchange in data:
        if not date_exchange:
            continue
        date = date_exchange.get("date")
        
        exchange_rate = date_exchange.get("exchangeRate")
        exchange_list = list(filter(lambda el: el["currency"] in currency_list, exchange_rate))

        date_dict = {}
        currency_dict = {}
        values_dict = {}
        for currency in exchange_list:
            values_dict["sale"] = currency.get("saleRate")
            values_dict["purchase"] = currency.get("purchaseRate")
            currency_dict[currency.get("currency")] = values_dict
        
        date_dict[date] = currency_dict
        exchange.append(date_dict)
    
    if not len(exchange):
        return "Exchange rates could not be found! Change request and try again."
    
    return str(exchange)



    
if __name__ == "__main__":
    # start = time()
    r = asyncio.run(main(None))
    print(r)
    # print(f"Processing time: {time() - start} sec")
