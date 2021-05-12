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


class AskSide(SortedDict):

    def __init__(self, depth, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.depth = depth

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.depth:
            self.popitem(-1)

class BidSide(SortedDict):
    def __init__(self, depth, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.depth = depth

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.depth:
            self.popitem(0)

class OrderBook:
    def __init__(self, depth):
        self.depth = depth
        self.bid = BidSide(depth)
        self.ask = AskSide(depth)

        self.bid_depth_view = self.bid.items()
        self.ask_depth_view = self.ask.items()

        self.ask_prices = self.ask.keys()
        self.bid_prices = self.bid.keys()
    
    def get_bids(self):
        return self.bid_depth_view[:-self.depth-1:-1]

    def get_asks(self):
        return self.ask_depth_view[:self.depth]

    def get_ask_prices(self):
        return self.ask_prices[:self.depth]

    def get_bid_prices(self):
        return self.bid_prices[:-self.depth-1:-1]
        

class MultiOrderBook:
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

    def __setitem__(self, key, value):
        self.book[key] = value

    async def update(self, payload):
        async with self.updated:
            updates = [L2Update(*update) for update in payload]
            for update in updates:
                self.handle_update(update)

            self.updated.notify_all()

    def handle_update(self, update):
        if update.Side == 0:
            book_to_update = self.book[update.ProductPairCode].bid
        elif update.Side == 1:
            book_to_update = self.book[update.ProductPairCode].ask
        else:
            print('What the fuck is this')

        price = update.Price
        quantity = update.Quantity
        if update.ActionType < 2:
            book_to_update[price] = quantity
        else:
            try: # still not sure why we get delete orders for stuff not in our sights
                book_to_update.pop(price)
            except KeyError as e:
                pass # Happens because delete orders are sent irrespective of depth level
