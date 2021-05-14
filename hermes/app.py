from hermes.exchanges.ndax import (
    NDAXSession,
    create_subscribe_level2_req,
    BTCCAD_ID,
    BTCUSDT_ID,
    USDTCAD_ID,
)
from hermes.orderbook.orderbook import MultiOrderBook
from hermes.strategies.arbitrage.triangle import TriangleBTCUSDTL1
from hermes.trader.trader import NDAXMarketTriangleTrader
from hermes.exchanges.ndax import create_request
from hermes.account.ndax import NDAXAccount
from hermes.router.router import NDAXRouter
import asyncio
import json
import logging

logging.basicConfig()


# TODO: Create config file for this stuff
BOOK_DEPTH = 3 


class NDAXBot:
    def __init__(self, user_id, api_key, secret, account_id, orderbook_print_interval=5):
        self.session = NDAXSession(user_id, api_key, secret)
        self.orderbook = MultiOrderBook(depth=BOOK_DEPTH, debug=False)
        self.orderbook_print_interval = orderbook_print_interval

        triangle = TriangleBTCUSDTL1(self.orderbook)
        self.trader = NDAXMarketTriangleTrader(
            self.session, self.orderbook, account_id, triangle, 50, debug_mode=True, min_trade_value=0.01, sequential=True
        )
        self.account = NDAXAccount(self.session, account_id)
        self.router = NDAXRouter(
            self.session, self.account, self.orderbook, self.trader
        )

    def start(self):
        asyncio.run(self.start_all_tasks())

    async def start_all_tasks(self):
        tasks = [self.main_loop()]
        if self.orderbook_print_interval:
            tasks.append(self.orderbook_update_loop())

        await asyncio.gather(*tasks)


    async def main_loop(self):
        # Initialize session
        await self.session.initialize_session()
        await self.session.authenticate()

        await self.account.request_account_update()

        sub_requests = self.get_sub_requests()
        for request in sub_requests:
            await self.session.send(request)

        async for message in self.session.session:
            await self.router.route(message)

    async def orderbook_update_loop(self):
        while True:
            self.orderbook.print_orderbook()
            print('-------')
            await asyncio.sleep(self.orderbook_print_interval*60)

    async def refresh_session(self, mins_until_refresh=30):
        seconds_until_refresh = mins_until_refresh*60
        while True:
            await asyncio.sleep(seconds_until_refresh)
            await self.session.refresh()

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
    bot = NDAXBot(data["user_id"], data["api_key"], data['secret'], data['account_id'])
    bot.start()
