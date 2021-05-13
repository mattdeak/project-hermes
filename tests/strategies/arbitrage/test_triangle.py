import pytest

from hermes.strategies.arbitrage.triangle import (
    TriangleBTCUSDTL1,
    SIDE_BUY,
    SIDE_SELL,
    ORDER_TYPE_MARKET,
)
from hermes.orderbook.orderbook import MultiOrderBook, OrderBook
from hermes.exchanges.ndax import BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID
from hermes.utils.structures import Order


@pytest.fixture
def orderbook_1():
    orderbook = MultiOrderBook(depth=1)

    btc_cad_orderbook = OrderBook(depth=1)
    btc_usdt_orderbook = OrderBook(depth=1)
    usdt_cad_orderbook = OrderBook(depth=1)

    btc_cad_orderbook.ask[68971.67] = 0.044
    btc_cad_orderbook.bid[68910] = 0.15759

    btc_usdt_orderbook.ask[57049.62] = 0.053027
    btc_usdt_orderbook.bid[56538.5] = 0.15759

    usdt_cad_orderbook.ask[1.2343] = 1234.16
    usdt_cad_orderbook.bid[1.2166] = 34.96

    orderbook[BTCCAD_ID] = btc_cad_orderbook
    orderbook[BTCUSDT_ID] = btc_usdt_orderbook
    orderbook[USDTCAD_ID] = usdt_cad_orderbook

    return orderbook


@pytest.fixture
def orderbook_2():
    orderbook = MultiOrderBook(depth=1)

    btc_cad_orderbook = OrderBook(depth=1)
    btc_usdt_orderbook = OrderBook(depth=1)
    usdt_cad_orderbook = OrderBook(depth=1)

    btc_cad_orderbook.ask[68971.67] = 0.044
    btc_cad_orderbook.bid[68910] = 0.15759

    btc_usdt_orderbook.ask[57049.62] = 0.053027
    btc_usdt_orderbook.bid[56538.5] = 0.15759

    usdt_cad_orderbook.ask[1.4] = 1234.16
    usdt_cad_orderbook.bid[1.3] = 34.96

    orderbook[BTCCAD_ID] = btc_cad_orderbook
    orderbook[BTCUSDT_ID] = btc_usdt_orderbook
    orderbook[USDTCAD_ID] = usdt_cad_orderbook
    return orderbook

@pytest.fixture
def orderbook_3():
    orderbook = MultiOrderBook(depth=1)

    btc_cad_orderbook = OrderBook(depth=1)
    btc_usdt_orderbook = OrderBook(depth=1)
    usdt_cad_orderbook = OrderBook(depth=1)

    btc_cad_orderbook.ask[61401.15] = 1.243
    btc_cad_orderbook.bid[61400] = 0.0187

    btc_usdt_orderbook.ask[50884.01] = 0.312143
    btc_usdt_orderbook.bid[50700.33] = 0.0492

    usdt_cad_orderbook.ask[1.2332] = 40.38
    usdt_cad_orderbook.bid[1.23] = 6958.44

    orderbook[BTCCAD_ID] = btc_cad_orderbook
    orderbook[BTCUSDT_ID] = btc_usdt_orderbook
    orderbook[USDTCAD_ID] = usdt_cad_orderbook

    return orderbook

@pytest.fixture
def orderbook_4():
    pass

@pytest.fixture
def orderbook_5():
    pass

@pytest.fixture
def orderbook_6():
    pass



