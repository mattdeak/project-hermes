import logging
import asyncio
from collections import namedtuple
from hermes.exchanges.ndax import BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID
from hermes.utils.structures import Order
from typing import Tuple
from functools import lru_cache

OrderbookLine = namedtuple("OrderbookLine", ["price", "quantity"])
Instrument = namedtuple("Instrument", ["bid", "ask"])


class TriangleBTCUSDTL1:
    def __init__(self, orderbook, fee=0.002):  # Base to X. Eg BTC_CAD  # 0.2%
        self.adjusted_single_trade_value = 1 - fee
        self.triangle_value_multiplier = (1 - fee) ** 3

        self.instrument_ids = BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID
        self.orderbook = orderbook

    def forward(self) -> float:
        return (
            1
            / (
                self.orderbook[BTCCAD_ID].get_ask_prices()[0]
                / self.orderbook[BTCUSDT_ID].get_bid_prices()[0]
                / self.orderbook[USDTCAD_ID].get_bid_prices()[0]
            )
            * self.triangle_value_multiplier
        )

    def forward_net(self, cash_available):
        value, _ = self._get_forward_bottleneck_ix_and_cash_value(cash_available)
        multiplier = self.forward()
        return (multiplier - 1) * value

    def get_forward_orders(self, cash_available: float) -> Tuple[Order]:
        # This is harder than I thought
        #
        # First I need to identify what the bottleneck is between the three
        # Then I need to propagate the value of that trade back

        # Aliases
        fee_adjustment = self.adjusted_single_trade_value

        ix, trade_value = self._get_forward_bottleneck_ix_and_cash_value(cash_available)
        btc_cad_ask_price, btc_cad_ask_qty = self.orderbook[BTCCAD_ID].get_asks()[0]
        btc_usdt_bid_price, btc_usdt_bid_qty = self.orderbook[BTCUSDT_ID].get_bids()[0]
        usdt_cad_bid_price, usdt_cad_bid_qty = self.orderbook[USDTCAD_ID].get_bids()[0]

        if ix == 0:  # Cash bottleneck
            order1_qty = cash_available / btc_cad_ask_price
            order2_qty = cash_available / btc_cad_ask_price * fee_adjustment
            order3_qty = (
                cash_available
                / btc_cad_ask_price
                * btc_usdt_bid_price
                * fee_adjustment ** 2
            )

        elif ix == 1:  # BTC Ask bottleneck
            order1_qty = btc_cad_ask_qty
            order2_qty = btc_cad_ask_qty * fee_adjustment
            order3_qty = btc_cad_ask_qty * btc_usdt_bid_price * fee_adjustment ** 2

        elif ix == 2:  # BTC Bid Bottleneck
            order1_qty = btc_usdt_bid_qty / fee_adjustment
            order2_qty = btc_usdt_bid_qty
            order3_qty = btc_usdt_bid_qty * btc_usdt_bid_price * fee_adjustment

        elif ix == 3:  # USDT Bid Bottleneck
            order1_qty = usdt_cad_bid_qty * usdt_cad_bid_price

        return (order1_qty, order2_qty, order3_qty)

    def backward(self):
        return (
            1
            / self.orderbook[USDTCAD_ID].get_ask_prices()[0]
            / self.orderbook[BTCUSDT_ID].get_ask_prices()[0]
            * self.orderbook[BTCCAD_ID].get_bid_prices()[0]
        ) * self.triangle_value_multiplier

    def backward_net(self, cash_available):
        value, _ = self._get_backward_bottleneck_ix_and_cash_value(cash_available)
        multiplier = self.backward()

        return (multiplier - 1) * value


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

    def _get_forward_bottleneck_ix_and_cash_value(
        self, cash_available
    ) -> Tuple[float, int]:
        # Gets the L1 tradethrough value in cash amounts
        # and provides the trade_ix, which can be used to efficiently
        # get the trade orders
        btc_cad_ask_price, btc_cad_ask_qty = self.orderbook[BTCCAD_ID].get_asks()[0]
        usdt_cad_bid_price, usdt_cad_bid_qty = self.orderbook[USDTCAD_ID].get_bids()[0]
        btc_usdt_bid_price, btc_usdt_bid_qty = self.orderbook[BTCUSDT_ID].get_bids()[0]

        # Trying to minimize computation
        current_best = cash_available
        current_ix = 0

        t1_order = btc_cad_ask_qty * btc_cad_ask_price

        if t1_order < current_best:
            current_best = t1_order
            current_ix = 1

        t2_order = (
            btc_usdt_bid_qty * btc_cad_ask_price / self.adjusted_single_trade_value
        )
        if t2_order < current_best:
            current_best = t2_order
            current_ix = 2

        t3_order = (
            usdt_cad_bid_qty
            * btc_cad_ask_price
            / (btc_usdt_bid_price * self.adjusted_single_trade_value ** 2)
        )
        if t3_order < current_best:
            current_best = t3_order
            current_ix = 3

        return current_best, current_ix


    def _get_backward_bottleneck_ix_and_cash_value(self, cash_available) -> Tuple[float, int]:
        btc_cad_bid_price, btc_cad_bid_qty = self.orderbook[BTCCAD_ID].get_bids()[0]
        usdt_cad_ask_price, usdt_cad_ask_qty = self.orderbook[USDTCAD_ID].get_asks()[0]
        btc_usdt_ask_price, btc_usdt_ask_qty = self.orderbook[BTCUSDT_ID].get_asks()[0]
        

        current_best = cash_available
        current_ix = 0

        t1_order = usdt_cad_ask_qty * usdt_cad_ask_price
        if t1_order < current_best:
            current_best = t1_order
            current_ix = 1

        t2_order = btc_usdt_ask_qty * btc_usdt_ask_price * usdt_cad_ask_price / self.adjusted_single_trade_value
        if t2_order < current_best:
            current_best = t2_order
            current_ix = 2

        t3_order = btc_cad_bid_qty * usdt_cad_ask_price * btc_usdt_ask_price / self.adjusted_single_trade_value ** 2
        if t3_order < current_best:
            current_best = t3_order
            current_ix = 3
        
        return current_best, current_ix

