import websockets
import traceback
import asyncio
import json
from hermes.orderbook.orderbook import MultiOrderBook
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)

DEMO_URL = "wss://ws.kraken.com"

event_subscription = json.dumps(
    {
        "event": "subscribe",
        "pair": ["XBT/CAD", "ETH/XBT", "ETH/CAD"],
        "subscription": {"name": "book"},
    }
)


@dataclass
class KrakenL2Update:
    ProductPairCode: str
    Price: float
    Quantity: float
    Side: int


DEPTH=10
async def print_orderbook_at_interval(orderbook, interval=5):
    while True:
        await asyncio.sleep(interval)
        print('Printing Orderbook')
        orderbook.print_orderbook()


async def test(orderbook):
    session = await websockets.connect(DEMO_URL)
    await session.recv()

    try:
        await session.send(event_subscription)

        # Order confirmations
        await session.recv()
        await session.recv()
        await session.recv()

        snapshot_received = {"XBT/CAD": False, "ETH/XBT": False, "ETH/CAD": False}

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

            except Exception as e:
                traceback.print_exc()

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
        try:
            _id, book, _, instrument = payload
        except Exception as e:
            print(e)
            print(payload)
            print(len(payload))
            return
        for ask in book.get("a", []):
            l2update = KrakenL2Update(instrument, *ask[:2], Side=1)
            await self.handle_update(l2update)

        for bid in book.get("b", []):
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
                pass
        else:
            book_to_update[price] = quantity

async def gather_all_tasks(orderbook):
    await asyncio.gather(test(orderbook), print_orderbook_at_interval(orderbook))


if __name__ == "__main__":
    orderbook = KrakenOrderBook(instrument_keys=["XBT/CAD", "ETH/XBT", "ETH/CAD"], depth=DEPTH, use_depth_limiter=False)
    asyncio.run(gather_all_tasks(orderbook))
