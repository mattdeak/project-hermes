import asyncio
import json
import websockets
import requests
import random
from enum import Enum
import logging
import uuid
from collections import namedtuple
import datetime
import traceback

SECRET_PATH = "secrets/ndax.json"
NDAX_URL = "wss://api.ndax.io"

BTCCAD_ID = 1
BTCUSDT_ID = 82
USDTCAD_ID = 80

FEE = 0.002

logging.basicConfig(level=logging.INFO)


MESSAGE_TYPES = {
    "REQUEST": 0,
    "REPLY": 1,
    "SUBSCRIBE": 2,
    "EVENT": 3,
    "UNSUB": 4,
    "ERROR": 5,
}

ACTION_TYPES = ("NEW", "UPDATE", "DELETE")

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


class MFAError(Exception):
    pass


class AuthError(Exception):
    pass


def create_request(message_type: int, function_name: str, payload: dict) -> str:
    i = random.randint(1, 10000)  # TODO thjis should be different/random
    return json.dumps(
        {"m": message_type, "i": i, "n": function_name, "o": json.dumps(payload)}
    )


def create_authentication_request(username, password):
    return create_request(
        MESSAGE_TYPES["REQUEST"],
        "AuthenticateUser",
        {"username": username, "password": password},
    )


def create_subscription_message(function: str, payload: dict):
    return create_request(MESSAGE_TYPES["SUBSCRIBE"], function, payload)


def create_subscribe_level1_req(instrument_id: int) -> str:
    payload = {"OMSId": 1, "InstrumentId": instrument_id}
    return create_request(MESSAGE_TYPES["REQUEST"], "SubscribeLevel1", payload)


def create_subscribe_level2_req(instrument_id: int, depth=5) -> str:
    payload = {"OMSId": 1, "InstrumentId": instrument_id, "Depth": depth}
    return create_request(MESSAGE_TYPES["REQUEST"], "SubscribeLevel2", payload)


class NDAXAuth:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_authenticate_user_request(self):
        return create_request(
            MESSAGE_TYPES["REQUEST"],
            "AuthenticateUser",
            {"username": self.username, "password": self.password},
        )

    def get_authenticate_2fa_request(self, code):
        return create_request(
            MESSAGE_TYPES["REQUEST"], "Authenticate2FA", {"code": code}
        )


class NDAXSession:
    def __init__(self, username, password, apikey):
        self.auth_manager = NDAXAuth(username, password)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize_session(self):
        self.session = await websockets.connect(NDAX_URL)

    async def close(self):
        await self.session.close()

    async def send(self, message):
        return await self.session.send(message)

    async def recv(self):
        return await self.session.recv()

    async def _send_and_receive(self, req):
        await self.session.send(req)
        response = await self.session.recv()
        return json.loads(response)

    async def authenticate(self):
        self.logger.info("Authenticating...")
        auth_req = self.auth_manager.get_authenticate_user_request()

        self.logger.debug(f"Sending Authentication Request: {auth_req}")
        response = await self._send_and_receive(auth_req)
        payload = json.loads(response["o"])

        self.logger.debug("Sending MFA Authentication Request")
        if not payload["Authenticated"]:
            raise AuthError(f"Authentication refused. Returned message: {payload}")

        if payload["Authenticated"] and payload["Requires2FA"]:
            self.session_token = await self._authenticate_mfa()
        else:
            self.session_token = payload["SessionToken"]

    async def _authenticate_mfa(self):
        mfa_code = input("Enter MFA: >")
        req = self.auth_manager.get_authenticate_2fa_request(mfa_code)
        response = await self._send_and_receive(req)
        self.logger.debug(f"Response: {response}")
        payload = json.loads(response["o"])

        if payload["Authenticated"]:
            return payload["SessionToken"]
        else:
            raise MFAError(f"MFA Failed: {payload}")

    async def subscribe(self, function, payload):
        pass

    async def listen(self):
        async with websockets.connect(uri) as websocket:
            response = None
        while True:
            pass

    async def send_order(self):
        pass


