import asyncio
from asyncio import Event
from dataclasses import dataclass
from collections import namedtuple, defaultdict

L2Update = namedtuple(
    "L2Update",
    [
        "MDUpdateId",
        "AccountId",
        "ActionDateTime",
        "ActionType",
        "LastTradePrice",
        "OrderId",
        "Price",
        "ProductPairCode",
        "Quantity",
        "Side",
    ],
)


@dataclass
class OrderbookLine:
    price: float
    quantity: float


@dataclass
class Instrument:
    bid: OrderbookLine
    ask: OrderbookLine


DUMMY_LINE = Instrument(bid=OrderbookLine(0, 0), ask=OrderbookLine(0, 0))


class NDAXOrderBook:
    def __init__(self, instrument_ids=(1, 80, 82), depth=5):
        self.is_updated = Event()

        self.book = defaultdict(list)
        self.initialize_book(instrument_ids, depth)
        self.depth = depth

    def initialize_book(self, instrument_ids, depth):
        for _id in instrument_ids:
            self.book[_id] = [DUMMY_LINE for i in range(depth)]

    async def update(self, payload):
        print(len(payload))

        updates = [L2Update(*update) for update in payload]
        

        for i, update in enumerate(updates):
            action_type = update.ActionType
            action_time = update.ActionDateTime
            instrument_id = update.ProductPairCode

            if action_type < 2:  # still not sure how to handle deletes
                line = OrderbookLine(price=update.Price, quantity=update.Quantity)
                if update.Side == 1:
                    self.book[instrument_id][i - self.depth].ask.price = update.Price
                    self.book[instrument_id][i - self.depth].ask.quantity = update.Quantity
                else:
                    self.book[instrument_id][i].bid.price = update.Price
                    self.book[instrument_id][i].bid.quantity = update.Quantity

        await self.is_updated.set()
        await self.is_updated.clear()
