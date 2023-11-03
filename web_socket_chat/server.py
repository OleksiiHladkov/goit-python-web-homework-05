import asyncio
from datetime import datetime
import logging
from pkg_resources import resource_filename

from aiofile import async_open
import names
import websockets
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK

import exchange_rates

logging.basicConfig(level=logging.INFO)


class Logger:
    def __init__(self, file_name: str, user: WebSocketServerProtocol, time: datetime, data: str) -> None:
        self.path = f"./{file_name}"
        self.user = user
        self.time = time
        self.data = data

    async def logging_exchange_command(self, response: list|str, message: str):
        rfn = resource_filename("web_socket_chat", self.path)
        async with async_open(rfn, "a+") as afp:
            format = "%d/%m/%Y, %H:%M:%S"
            await afp.write(f"{self.time.strftime(format)} - user: {self.user.name} - command: [{self.data}] - response: {str(response)} - message: [{message}]\n")


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_client(self, message: str, ws: WebSocketServerProtocol):
        if self.clients:
            await ws.send(message)
    
    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            split_message = message.strip().split()
            
            if len(split_message) and split_message[0] == "exchange":
                logger = Logger("exchange_log_file.txt", ws, datetime.now(), message)
                
                if len(split_message) == 1:
                    split_message.append("1")
                    exchange_data = await exchange_rates.main(split_message)
                else:
                    exchange_data = await exchange_rates.main(message.strip().split())
                
                new_message = await self.exchange_data_handler(exchange_data)                
                await self.send_to_client(new_message, ws)
                
                await logger.logging_exchange_command(exchange_data, new_message)
            else:
                await self.send_to_clients(f"{ws.name}: {message}")

    async def exchange_data_handler(self, exchange_data: list[dict]|str):
        if isinstance(exchange_data, str):
            return exchange_data
        
        result = ""
        
        for date in exchange_data:
            for date_key, date_value in date.items():
                result += date_key + ": "
                for ex_key, ex_value in date_value.items():
                    result += ex_key + " - "
                    for key, value in ex_value.items():
                        result += f"{key}: {value}" + "; "

        return result


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(main())