with open(SECRET_PATH, "r") as secret_file:
    data = json.load(secret_file)


def parse_l2update(response):
    payload = json.loads(json.loads(response)["o"])
    return L2Update(*payload)


def triangle_forward(
    btc_cad_ask,
    btc_usdt_bid,
    usdt_cad_bid,
    btc_cad_ask_qty=None,
    btc_usdt_bid_qty=None,
    usdt_cad_bid_qty=None,
    return_amount=True,
):
    if not (btc_cad_ask and btc_usdt_bid and usdt_cad_bid):
        return None, None

    if return_amount:
        t1_effective_quantity = btc_cad_ask_qty * btc_cad_ask
        t2_effective_quantity = btc_usdt_bid_qty * btc_cad_ask / 0.998
        t3_effective_quantity = usdt_cad_bid_qty * usdt_cad_bid / (0.998 ** 2)

        amount = min(
            t1_effective_quantity, t2_effective_quantity, t3_effective_quantity
        )
        return 1 / (btc_cad_ask / btc_usdt_bid / usdt_cad_bid), amount

    if btc_cad_ask and btc_usdt_bid and usdt_cad_bid:
        return 1 / (btc_cad_ask / btc_usdt_bid / usdt_cad_bid), None


def triangle_backward(
    usdt_cad_ask,
    btc_usdt_ask,
    btc_cad_bid,
    usdt_cad_ask_qty=None,
    btc_usdt_ask_qty=None,
    btc_cad_bid_qty=None,
    return_amount=True,
):
    if not (usdt_cad_ask and btc_usdt_ask and btc_cad_bid):
        return None, None
    if return_amount:
        t1_effective_quantity = usdt_cad_ask * usdt_cad_ask_qty
        t2_effective_quantity = btc_usdt_ask_qty * btc_usdt_ask / 0.998
        t3_effective_quantity = btc_cad_bid_qty * btc_cad_bid / (0.998 ** 2)

        amount = min(
            t1_effective_quantity, t2_effective_quantity, t3_effective_quantity
        )
        return 1 / usdt_cad_ask / btc_usdt_ask * btc_cad_bid, amount

    if usdt_cad_ask and btc_usdt_ask and btc_cad_bid:
        return 1 / usdt_cad_ask / btc_usdt_ask * btc_cad_bid



def lazy_triangle_forward(
    btc_cad_ask,
    btc_usdt_ask,
    usdt_cad_bid,
    btc_cad_ask_qty=None,
    btc_usdt_ask_qty=None,
    usdt_cad_bid_qty=None,
    return_amount=True,
):
    if not (btc_cad_ask and btc_usdt_ask and usdt_cad_bid):
        return None, None

    if return_amount:
        t1_effective_quantity = btc_cad_ask_qty * btc_cad_ask
        t2_effective_quantity = btc_usdt_ask_qty * btc_cad_ask / 0.998
        t3_effective_quantity = usdt_cad_bid_qty * usdt_cad_bid / (0.998 ** 2)

        amount = min(
            t1_effective_quantity, t2_effective_quantity, t3_effective_quantity
        )
        return 1 / (btc_cad_ask / btc_usdt_ask / usdt_cad_bid), amount


def triangle_backward(
    usdt_cad_ask,
    btc_usdt_ask,
    btc_cad_bid,
    usdt_cad_ask_qty=None,
    btc_usdt_ask_qty=None,
    btc_cad_bid_qty=None,
    return_amount=True,
):
    if not (usdt_cad_ask and btc_usdt_ask and btc_cad_bid):
        return None, None
    if return_amount:
        t1_effective_quantity = usdt_cad_ask * usdt_cad_ask_qty
        t2_effective_quantity = btc_usdt_ask_qty * btc_usdt_ask / 0.998
        t3_effective_quantity = btc_cad_bid_qty * btc_cad_bid / (0.998 ** 2)

        amount = min(
            t1_effective_quantity, t2_effective_quantity, t3_effective_quantity
        )
        return 1 / usdt_cad_ask / btc_usdt_ask * btc_cad_bid, amount

    if usdt_cad_ask and btc_usdt_ask and btc_cad_bid:
        return 1 / usdt_cad_ask / btc_usdt_ask * btc_cad_bid

