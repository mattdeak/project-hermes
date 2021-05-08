import pytest

from hermes.strategies.arbitrage.triangle import Instrument, OrderbookLine
from hermes.strategies.arbitrage.triangle import TriangleBTCUSDT


dummy_side = OrderbookLine(price=0, quantity=0)


@pytest.fixture
def forward_trades_cash_bottleneck():

    btc_cad = Instrument(
        ask=OrderbookLine(price=69622.22, quantity=0.034), bid=dummy_side
    )

    btc_usdt = Instrument(bid=OrderbookLine(price=56945.6, quantity=2), ask=dummy_side)
    usdt_cad = Instrument(bid=OrderbookLine(price=1.23, quantity=1000), ask=dummy_side)

    return [btc_cad, btc_usdt, usdt_cad]


@pytest.fixture
def forward_trades_q1_bottleneck():

    # TODO: Alter
    btc_cad = Instrument(
        ask=OrderbookLine(price=69622.22, quantity=0.034), bid=dummy_side
    )
    btc_usdt = Instrument(bid=OrderbookLine(price=56945.6, quantity=2), ask=dummy_side)
    usdt_cad = Instrument(bid=OrderbookLine(price=1.23, quantity=1000), ask=dummy_side)

    return [btc_cad, btc_usdt, usdt_cad]


@pytest.fixture
def forward_trades_q2_bottleneck():

    # TODO: Alter
    btc_cad = Instrument(
        ask=OrderbookLine(price=69622.22, quantity=0.034), bid=dummy_side
    )
    btc_usdt = Instrument(bid=OrderbookLine(price=56945.6, quantity=2), ask=dummy_side)
    usdt_cad = Instrument(bid=OrderbookLine(price=1.23, quantity=1000), ask=dummy_side)

    return [btc_cad, btc_usdt, usdt_cad]


@pytest.fixture
def forwad_trades_q3_bottleneck():

    # TODO: Alter
    btc_cad = Instrument(
        ask=OrderbookLine(price=69622.22, quantity=0.034), bid=dummy_side
    )
    btc_usdt = Instrument(bid=OrderbookLine(price=56945.6, quantity=2), ask=dummy_side)
    usdt_cad = Instrument(bid=OrderbookLine(price=1.23, quantity=1000), ask=dummy_side)

    return [btc_cad, btc_usdt, usdt_cad]


def test_triangle_value_forward(forward_trades_cash_bottleneck):
    btc_cad, btc_usdt, usdt_cad = forward_trades_cash_bottleneck

    triangle = TriangleBTCUSDT(btc_cad, btc_usdt, usdt_cad)

    value = triangle.forward()
    true_value = 1.000020818

    assert pytest.approx(value, true_value, abs=1e-8)


def test_triangle_value_backward(forward_trades_1):
    pass


def test_triangle_trades_forward(forward_trades_q1_bottleneck):
    btc_cad, btc_usdt, usdt_cad = forward_trades_q1_bottleneck

    triangle = TriangleBTCUSDT(btc_cad, btc_usdt, usdt_cad)
    cash_available = 1000
    orders = triangle.get_forward_orders(cash_available)

    true_orders = [0.01436323059, 0.01433450413, 814.6543644]

    for order, true_order in zip(orders, true_orders):
        assert pytest.approx(order, true_order, abs=1e-9)


def test_triangle_trades_backward(forward_trades_1):
    pass
