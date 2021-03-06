import asyncio
from asyncio import Condition
from dataclasses import dataclass
from sortedcontainers import SortedDict, SortedItemsView
from collections import namedtuple
import logging

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
    def __init__(self, depth, use_depth_limiter=True):
        self.depth = depth

        if use_depth_limiter:
            self.bid = BidSide(depth)
            self.ask = AskSide(depth)
        else:
            self.bid = SortedDict()
            self.ask = SortedDict()

        self.bid_depth_view = self.bid.items()
        self.ask_depth_view = self.ask.items()

        self.ask_prices = self.ask.keys()
        self.bid_prices = self.bid.keys()

    def get_bids(self):
        return self.bid_depth_view[: -self.depth - 1 : -1]

    def get_asks(self):
        return self.ask_depth_view[: self.depth]

    def get_ask_prices(self):
        return self.ask_prices[: self.depth]

    def get_bid_prices(self):
        return self.bid_prices[: -self.depth - 1 : -1]


class MultiOrderBook:
    def __init__(self, instrument_keys=(1, 80, 82), depth=5, use_depth_limiter=True):
        self.book = {}
        self.initialize_book(instrument_keys, depth, use_depth_limiter=use_depth_limiter)
        self.depth = depth
        self.logger = logging.getLogger(self.__class__.__name__)


    def initialize_book(self, instrument_ids, depth, use_depth_limiter=True):
        for _id in instrument_ids:
            self.book[_id] = OrderBook(depth, use_depth_limiter=use_depth_limiter)

    def __getitem__(self, key):
        return self.book[key]

    def __setitem__(self, key, value):
        self.book[key] = value

    async def update(self, payload):
        raise NotImplementedError("Please use a child class")

    def print_orderbook(self, depth=1):
        for k, v in self.book.items():
            try:
                self.logger.info(f"{k}: ASK:{v.get_asks()[:depth]}")
                self.logger.info(f"{k}: BID:{v.get_bids()[:depth]}")
            except IndexError:
                pass

    def handle_update(self, update):
        if update.Side == 0:
            book_to_update = self.book[update.ProductPairCode].bid
        elif update.Side == 1:
            book_to_update = self.book[update.ProductPairCode].ask
        else:
            print("What the fuck is this")

        price = update.Price
        quantity = update.Quantity
        if update.ActionType < 2:
            book_to_update[price] = quantity
        else:
            try:  # still not sure why we get delete orders for stuff not in our sights
                book_to_update.pop(price)
            except KeyError as e:
                pass  # Happens because delete orders are sent irrespective of depth level

    def clear(self):
        for book in self.book.values():
            book.ask.clear()
            book.bid.clear()


class NDAXOrderbook(MultiOrderBook):
    async def update(self, payload):
        # for update in sorted(payload, key=lambda x: x[2]): # sort by action date time
        for update in payload:
            self.handle_update(L2Update(*update))

