import pytest

from hermes.strategies.arbitrage.triangle import TriangleBTCUSDTL1
from hermes.orderbook.orderbook import  MultiOrderBook, OrderBook
from hermes.exchanges.ndax import BTCCAD_ID, BTCUSDT_ID, USDTCAD_ID

sample_bids = []
sample_asks = []

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

@pytest.fixture()
def orderbook_forward_arb_btccad_ask_bottleneck():
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
    pass

@pytest.fixture()
def orderbook_backward_arb_btccad_bid_bottleneck():
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
    pass

@pytest.fixture()
def orderbook_forward_arb_btcusdt_bid_bottleneck():
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
    pass

@pytest.fixture()
def orderbook_backward_arb_btcusdt_ask_bottleneck():
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
    pass

@pytest.fixture()
def orderbook_forward_arb_usdtcad_bottleneck():
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
    pass

@pytest.fixture()
def orderbook_backward_arb_usdtcad_ask_bottleneck():
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
        assert backward ==pytest.approx(backward_value, abs=1e-8)

    def test_orderbook_1_net(self, orderbook_1):
        cash_available = 10000 # Not the bottleneck
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
