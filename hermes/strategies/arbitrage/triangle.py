import logging
import asyncio
from collections import namedtuple

OrderbookLine = namedtuple("OrderbookLine", ["price", "quantity"])
Instrument = namedtuple("Instrument", ["bid", "ask"])


class TriangleBTCUSDT:
    def __init__(
        self,
        btc_cad,
        btc_usdt,
        usdt_cad,
        fee=0.002,
        max_btc_order=float("inf"),
        max_usdt_order=float("inf"),  # Base to X. Eg BTC_CAD  # 0.2%
    ):
        self.adjusted_single_trade_value = 1 - fee
        self.triangle_value_multiplier = (1 - fee) ** 3

        self.btc_cad = btc_cad
        self.btc_usdt = btc_usdt
        self.usdt_cad = usdt_cad

        self.max_btc_order = max_btc_order
        self.max_usdt_order = max_usdt_order

    # TODO: The quantities need to be different. I need to get the effective trade in the
    # target currency.
    #   Fine the minimum price, get appropriate amounts for each currency. Need them to issue trades.
    def forward(self):
        return (
            1
            / (
                self.btc_cad.ask.price
                / self.btc_usdt.bid.price
                / self.usdt_cad.bid.price
            )
            * self.triangle_value_multiplier
        )

    def forward_with_l1_limit(self):
        fee = self.fee  # alias
        t1_effective_quantity = self.btc_cad.ask.quantity * self.btc_cad.ask.price
        t2_effective_quantity = self.btc_cad.ask.quantity * self.btc_cad.ask.price / fee
        t3_effective_quantity = (
            self.usdt_cad.bid.quantity * self.usdt_cad.bid.price / fee ** 2
        )

        viable_trade = min(
            t1_effective_quantity, t2_effective_quantity, t3_effective_quantity
        )
        return (
            1 / (self.btc_cad.ask / self.btc_usdt.bid.price / self.usdt_cad.bid.price),
            viable_trade,
        )

    def get_forward_orders(self, cash_available):
        fee_adjustment = self.adjusted_single_trade_value
        squared_fee_adjustment = fee_adjustment ** 2

        btc_cad_ask_qty = self.btc_cad.ask.quantity
        btc_usdt_bid_qty = self.btc_usdt.bid.quantity
        usdt_cad_bid_qty = self.usdt_cad.bid.quantity

        btc_cad_ask_price = self.btc_cad.ask.price
        btc_usdt_bid_price = self.btc_usdt.bid.price
        usdt_cad_bid_price = self.usdt_cad.bid.price

        order1_qty = min(
            cash_available / btc_cad_ask_price,
            btc_cad_ask_qty,
            btc_usdt_bid_qty / fee_adjustment,
            usdt_cad_bid_qty * usdt_cad_bid_price * squared_fee_adjustment,
        )

        order2_qty = min(
            cash_available / btc_cad_ask_price * fee_adjustment,
            btc_cad_ask_qty * fee_adjustment,
            btc_usdt_bid_qty,
            (usdt_cad_bid_qty / usdt_cad_bid_price) / fee_adjustment,
        )

        order3_qty = min(
            cash_available
            / btc_cad_ask_price
            * btc_usdt_bid_price
            * squared_fee_adjustment,
            btc_cad_ask_qty * btc_usdt_bid_price * squared_fee_adjustment,
            btc_usdt_bid_qty * btc_usdt_bid_price * squared_fee_adjustment,
            usdt_cad_bid_qty,
        )

        return (order1_qty, order2_qty, order3_qty)

    def _backward(self):
        fee = self.fee

        t1_effective_quantity = self.usdt_cad.ask.price * self.usdt_cad.ask.quantity
        t2_effective_quantity = (
            self.btc_usdt.ask.price * self.btc_usdt.ask.quantity / fee
        )
        t3_effective_quantity = (
            self.btc_cad.bid.price * self.btc_cad.bid.quantity / fee ** 2
        )

        viable_trade = min(
            t1_effective_quantity, t2_effective_quantity, t3_effective_quantity
        )

        return (
            (
                1
                / self.usdt_cad.ask.price
                / self.btc_usdt.ask.price
                * self.btc_cad.bid.price
            ),
            viable_trade,
        )

    def get_backward_orders(self, cash_available):
        fee_adjustment = 1 - self.fees
        squared_fee_adjustment = (1 / self.fees) ** 2

        btc_cad_bid_qty = self.btc_cad.bid.quantity
        btc_usdt_ask_qty = self.btc_usdt.ask.quantity
        usdt_cad_ask_qty = self.usdt_cad.ask.quantity

        btc_cad_bid_price = self.btc_cad.bid.price
        btc_usdt_ask_price = self.btc_usdt.ask.price
        usdt_cad_ask_price = self.usdt_cad.ask.price

        # TODO: Implement backward orders
        pass


class NDAXTrader:
    def __init__(self, session, trade_queue):
        self.trade_queue
        pass

    async def run(self):
        while True:
            trades = await self.trade_queue.pop()
            await self.handle_trades(trades)

    async def handle_trades(self):
        pass

    async def handle_trades(self):
        pass


class TriangleMarketTrader:
    def __init__(
        self,
        session,
        message_queue,
        triangle,
        trade_lock,
        min_value=0.01,
        max_trade_vals=(500, 0.001, 500),
    ):
        self.session = session
        self.triangle = triangle
        self.logger = logging.getLogger(self.__class__.__name__)

        self.trade_lock = trade_lock

    async def process(self):
        """process

        """
        forward_val, forward_trade = self.triangle.forward()
        backward_val, backward_trade = self.triangle.backward()

        if forward_val > 1:
            pass

        if backward_val > 1:
            pass

    async def send_and_confirm(self, orders):
        """send_and_confirm.

        This will by default block until all orders are confirmed. Are we sure this is how we want to do it?

        :param orders:
        """
        for order in orders:
            await self.session.send(orders)

            confirmation = await message_queue.pop()
            self.handle_confirmation(confirmation)