class Test_MarketTriangleL1:
    def test_orderbook_1_value(self, orderbook_1):
        triangle = TriangleBTCUSDTL1(orderbook_1, fee=0.002)

        forward = triangle.forward()
        forward_value = 0.9913179648
        backward = triangle.backward()
        backward_value = 0.9727480946

        assert forward == pytest.approx(forward_value, abs=1e-8)
        assert backward == pytest.approx(backward_value, abs=1e-8)

    def test_orderbook_2_value(self, orderbook_2):
        triangle = TriangleBTCUSDTL1(orderbook_2, fee=0.002)

        forward = triangle.forward()
        forward_value = 1.059274498
        backward = triangle.backward()
        backward_value = 0.8576164094

        assert forward == pytest.approx(forward_value, abs=1e-8)
        assert backward == pytest.approx(backward_value, abs=1e-8)

    def test_orderbook_1_net(self, orderbook_1):
        cash_available = 10000  # Not the bottleneck
        triangle = TriangleBTCUSDTL1(orderbook_1)
        forward_net = triangle.forward_net(cash_available)
        backward_net = triangle.backward_net(cash_available)

        true_forward_net = -0.3717563059
        true_backward_net = -41.513473

        assert forward_net == pytest.approx(true_forward_net, abs=1e-5)
        assert backward_net == pytest.approx(true_backward_net, abs=1e-5)

    def test_orderbook_2_net(self, orderbook_2):
        cash_available = 10000
        triangle = TriangleBTCUSDTL1(orderbook_2)

        forward_net = triangle.forward_net(cash_available)
        backward_net = triangle.backward_net(cash_available)

        true_forward_net = 2.538076366
        true_backward_net = -246.013785

        assert forward_net == pytest.approx(true_forward_net, abs=1e-5)
        assert backward_net == pytest.approx(true_backward_net, abs=1e-5)

    def test_orderbook2_forward_trades_10000_cash(self, orderbook_2):
        cash_available = 10000
        triangle = TriangleBTCUSDTL1(orderbook_2, fee=0.002)

        o1, o2, o3 = triangle.get_forward_orders(cash_available)

        true_order_1 = Order(
            instrument_id=BTCCAD_ID,
            side=0,
            quantity=0.0006208205142,
            order_type=ORDER_TYPE_MARKET,
        )
        true_order_2 = Order(
            instrument_id=BTCUSDT_ID,
            side=1,
            quantity=0.0006195788732,
            order_type=ORDER_TYPE_MARKET,
        )
        true_order_3 = Order(
            instrument_id=USDTCAD_ID,
            side=1,
            quantity=34.96,
            order_type=ORDER_TYPE_MARKET,
        )

        # Order 1
        assert o1.instrument_id == true_order_1.instrument_id
        assert o1.side == true_order_1.side
        assert o1.quantity == pytest.approx(true_order_1.quantity, abs=1e-5)
        assert o1.order_type == true_order_1.order_type

        assert o2.instrument_id == true_order_2.instrument_id

        assert o2.side == true_order_2.side
        assert o2.quantity == pytest.approx(true_order_2.quantity, abs=1e-5)
        assert o2.order_type == true_order_2.order_type

        assert o3.instrument_id == true_order_3.instrument_id
        assert o3.side == true_order_3.side
        assert o3.quantity == pytest.approx(true_order_3.quantity, abs=1e-5)
        assert o3.order_type == true_order_3.order_type

    def test_orderbook2_forward_trades_30_cash(self, orderbook_2):
        cash_available = 30
        triangle = TriangleBTCUSDTL1(orderbook_2, fee=0.002)

        o1, o2, o3 = triangle.get_forward_orders(cash_available)

        true_order_1 = Order(
            instrument_id=BTCCAD_ID,
            side=0,
            quantity=0.0004349611949,
            order_type=ORDER_TYPE_MARKET,
        )
        true_order_2 = Order(
            instrument_id=BTCUSDT_ID,
            side=1,
            quantity=0.0004340912725,
            order_type=ORDER_TYPE_MARKET,
        )
        true_order_3 = Order(
            instrument_id=USDTCAD_ID,
            side=1,
            quantity=24.49378367,
            order_type=ORDER_TYPE_MARKET,
        )

        # Order 1
        assert o1.instrument_id == true_order_1.instrument_id
        assert o1.side == true_order_1.side
        assert o1.quantity == pytest.approx(true_order_1.quantity, abs=1e-5)
        assert o1.order_type == true_order_1.order_type

        assert o2.instrument_id == true_order_2.instrument_id

        assert o2.side == true_order_2.side
        assert o2.quantity == pytest.approx(true_order_2.quantity, abs=1e-5)
        assert o2.order_type == true_order_2.order_type

        assert o3.instrument_id == true_order_3.instrument_id
        assert o3.side == true_order_3.side
        assert o3.quantity == pytest.approx(true_order_3.quantity, abs=1e-5)
        assert o3.order_type == true_order_3.order_type

    def test_orderbook3_forward_trades_10000_cash(self, orderbook_3):

        cash_available = 10000
        triangle = TriangleBTCUSDTL1(orderbook_3, fee=0.002)

        o1, o2, o3 = triangle.get_forward_orders(cash_available)

        true_order_1 = Order(
            instrument_id=BTCCAD_ID,
            side=0,
            quantity=0.04929859719,
            order_type=ORDER_TYPE_MARKET,
        )
        true_order_2 = Order(
            instrument_id=BTCUSDT_ID,
            side=1,
            quantity=0.0492,
            order_type=ORDER_TYPE_MARKET,
        )
        true_order_3 = Order(
            instrument_id=USDTCAD_ID,
            side=1,
            quantity=2489.467324,
            order_type=ORDER_TYPE_MARKET,
        )

        # Order 1
        assert o1.instrument_id == true_order_1.instrument_id
        assert o1.side == true_order_1.side
        assert o1.quantity == pytest.approx(true_order_1.quantity, abs=1e-5)
        assert o1.order_type == true_order_1.order_type

        assert o2.instrument_id == true_order_2.instrument_id
        assert o2.side == true_order_2.side
        assert o2.quantity == pytest.approx(true_order_2.quantity, abs=1e-5)
        assert o2.order_type == true_order_2.order_type

        assert o3.instrument_id == true_order_3.instrument_id
        assert o3.side == true_order_3.side
        assert o3.quantity == pytest.approx(true_order_3.quantity, abs=1e-5)
        assert o3.order_type == true_order_3.order_type



