from hermes.exchanges.ndax import (
    NDAXSession,
    create_subscribe_level2_req,
    BTCCAD_ID,
    BTCUSDT_ID,
    USDTCAD_ID,
)
from hermes.orderbook.orderbook import MultiOrderBook
from hermes.strategies.arbitrage.triangle import TriangleBTCUSDTL1
from hermes.trader.trader import NDAXMarketTriangleLogger
import asyncio
import json


async def listen(session, orderbook):
    counter = 0
    req1 = create_subscribe_level2_req(BTCCAD_ID, depth=1)
    req2 = create_subscribe_level2_req(BTCUSDT_ID, depth=1)
    req3 = create_subscribe_level2_req(USDTCAD_ID, depth=1)

    await session.send(req1)
    await session.send(req2)
    await session.send(req3)

    async for message in session.session:

        parsed = json.loads(message)
        message_type = parsed["n"]
        payload = json.loads(json.loads(message)["o"])
        await orderbook.update(payload, snapshot=(message_type == "SubscribeLevel2"))


async def main(username, password):
    session = NDAXSession(username, password, None)

    await session.initialize_session()
    await session.authenticate()

    orderbook = MultiOrderBook(depth=1)
    triangle = TriangleBTCUSDTL1(orderbook)
    trader = NDAXMarketTriangleLogger(
        session, orderbook, triangle, 1500, debug_mode=False
    )

    await asyncio.gather(listen(session, orderbook), trader.run())


if __name__ == "__main__":

    with open("secrets/ndax.json", "r") as sfile:
        data = json.load(sfile)
    asyncio.run(main(data["username"], data["password"]))
