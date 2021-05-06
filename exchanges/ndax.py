import asyncio
import json
import websockets
import requests
import random
from enum import Enum
import logging
import uuid
from collections import namedtuple

SECRET_PATH = "secrets/ndax.json"
NDAX_URL = "wss://api.ndax.io"

BTCCAD_ID = 1
BTCUSDT_ID = 82
USDTCAT_ID = 80


logging.basicConfig(level=logging.INFO)


MESSAGE_TYPES = {
    "REQUEST": 0,
    "REPLY": 1,
    "SUBSCRIBE": 2,
    "EVENT": 3,
    "UNSUB": 4,
    "ERROR": 5,
}

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


with open(SECRET_PATH, "r") as secret_file:
    data = json.load(secret_file)

def parse_l2update(response):
        payload = json.loads(json.loads(response)["o"])
        return L2Update(payload)



async def test():
    response = None
    session = NDAXSession(data["username"], data["password"], data["secret"])
    await session.initialize_session()
    try:
        await session.authenticate()
        # req = create_request(0, 'GetInstruments', {'OMSId': 1})

        req = create_subscribe_level2_req(BTCCAD_ID, depth=1)
        await session.send(req)
        response = await session.recv()

        initial_response = parse_l2update(response)

        async for message in session.session:
            print('----')
            print('BID: ')
            payload = json.loads(json.loads(message)["o"])
            update = L2Update(payload)
            print(payload)

    # await session.close()
    # return response

    # async for message in session.session:
    #     x = json.loads(message)
    #     print(x)
    except Exception as e:
        print(e)
    finally:
        await session.close()
        return response


if __name__ == "__main__":
    asyncio.run(test())