def triangle_backward(
    usdt_cad_ask,
    btc_usdt_ask,
    btc_cad_bid,
    usdt_cad_ask_qty=None,
    btc_usdt_ask_qty=None,
    btc_cad_bid_qty=None,
    return_amount=True,
):
    if not (usdt_cad_ask and btc_usdt_ask and btc_cad_bid):
        return None, None
    if return_amount:
        t1_effective_quantity = usdt_cad_ask * usdt_cad_ask_qty
        t2_effective_quantity = btc_usdt_ask_qty * btc_usdt_ask / 0.998
        t3_effective_quantity = btc_cad_bid_qty * btc_cad_bid / (0.998 ** 2)

        amount = min(
            t1_effective_quantity, t2_effective_quantity, t3_effective_quantity
        )
        return 1 / usdt_cad_ask / btc_usdt_ask * btc_cad_bid, amount

    if usdt_cad_ask and btc_usdt_ask and btc_cad_bid:
        return 1 / usdt_cad_ask / btc_usdt_ask * btc_cad_bid


async def test():
    response = None
    session = NDAXSession(data["username"], data["password"], data["secret"])
    await session.initialize_session()
    try:
        await session.authenticate()
        # req = create_request(0, 'GetInstruments', {'OMSId': 1})

        req1 = create_subscribe_level2_req(BTCCAD_ID, depth=1)
        req2 = create_subscribe_level2_req(BTCUSDT_ID, depth=1)
        req3 = create_subscribe_level2_req(USDTCAD_ID, depth=1)
        await session.send(req1)
        await session.send(req2)
        await session.send(req3)

        # TODO: Refactor into class or data structure
        btc_cad_ask = None
        btc_cad_ask_qty = None

        btc_cad_bid = None
        btc_cad_bid_qty = None

        btc_usdt_ask = None
        btc_usdt_ask_qty = None

        btc_usdt_bid = None
        btc_usdt_bid_qty = None

        usdt_cad_ask = None
        usdt_cad_ask_qty = None

        usdt_cad_bid = None
        usdt_cad_bid_qty = None

        last_update_time = None

        print("Running...")
        async for message in session.session:
            payload = json.loads(json.loads(message)["o"])
            updates = [L2Update(*update) for update in payload]
            for update in updates:
                action_type = ACTION_TYPES[update.ActionType]

                if action_type in ["NEW", "UPDATE"]:
                    if update.ProductPairCode == BTCCAD_ID:
                        if update.Side == 1:
                            btc_cad_ask = update.Price
                            btc_cad_ask_qty = update.Quantity
                        else:
                            btc_cad_bid = update.Price
                            btc_cad_bid_qty = update.Quantity

                    elif update.ProductPairCode == USDTCAD_ID:
                        if update.Side == 1:
                            usdt_cad_ask = update.Price
                            usdt_cad_ask_qty = update.Quantity
                        else:
                            usdt_cad_bid = update.Price
                            usdt_cad_bid_qty = update.Quantity
                    else:
                        if update.Side == 1:
                            btc_usdt_ask = update.Price
                            btc_usdt_ask_qty = update.Quantity
                        else:
                            btc_usdt_bid = update.Price
                            btc_usdt_bid_qty = update.Quantity
                else:
                    continue

                last_update_time = datetime.datetime.fromtimestamp(
                    update.ActionDateTime / 1000
                )
                triangle_forward_val, forward_amount = triangle_forward(
                    btc_cad_ask,
                    btc_usdt_bid,
                    usdt_cad_bid,
                    btc_cad_ask_qty=btc_cad_ask_qty,
                    btc_usdt_bid_qty=btc_usdt_bid_qty,
                    usdt_cad_bid_qty=usdt_cad_bid_qty,
                    return_amount=True,
                )

                lazy_triangle_forward_val, lazy_forward_amount = triangle_forward(
                    btc_cad_ask,
                    btc_usdt_ask,
                    usdt_cad_bid,
                    btc_cad_ask_qty=btc_cad_ask_qty,
                    btc_usdt_bid_qty=btc_usdt_ask_qty,
                    usdt_cad_bid_qty=usdt_cad_bid_qty,
                    return_amount=True,
                )

                triangle_backward_val, backward_amount = triangle_backward(
                    usdt_cad_ask,
                    btc_usdt_ask,
                    btc_cad_bid,
                    usdt_cad_ask_qty=usdt_cad_ask_qty,
                    btc_usdt_ask_qty=btc_usdt_ask_qty,
                    btc_cad_bid_qty=btc_cad_bid_qty,
                    return_amount=True,
                )

                if not (triangle_forward_val and triangle_backward_val):
                    continue

                adjusted_forward = (
                    triangle_forward_val * (1 - FEE) ** 3 if triangle_forward_val else 0
                )
                adjusted_backward = (
                    triangle_backward_val * (1 - FEE) ** 3
                    if triangle_backward_val
                    else 0
                )

                lazy_adjusted_forward = (
                    lazy_triangle_forward_val * (1 - FEE) ** 3 if lazy_triangle_forward_val else 0
                )

                expected_forward_net = (adjusted_forward - 1) * forward_amount
                expected_lazy_forward_net = (lazy_adjusted_forward - 1) * lazy_forward_amount
                expected_backward_net = (adjusted_backward - 1) * backward_amount

                print(f'Forward: {expected_forward_net}')
                print(f'Lazy Forward: {expected_lazy_forward_net}')
                print(f'Backward: {expected_backward_net}')
                print('------------------------------')

                if adjusted_backward > 1 or adjusted_forward > 1 or lazy_adjusted_forward > 1:
                    if lazy_adjusted_forward > 1:

                        print("----")
                        print(
                            f"Lazy Forward Opportunity Detected at {last_update_time}: {action_type}"
                        )
                        print(
                            f"Lazy Forward: {lazy_adjusted_forward}, Tradable L1 {lazy_forward_amount}, Expected Profit at 100% capture: {expected_lazy_forward_net}"
                        )
                        print(f"Prices: {btc_cad_ask}, {btc_usdt_ask}, {usdt_cad_bid}")
                        print(
                            f"Quantities: {btc_cad_ask_qty}, {btc_usdt_ask_qty}, {usdt_cad_bid_qty}"
                        )
                        print("---")

                    if adjusted_forward > 1:

                        print("----")
                        print(
                            f"Forward Opportunity Detected at {last_update_time}: {action_type}"
                        )
                        print(
                            f"Forward: {adjusted_forward}, Tradable L1 {forward_amount}, Expected Profit at 100% capture: {expected_forward_net}"
                        )
                        print(f"Prices: {btc_cad_ask}, {btc_usdt_bid}, {usdt_cad_bid}")
                        print(
                            f"Quantities: {btc_cad_ask_qty}, {btc_usdt_bid_qty}, {usdt_cad_bid_qty}"
                        )
                        print("---")
                    if adjusted_backward > 1:

                        print(
                            f"Backward Opportunity Detected at {last_update_time}: {action_type}"
                        )
                        print(
                            f"Backward: {adjusted_backward}, Tradable L1 {backward_amount}, Expected Profit at 100% capture: {expected_backward_net}"
                        )
                        print(f"Prices: {btc_cad_bid}, {btc_usdt_ask}, {usdt_cad_ask}")
                        print(
                            f"Quantities: {btc_cad_bid_qty}, {btc_usdt_ask_qty}, {usdt_cad_ask_qty}"
                        )
                        print("---")

    # await session.close()
    # return response

    # async for message in session.session:
    #     x = json.loads(message)
    #     print(x)
    except Exception as e:
        print(e)
        traceback.print_exc()
    finally:
        await session.close()
        return response


if __name__ == "__main__":
    asyncio.run(test())
