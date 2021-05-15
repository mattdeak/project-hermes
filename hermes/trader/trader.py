import asyncio
import logging
from hermes.exchanges.ndax import create_request, BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID
from hermes.utils.structures import Order
from uuid import uuid1
from typing import List
from dataclasses import dataclass
from math import floor

FORWARD = 0
BACKWARD = 1

QTY_DECIMAL_PLACES = {BTCCAD_ID: 6, BTCUSDT_ID: 6, USDTCAD_ID: 2}


class NDAXTrader:
    def __init__(self, session, orderbook, account_id):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = session
        self.orderbook = orderbook
        self.account_id = account_id
        self.outstanding_orders = {}
        self.pending_orders = []
        self.current_trade_id = 1
        self.trade_lock = False

    async def run(self):
        pass

    def format_request(self, client_id: int, order: Order):
        payload = {
            "InstrumentId": order.instrument_id,
            "OMSId": 1,
            "AccountId": self.account_id,
            "TimeInForce": order.time_in_force,
            "ClientOrderId": client_id,
            "OrderIdOCO": 0,
            "UseDisplayQuantity": False,
            "Side": order.side,
            "Quantity": round(order.quantity, QTY_DECIMAL_PLACES[order.instrument_id]),
            "OrderType": order.order_type,
            "PegPriceType": 1,
        }

        request = create_request(0, "SendOrder", payload)
        return request

    def create_trade_id(self):
        self.current_trade_id += 1
        return self.current_trade_id

    async def handle_trade_event(self, response):
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
    def __init__(
        self, session, orderbook, account_id, triangle, cash, debug_mode=False
    ):
        super().__init__(session, orderbook, account_id)
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
        account_id,
        triangle,
        cash_available,
        min_trade_value=0.1,
        debug_mode=False,
        sequential=False,
    ):
        super().__init__(session, orderbook, account_id)
        self.triangle = triangle
        self.min_trade_value = min_trade_value
        self.cash_available = cash_available
        self.debug_mode = debug_mode
        self.sequential = sequential
        self.VALUE_DIFF_THRESH = 0.001

        self.trade_lock = False
        self.permanent_trade_lock = (
            False  # TODO: Temporary, should restart if this ever occurs
        )

    async def recheck_orderbook_and_trade(self):
        if self.trade_lock or self.permanent_trade_lock:
            return

        orders = None
        try:
            forward_val = self.triangle.forward_net(self.cash_available)
            if forward_val > self.min_trade_value:
                orders = self.triangle.get_forward_orders(self.cash_available)

            else:
                backward_val = self.triangle.backward_net(self.cash_available)
                if backward_val > self.min_trade_value:
                    orders = self.triangle.get_backward_orders(self.cash_available)
        except IndexError as e:
            self.logger.warning(f"Index Error: {e}")

        if not orders:
            return

        await self.process_orders(orders)
        self.trade_lock = True

    async def process_orders(self, orders):
        if self.sequential:
            # Send the first order, queue the other 2
            self.pending_orders += orders[1:]
            await self.send_order(orders[0])
        else:
            for order in orders:
                await self.send_order(order)

    async def handle_trade_event(self, event_payload):
        self.match_order(event_payload)

        if self.sequential and len(self.pending_orders) != 0:
            next_order = self.pending_orders.pop(0)
            await self.send_order(next_order)
        elif len(self.pending_orders) == 0:
            self.trade_lock = False

    async def send_order(self, order):
        self.logger.info(f"Sending Order: {order}")
        trade_id = self.create_trade_id()
        self.outstanding_orders[trade_id] = order
        request = self.format_request(trade_id, order)
        await self.session.send(request)

    def match_order(self, event_payload):
        client_id = event_payload["ClientOrderId"]
        quantity = event_payload["Quantity"]
        price = event_payload["Price"]
        side = event_payload["Side"]
        instrument_id = event_payload["InstrumentId"]
        value = event_payload["Value"]

        expected_order = self.outstanding_orders[client_id]
        expected_price = expected_order.expected_price

        flagged = False

        if side == "Buy":
            self.logger.info(
                f"Bought {instrument_id}: {quantity} at {price}. Value: {value}"
            )
            self.logger.info(f"Expected: {expected_order}")

            price_ratio = price / expected_price # Large value over expected value means more money was paid on the purchase

        else:
            self.logger.info(
                f"Sold {instrument_id}: {quantity} at {price}. Value: {value}"
            )
            self.logger.info(f"Expected: {expected_order}")
            price_ratio = expected_price / price # Large expected value over small value means less money was made on the sale

        if price_ratio > 1+self.VALUE_DIFF_THRESH:
            self.logger.warning(
                f"Value difference of {price_ratio} exceeds threshold, setting permalock."
            )
            self.permanent_trade_lock = True

        del self.outstanding_orders[client_id]


class NDAXDummyTriangleTrader(NDAXMarketTriangleTrader):
    async def release_trade_lock(self):
        await asyncio.sleep(0.5)
        self.trade_lock = False

    async def send_requests(self, requests):
        for request in requests:
            await asyncio.sleep(0.001)
            self.logger.info(f"Would have sent request: {request}")

        asyncio.create_task(self.release_trade_lock())
