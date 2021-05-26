import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)s| %(message)s")

import websockets
import traceback
import asyncio
import json
from hermes.orderbook.orderbook import MultiOrderBook
from dataclasses import dataclass
import logging
from hermes.strategies.arbitrage.triangle import TriangleBSS

DEMO_URL = "wss://ws.kraken.com"

DEBUG = False

TICKERS = ["XBT/CAD", "ETH/CAD", "XRP/CAD", "ETH/XBT", "XRP/XBT", "XRP/ETH"]
TRIANGLE1 = ["ETH/CAD", "ETH/XBT", "XBT/CAD"]
TRIANGLE2 = ["XRP/CAD", "XRP/XBT", "XBT/CAD"]
TRIANGLE3 = ["XRP/CAD", "XRP/ETH", "ETH/CAD"]

event_subscription = json.dumps(
    {"event": "subscribe", "pair": TICKERS, "subscription": {"name": "book"},}
)


@dataclass
class KrakenL2Update:
    ProductPairCode: str
    Price: float
    Quantity: float
    Side: int


DEPTH = 10


def get_kraken_message_type(payload):
    if isinstance(payload, list):
        # L2 Update or Snapshot
        if "book" in payload[-2]:
            if True:  # TODO: detect snapshot vs l2 update
                return "snapshot"
            else:
                return "l2update"
    elif isinstance(payload, list):
        if payload.get("event"):
            return payload["event"]


async def print_orderbook_at_interval(orderbook, interval=1200):
    await asyncio.sleep(10)  # wait for a bit to initialize
    while True:
        print("Printing Orderbook")
        orderbook.print_orderbook()
        await asyncio.sleep(interval)


async def test(orderbook):
    session = await websockets.connect(DEMO_URL)
    await session.recv()

    try:
        await session.send(event_subscription)

        # Order confirmations
        await session.recv()
        await session.recv()
        await session.recv()

        snapshot_received = {ticker: False for ticker in TICKERS}
        triangle1 = TriangleBSS(orderbook, instrument_ids=TRIANGLE1, fee=0.0022)
        triangle2 = TriangleBSS(orderbook, instrument_ids=TRIANGLE2, fee=0.0022)
        triangle3 = TriangleBSS(orderbook, instrument_ids=TRIANGLE3, fee=0.0022)

        async for raw_message in session:
            try:
                message = json.loads(raw_message)

                if not isinstance(message, list):
                    continue

                if not snapshot_received[message[-1]]:
                    await orderbook.snapshot(message)
                    snapshot_received[message[-1]] = True
                else:
                    await orderbook.update(message)

                for triangle in [triangle1, triangle2, triangle3]:
                    if DEBUG:
                        print(f'Forward: {triangle.forward()}')
                        print(f'Backward: {triangle.backward()}')
                    forward_val = triangle.forward_net(100)
                    backward_val = triangle.backward_net(100)


                    if forward_val > 0.1:
                        print(triangle.instrument_ids)
                        print("Forward Value > 10 cents detected")
                        print("--")
                        print(f"Val: {forward_val}")
                        orderbook.print_orderbook()

                    if backward_val > 0.1:
                        print(triangle.instrument_ids)
                        print("Backward Value > 10 cents detected")
                        print("--")
                        print(f"Val: {backward_val}")
                        orderbook.print_orderbook()
            except Exception as e:
                print(e)

    except Exception as e:
        await session.close()


class KrakenOrderBook(MultiOrderBook):
    async def snapshot(self, payload):
        try:
            _id, book, _, instrument = payload
        except Exception as e:
            print(payload)
            return

        for ask in book["as"]:
            l2update = KrakenL2Update(instrument, *ask[:2], Side=1)
            await self.handle_update(l2update)

        for bid in book["bs"]:
            l2update = KrakenL2Update(instrument, *bid[:2], Side=0)
            await self.handle_update(l2update)

    async def update(self, payload):
        if len(payload) == 4:
            _id, book, _, instrument = payload
            ask_book = book.get("a", [])
            bid_book = book.get("b", [])

        elif len(payload) == 5:
            _id, ask_book, bid_book, _, instrument = payload
            ask_book = ask_book["a"]
            bid_book = bid_book["b"]
        else:
            raise ValueError(f"What the fuck is this: {payload}")

        for ask in ask_book:
            l2update = KrakenL2Update(instrument, *ask[:2], Side=1)
            await self.handle_update(l2update)

        for bid in bid_book:
            l2update = KrakenL2Update(instrument, *bid[:2], Side=0)
            await self.handle_update(l2update)

    async def handle_update(self, update: KrakenL2Update):
        if update.Side == 0:
            book_to_update = self.book[update.ProductPairCode].bid
        else:
            book_to_update = self.book[update.ProductPairCode].ask

        quantity = float(update.Quantity)
        price = float(update.Price)
        if quantity == 0:  # deletion
            try:
                book_to_update.pop(price)
            except KeyError:
                print("why is there a key error")
        else:
            book_to_update[price] = quantity


async def gather_all_tasks(orderbook):
    await asyncio.gather(test(orderbook), print_orderbook_at_interval(orderbook))


if __name__ == "__main__":
    orderbook = KrakenOrderBook(instrument_keys=TICKERS, depth=DEPTH)
    asyncio.run(gather_all_tasks(orderbook))
