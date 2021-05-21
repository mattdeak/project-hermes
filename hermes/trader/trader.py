import asyncio
import logging
from hermes.exchanges.ndax import create_request, BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID
from hermes.utils.structures import Order
from hermes.utils.synchronization import SingletonTradeLock, SingletonResetEvent
from uuid import uuid1
from typing import List
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
        self.order_records = {}
        self.pending_orders = []
        self.current_trade_id = 1

        # Singleton trade lock, so it can be shared with other components easily
        self.trade_lock = SingletonTradeLock.instance()
        self.reset_trigger = SingletonResetEvent.instance()

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
    ):
        super().__init__(session, orderbook, account_id)
        self.triangle = triangle
        self.min_trade_value = min_trade_value
        self.cash_available = cash_available
        self.debug_mode = debug_mode
        self.VALUE_DIFF_THRESH = 0.001
        self.outstanding_orders = []

        self.permanent_trade_lock = (
            False  # TODO: Temporary, should restart if this ever occurs
        )

    async def recheck_orderbook_and_trade(self):
        if self.permanent_trade_lock or self.trade_lock.locked():
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

    async def process_orders(self, orders):
        # For the market triangle, we just send all of them immediately
        await self.trade_lock.acquire()

        for order in orders:
            await self.send_order(order)

    async def handle_trade_event(self, event_payload):
        self.logger.info("Handling Trade Event")
        self.match_order(event_payload)

    async def send_order(self, order):
        self.logger.info(f"Sending Order: {order}")

        trade_id = self.create_trade_id()
        self.order_records[trade_id] = order
        self.outstanding_orders.append(trade_id)

        request = self.format_request(trade_id, order)
        await self.session.send(request)

    def match_order(self, event_payload):
        client_id = event_payload["ClientOrderId"]
        quantity = event_payload["Quantity"]
        price = event_payload["Price"]
        side = event_payload["Side"]
        instrument_id = event_payload["InstrumentId"]
        value = event_payload["Value"]

        expected_order = self.order_records[client_id]
        expected_price = expected_order.expected_price
        expected_quantity = expected_order.quantity

        if side == "Buy":
            self.logger.info(
                f"Bought {instrument_id}: {quantity} at {price}. Value: {value}"
            )
            self.logger.info(f"Expected: {expected_order}")

            price_ratio = (
                price / expected_price
            )  # Large value over expected value means more money was paid on the purchase

        else:
            self.logger.info(
                f"Sold {instrument_id}: {quantity} at {price}. Value: {value}"
            )
            self.logger.info(f"Expected: {expected_order}")
            price_ratio = (
                expected_price / price
            )  # Large expected value over small value means less money was made on the sale

        quantity_ratio = quantity / expected_quantity

        if price_ratio > 1 + self.VALUE_DIFF_THRESH:  # A quantity ratio of at least 0.
            if (
                quantity_ratio > 0.99
            ):  # Then almost the whole trade was executed at the wrong price. Most likely a price mismatch rather than slippage
                self.logger.warning(
                    f"Value difference of {price_ratio} and quantity ratio of {quantity_ratio} exceeds threshold, setting permalock."
                )
                self.reset_trigger.set()  # Request a reset in case of synchronization problem
                self.permanent_trade_lock = True  # Shouldn't be needed, but just in case we don't want to trade again before the reset is complete
            else:
                self.logger.warning("Slippage Detected.")

    async def handle_state_change_event(self, event_payload):
        client_id = event_payload["ClientOrderId"]
        status = event_payload["OrderState"]
        if status == "FullyExecuted":
            self.outstanding_orders.remove(client_id)
            # Release trade lock if everything came back
            if len(self.outstanding_orders) == 0:
                self.logger.info('Releasing Trade Lock')
                self.trade_lock.release()

    def reset(self):
        self.order_records = {}


class NDAXDummyTriangleTrader(NDAXMarketTriangleTrader):
    async def release_trade_lock(self):
        await asyncio.sleep(0.5)
        self.trade_lock = False

    async def send_requests(self, requests):
        for request in requests:
            await asyncio.sleep(0.001)
            self.logger.info(f"Would have sent request: {request}")

        asyncio.create_task(self.release_trade_lock())
