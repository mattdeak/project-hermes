import asyncio
import logging
from hermes.exchanges.ndax import create_request, BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID
from hermes.utils.structures import Order
from uuid import uuid1
from typing import List
from dataclasses import dataclass

FORWARD = 0
BACKWARD = 1


class NDAXTrader:
    def __init__(self, session, orderbook):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.orderbook = orderbook
        self.outstanding_trades = []
        self.current_trade_id = 1

    async def run(self):
        pass

    def format_requests(self, orders: List[Order]):
        requests = []
        for order in orders:
            trade_id = self.create_trade_id()
            payload = {
                "InstrumentId": order.InstrumentId,
                "OMDId": 1,
                "AccountId": 1,  # TODO: Get the real one
                "TimeInForce": order.time_in_force,
                "ClientOrderId": trade_id,
                "OrderIdOCO": 0,
                "UseDisplayQuantity": False,
                "Side": order.side,
                "Quantity": order.quantity,
                "OrderType": order.order_type,
                "PegPriceType": 1,
                "LimitPrice": order.limit_price,
            }
            requests.append(create_request(0, "SendOrder", payload))
        return requests

    def create_trade_id(self):
        self.current_trade_id += 1
        self.outstanding_trades.append(self.current_trade_id)
        return self.current_trade_id

    async def handle_response(self, response):
        print(response)
        if response["n"] == "SendOrder":
            pass  # TODO: Determine if order was a success
        elif response["n"] == "OrderTradeEvent":
            pass  # TODO: handle
        elif response["n"] == "OrderStateEvent":
            pass

    async def send_requests(self, requests):
        for req in requests:
            self.session.send(req)


class NDAXMarketTriangleLogger(NDAXTrader):
    def __init__(self, session, orderbook, triangle, cash, debug_mode=False):
        super().__init__(session, orderbook)
        self.triangle = triangle
        self.cash = cash
        self.debug_mode=debug_mode

    async def run(self):
        while True:
            async with self.orderbook.updated:
                await self.orderbook.updated.wait()

                forward = self.triangle.forward_net(self.cash)
                if forward > 0 or self.debug_mode:
                    self.logger.info(f"Forward Arbitrage Opportunity: {forward}")
                    self.logger.info(f"BTC_CAD: {self.orderbook[BTCCAD_ID].get_asks()[0]}")
                    self.logger.info(f"BTC_USD: {self.orderbook[BTCUSDT_ID].get_bids()[0]}")
                    self.logger.info(f"USDT_CAD: {self.orderbook[USDTCAD_ID].get_bids()[0]}")

                backward = self.triangle.backward_net(self.cash)
                if backward > 0 or self.debug_mode:
                    self.logger.info(f"Backward Arbitrage Opportunity: {backward}")
                    self.logger.info(f"USDT_CAD: {self.orderbook[USDTCAD_ID].get_asks()[0]}")
                    self.logger.info(f"BTC_USD: {self.orderbook[BTCUSDT_ID].get_asks()[0]}")
                    self.logger.info(f"BTC_CAD: {self.orderbook[BTCCAD_ID].get_bids()[0]}")


class NDAXMarketTriangleTrader(NDAXTrader):
    def __init__(self, session, orderbook, triangle, min_trade_value=0.2):
        super().__init__(session, orderbook)
        self.triangle = triangle
        self.min_trade_value = min_trade_value

    async def run(self):
        while True:
            async with self.orderbook.updated:
                await self.orderbook.updated.wait()

                if self.triangle.forward_value() > self.min_trade_value:
                    orders = self.triangle.get_forward_orders()

                elif self.triangle.backward_value() > self.min_trade_value:
                    orders = self.triangle.get_backward_orders()

                requests = self.format_requests(orders)

                for req in requests:
                    await self.session.send(req)


class NDAXDummyTriangleTrader(NDAXMarketTriangleTrader):
    async def send_requests(self, requests):
        for request in requests:
            await asyncio.sleep(0.001)
            self.logger.info(f"Would have sent request: {requests}")
