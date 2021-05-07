import logging
from collections import namedtuple

Instrument = namedtuple("Instrument", ["bid", "ask"])


class TriangleResponse:
    def __init__(self):
        pass


class TriangleBTCUSDT:
    def __init__(
        self, btc_cad, btc_usdt, usdt_cad, fee=0.002,  # Base to X. Eg BTC_CAD  # 0.2%
    ):
        self.fee_per_trade = fee_per_trade

        self.btc_cad = btc_cad
        self.btc_usdt = btc_usdt
        self.usdt_cad = usdt_cad

        self.forward_method = self._create_forward_method(None)
        self.backward_method = self._create_backward_method(None)

    # TODO: The quantities need to be different. I need to get the effective trade in the
    # target currency.
    #   Fine the minimum price, get appropriate amounts for each currency. Need them to issue trades.
    def forward(self):
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

    def backward(self):
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


class TriangleTrader:
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
