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
        self.session = session
        self.orderbook = orderbook
        self.outstanding_trades = []
        self.current_trade_id = 1
        self.trade_lock = False

    async def run(self):
        pass

    def format_requests(self, orders: List[Order]):
        requests = []
        for order in orders:
            trade_id = self.create_trade_id()
            payload = {
                "InstrumentId": order.instrument_id,
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
        self.debug_mode = debug_mode

    async def run(self):
        while True:
            async with self.orderbook.updated:
                await self.orderbook.updated.wait()

                forward = self.triangle.forward_net(self.cash)
                if forward > 0 or self.debug_mode:
                    self.logger.info(f"Forward Arbitrage Opportunity: {forward}")
                    self.logger.info(
                        f"BTC_CAD: {self.orderbook[BTCCAD_ID].get_asks()[0]}"
                    )
                    self.logger.info(
                        f"BTC_USD: {self.orderbook[BTCUSDT_ID].get_bids()[0]}"
                    )
                    self.logger.info(
                        f"USDT_CAD: {self.orderbook[USDTCAD_ID].get_bids()[0]}"
                    )

                backward = self.triangle.backward_net(self.cash)
                if backward > 0 or self.debug_mode:
                    self.logger.info(f"Backward Arbitrage Opportunity: {backward}")
                    self.logger.info(
                        f"USDT_CAD: {self.orderbook[USDTCAD_ID].get_asks()[0]}"
                    )
                    self.logger.info(
                        f"BTC_USD: {self.orderbook[BTCUSDT_ID].get_asks()[0]}"
                    )
                    self.logger.info(
                        f"BTC_CAD: {self.orderbook[BTCCAD_ID].get_bids()[0]}"
                    )


class NDAXMarketTriangleTrader(NDAXTrader):
    def __init__(
        self,
        session,
        orderbook,
        triangle,
        cash_available,
        min_trade_value=0.2,
        debug_mode=False,
    ):
        super().__init__(session, orderbook)
        self.triangle = triangle
        self.min_trade_value = min_trade_value
        self.cash_available = cash_available
        self.debug_mode = debug_mode

    async def recheck_orderbook_and_trade(self):
        if self.trade_lock:
            return

        orders = None
        if (
            self.triangle.forward_net(self.cash_available) > self.min_trade_value
            or self.debug_mode
        ):
            orders = self.triangle.get_forward_orders(self.cash_available)

        elif self.triangle.backward_net(self.cash_available) > self.min_trade_value:
            orders = self.triangle.get_backward_orders(self.cash_available)

        if not orders:
            return

        if self.debug_mode:
            for i, order in enumerate(orders):
                self.logger.info(f"Order {i}: {order}")

        requests = self.format_requests(orders)
        await self.send_requests(requests)

        self.trade_lock = True

    async def validate_orders(self, orders):
        pass

    async def update_account_quantities(self):
        pass


class NDAXDummyTriangleTrader(NDAXMarketTriangleTrader):
    async def release_trade_lock(self):
        await asyncio.sleep(0.5)
        self.trade_lock = False

    async def send_requests(self, requests):
        for request in requests:
            await asyncio.sleep(0.001)
            self.logger.info(f"Would have sent request: {request}")

        asyncio.create_task(self.release_trade_lock())