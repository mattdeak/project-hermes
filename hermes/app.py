from hermes.exchanges.ndax import (
    NDAXSession,
    create_subscribe_level2_req,
    BTCCAD_ID,
    BTCUSDT_ID,
    USDTCAD_ID,
)
from hermes.orderbook.orderbook import NDAXOrderbook
from hermes.strategies.arbitrage.triangle import TriangleBTCUSDTL1
from hermes.trader.trader import NDAXMarketTriangleTrader
from hermes.exchanges.ndax import create_request
from hermes.account.ndax import NDAXAccount
from hermes.router.router import NDAXRouter
from hermes.utils.synchronization import SingletonTradeLock, SingletonResetEvent

import asyncio
import json
import logging
import traceback
import sys

logging.basicConfig()


# TODO: Create config file for this stuff
BOOK_DEPTH = 10


class NDAXBot:
    def __init__(
        self, user_id, api_key, secret, account_id, orderbook_print_interval=0.5
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = NDAXSession(user_id, api_key, secret)
        self.orderbook = NDAXOrderbook(instrument_keys=(BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID), depth=BOOK_DEPTH)
        self.orderbook_print_interval = orderbook_print_interval

        triangle = TriangleBTCUSDTL1(self.orderbook)
        self.trader = NDAXMarketTriangleTrader(
            self.session,
            self.orderbook,
            account_id,
            triangle,
            50,
            debug_mode=True,
            min_trade_value=0.1, 
        )
        self.account = NDAXAccount(self.session, account_id)
        self.router = NDAXRouter(
            self.session, self.account, self.orderbook, self.trader
        )

        self.event_loop = asyncio.get_event_loop()
        self.trade_lock = SingletonTradeLock.instance(self.event_loop)
        self.reset_trigger = SingletonResetEvent.instance(self.event_loop)

    def start(self):
        self.event_loop.run_until_complete(self.main_loop())

    def collect_bot_tasks(self):
        tasks = [
            self.bot_loop(),
            self.autoreset(),
        ]
        if self.orderbook_print_interval:
            tasks.append(self.orderbook_update_loop())

        tasks.append(self.net_asset_change_loop())
        return tasks

    async def start_bot_tasks(self):
        self.tasks = self.collect_bot_tasks()
        await asyncio.gather(*self.tasks)

    async def cancel_bot_tasks(self):
        for task in self.tasks:
            task.cancel()

    async def main_loop(self):
        # Initialize session first
        while True:
            tasks = self.collect_bot_tasks()
            tasks.append(self.reset_trigger.wait())
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )

            # Catch and report exceptions.
            for done_task in done:
                e = done_task.exception()
                if e:
                    self.logger.error(e)

            self.logger.warning("RESET REQUESTED: Acquiring Trade Lock")
            async with self.trade_lock:
                self.logger.warning("RESET REQUESTED: Restarting Tasks")
                for task in pending:
                    task.cancel()

            self.orderbook.clear()

            # TODO: Probably a cleaner way to do this
            self.trader.permanent_trade_lock = False
            self.reset_trigger.clear()

    async def bot_loop(self):
        await self.session.initialize_session()
        try:
            await self.session.authenticate()
            await self.account.request_account_update()

            sub_requests = self.get_sub_requests()
            for request in sub_requests:
                await self.session.send(request)
            async for message in self.session.session:
                await self.router.route(message)
        except asyncio.CancelledError:
            self.logger.error("Cancelled")
        finally:
            await self.session.close()

    async def autoreset(
        self, autoreset_timer=30
    ):  # Automatically resyncs every minutes, just in case
        autoreset_interval_in_seconds = autoreset_timer * 60
        while True:
            await asyncio.sleep(autoreset_interval_in_seconds)
            self.logger.info('Triggering Auto-reset...')
            self.reset_trigger.set()

    async def orderbook_update_loop(self):
        while True:
            await asyncio.sleep(self.orderbook_print_interval * 60)
            # Don't print while there's an ongoing trade
            async with self.trade_lock:
                self.orderbook.print_orderbook()
                print('------------------------')

    async def net_asset_change_loop(self, update_time=30):  # 30 minutes
        await asyncio.sleep(10)  # Wait for other stuff to initialize
        current_assets = {k: v for k, v in self.account.positions.items()}
        self.logger.info(f"Current Assets: {current_assets}")
        while (
            True
        ):  # TODO Chances are low, but this could interfere with trades. It is probably best to schedule this more intelligently
            await self.account.request_account_update()
            await asyncio.sleep(
                10
            )  # TODO: This is bad design. Should use a condition or something.

            async with self.trade_lock:
                new_assets = {k: v for k, v in self.account.positions.items()}

                for k in new_assets:
                    if new_assets[k] != current_assets[k]:
                        self.logger.info(
                            f"Net Change in {k}: {new_assets[k] - current_assets[k]}"
                        )

            await asyncio.sleep(update_time * 60)

    def get_sub_requests(self):
        req1 = create_subscribe_level2_req(BTCCAD_ID, depth=BOOK_DEPTH)
        req2 = create_subscribe_level2_req(BTCUSDT_ID, depth=BOOK_DEPTH)
        req3 = create_subscribe_level2_req(USDTCAD_ID, depth=BOOK_DEPTH)
        req4 = create_request(
            0,
            "SubscribeAccountEvents",
            {"OMSId": 1, "AccountId": self.account.account_id},
        )

        return req1, req2, req3, req4


if __name__ == "__main__":

    with open("secrets/ndax.json", "r") as sfile:
        data = json.load(sfile)
    bot = NDAXBot(data["user_id"], data["api_key"], data["secret"], data["account_id"])
    bot.start()
