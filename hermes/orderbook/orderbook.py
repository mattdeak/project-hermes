import asyncio
from asyncio import Condition
from dataclasses import dataclass
from sortedcontainers import SortedDict, SortedItemsView
from collections import namedtuple

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

class OrderBook:

    def __init__(self, depth):
        self.depth = depth
        self.bid = SortedDict()
        self.ask = SortedDict()

        self.bid_depth_view = self.bid.items()
        self.ask_depth_view = self.ask.items()
    
    def get_bids(self):
        return self.bid_depth_view[-self.depth:]

    def get_asks(self):
        return self.ask_depth_view[:self.depth]
        

class NDAXOrderBook:
    def __init__(self, instrument_ids=(1, 80, 82), depth=5):
        self.updated = Condition()

        self.book = {}
        self.initialize_book(instrument_ids, depth)
        self.depth = depth

    def initialize_book(self, instrument_ids, depth):
        for _id in instrument_ids:
            self.book[_id] = OrderBook(depth)

    def __getitem__(self, key):
        return self.book[key]

    async def update(self, payload):
        async with self.updated:
            print(len(payload))

            updates = [L2Update(*update) for update in payload]
            for update in updates:
                self.handle_update(update)

            self.updated.notify_all()

    def handle_update(self, update):
        if update.Side == 0:
            book_to_update = self.book[update.ProductPairCode].bid
        else:
            book_to_update = self.book[update.ProductPairCode].ask

        price = update.Price
        quantity = update.Quantity
        if update.ActionType < 2:
            book_to_update[price] = quantity
        else:
            try: # still not sure why we get delete orders for stuff not in our sights
                book_to_update.pop(price)
            except KeyError as e:
                print(f'Price not found {price}')

        # await self.is_updated.clear()
