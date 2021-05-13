from hermes.exchanges.ndax import (
    NDAXSession,
    create_subscribe_level2_req,
    BTCCAD_ID,
    BTCUSDT_ID,
    USDTCAD_ID,
)
from hermes.orderbook.orderbook import MultiOrderBook
from hermes.strategies.arbitrage.triangle import TriangleBTCUSDTL1
from hermes.trader.trader import NDAXDummyTriangleTrader
from hermes.exchanges.ndax import create_request
from hermes.account.ndax import NDAXAccount
from hermes.router.router import NDAXRouter
import asyncio
import json
import logging

logging.basicConfig()


# TODO: Create config file for this stuff
BOOK_DEPTH = 10 


class NDAXBot:
    def __init__(self, username, password, account_id):
        self.session = NDAXSession(username, password, None)
        self.orderbook = MultiOrderBook(depth=BOOK_DEPTH, debug=True)

        triangle = TriangleBTCUSDTL1(self.orderbook)
        self.trader = NDAXDummyTriangleTrader(
            self.session, self.orderbook, triangle, 1000, debug_mode=False
        )
        self.account = NDAXAccount(self.session, account_id)
        self.router = NDAXRouter(
            self.session, self.account, self.orderbook, self.trader
        )

    def start(self):
        asyncio.run(self.__run__())

    async def __run__(self):
        # Initialize session
        await self.session.initialize_session()
        await self.session.authenticate()

        await self.account.request_account_update()

        sub_requests = self.get_sub_requests()
        for request in sub_requests:
            await self.session.send(request)

        async for message in self.session.session:
            await self.router.route(message)

    async def refresh_session(self):
        raise NotImplementedError()

    async def reset(self):
        pass

    def get_sub_requests(self):
        req1 = create_subscribe_level2_req(BTCCAD_ID, depth=BOOK_DEPTH)
        req2 = create_subscribe_level2_req(BTCUSDT_ID, depth=BOOK_DEPTH)
        req3 = create_subscribe_level2_req(USDTCAD_ID, depth=BOOK_DEPTH)
        req4 = create_request(0, 'SubscribeAccountEvents', {'OMSId': 1, 'AccountId': self.account.account_id})

        return req1, req2, req3, req4

    def get_unsub_requests(self):
        pass


if __name__ == "__main__":

    with open("secrets/ndax.json", "r") as sfile:
        data = json.load(sfile)
    bot = NDAXBot(data["username"], data["password"], data['account_id'])
    bot.start()
