import logging
import asyncio
from collections import namedtuple
from hermes.exchanges.ndax import BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID
from hermes.utils.structures import Order
from typing import Tuple
from functools import lru_cache

SIDE_BUY = 0
SIDE_SELL = 1

ORDER_TYPE_MARKET = 1


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
        value = self._get_forward_cash_throughput(cash_available)
        multiplier = self.forward()
        return (multiplier - 1) * value

    def get_forward_orders(self, cash_available: float) -> Tuple[Order]:
        # This is harder than I thought
        #
        # First I need to identify what the bottleneck is between the three
        # Then I need to propagate the value of that trade back

        # Aliases
        fee_adjustment = self.adjusted_single_trade_value

        throughput = self._get_forward_cash_throughput(cash_available)
        if throughput < 0:
            return None

        btc_cad_ask_price = self.orderbook[BTCCAD_ID].get_ask_prices()[0]
        btc_usdt_bid_price = self.orderbook[BTCUSDT_ID].get_bid_prices()[0]
        usdt_cad_bid_price = self.orderbook[USDTCAD_ID].get_bid_prices()[0]

        order1_qty = throughput / btc_cad_ask_price
        order2_qty = order1_qty * fee_adjustment
        order3_qty = order2_qty * btc_usdt_bid_price * fee_adjustment

        order1 = Order(
            instrument_id=BTCCAD_ID,
            side=0,
            quantity=order1_qty,
            order_type=ORDER_TYPE_MARKET,
            expected_price=btc_cad_ask_price,
        )
        order2 = Order(
            instrument_id=BTCUSDT_ID,
            side=1,
            quantity=order2_qty,
            order_type=ORDER_TYPE_MARKET,
            expected_price=btc_usdt_bid_price,
        )
        order3 = Order(
            instrument_id=USDTCAD_ID,
            side=1,
            quantity=order3_qty,
            order_type=ORDER_TYPE_MARKET,
            expected_price=usdt_cad_bid_price
        )

        return (order1, order2, order3)

    def backward(self):
        return (
            1
            / self.orderbook[USDTCAD_ID].get_ask_prices()[0]
            / self.orderbook[BTCUSDT_ID].get_ask_prices()[0]
            * self.orderbook[BTCCAD_ID].get_bid_prices()[0]
        ) * self.triangle_value_multiplier

    def backward_net(self, cash_available):
        value = self._get_backward_cash_throughput(cash_available)
        multiplier = self.backward()

        return (multiplier - 1) * value

    def get_backward_orders(self, cash_available):
        fee_adjustment = self.adjusted_single_trade_value

        throughput = self._get_backward_cash_throughput(cash_available)
        if throughput < 0:
            return None

        usdt_cad_ask_price = self.orderbook[USDTCAD_ID].get_ask_prices()[0]
        btc_usdt_ask_price = self.orderbook[BTCUSDT_ID].get_ask_prices()[0]
        btc_cad_bid_price = self.orderbook[BTCCAD_ID].get_bid_prices()[0]

        order1_qty = throughput / usdt_cad_ask_price
        order2_qty = order1_qty / btc_usdt_ask_price * fee_adjustment
        order3_qty = order2_qty * fee_adjustment

        order1 = Order(
            instrument_id=USDTCAD_ID,
            side=0,
            quantity=order1_qty,
            order_type=ORDER_TYPE_MARKET,
            expected_price=usdt_cad_ask_price
        )
        order2 = Order(
            instrument_id=BTCUSDT_ID,
            side=0,
            quantity=order2_qty,
            order_type=ORDER_TYPE_MARKET,
            expected_price=btc_usdt_ask_price
        )
        order3 = Order(
            instrument_id=BTCCAD_ID,
            side=1,
            quantity=order3_qty,
            order_type=ORDER_TYPE_MARKET,
            expected_price=btc_cad_bid_price
        )

        return (order1, order2, order3)

    def _get_forward_cash_throughput(self, cash_available) -> float:
        # Gets the L1 tradethrough value in cash amounts
        # and provides the trade_ix, which can be used to efficiently
        # get the trade orders
        btc_cad_ask_price, btc_cad_ask_qty = self.orderbook[BTCCAD_ID].get_asks()[0]
        usdt_cad_bid_price, usdt_cad_bid_qty = self.orderbook[USDTCAD_ID].get_bids()[0]
        btc_usdt_bid_price, btc_usdt_bid_qty = self.orderbook[BTCUSDT_ID].get_bids()[0]

        # Trying to minimize computation
        current_best = cash_available

        t1_order = btc_cad_ask_qty * btc_cad_ask_price

        if t1_order < current_best:
            current_best = t1_order

        t2_order = (
            btc_usdt_bid_qty * btc_cad_ask_price / self.adjusted_single_trade_value
        )
        if t2_order < current_best:
            current_best = t2_order

        t3_order = (
            usdt_cad_bid_qty
            * btc_cad_ask_price
            / (btc_usdt_bid_price * self.adjusted_single_trade_value ** 2)
        )
        if t3_order < current_best:
            current_best = t3_order

        return current_best

    def _get_backward_cash_throughput(self, cash_available) -> float:
        btc_cad_bid_price, btc_cad_bid_qty = self.orderbook[BTCCAD_ID].get_bids()[0]
        usdt_cad_ask_price, usdt_cad_ask_qty = self.orderbook[USDTCAD_ID].get_asks()[0]
        btc_usdt_ask_price, btc_usdt_ask_qty = self.orderbook[BTCUSDT_ID].get_asks()[0]

        current_best = cash_available

        t1_order = usdt_cad_ask_qty * usdt_cad_ask_price
        if t1_order < current_best:
            current_best = t1_order

        t2_order = (
            btc_usdt_ask_qty
            * btc_usdt_ask_price
            * usdt_cad_ask_price
            / self.adjusted_single_trade_value
        )
        if t2_order < current_best:
            current_best = t2_order

        t3_order = (
            btc_cad_bid_qty
            * usdt_cad_ask_price
            * btc_usdt_ask_price
            / self.adjusted_single_trade_value ** 2
        )
        if t3_order < current_best:
            current_best = t3_order

        return current_best
