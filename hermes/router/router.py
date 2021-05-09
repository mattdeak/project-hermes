import asyncio
import json

BTCCAD_ID = 1
BTCUSDT_ID = 82
USDTCAD_ID = 80

class NDAXRouter:
    def __init__(self, session, orderbook, trader, sub_requests):
        self.session = session
        self.orderbook = orderbook
        self.trader = trader
        self.sub_requests = sub_requests

        asyncio.run(self.run())


    async def run(self):
        for sub_request in self.sub_requests:
            self.session.send(sub_request)

        async for raw_message in self.session.session:
            message = json.loads(raw_message)

            if message['n'] == '': # Should update order book
                payload = json.loads(message['o'])
                await self.orderbook.update(payload)
            
            if message['n'] == '': # Trade confirmation
                self.trader.handle_response(message)
            

