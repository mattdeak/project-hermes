import asyncio
import json
import websockets
import random
from enum import Enum
import logging
from collections import namedtuple
import datetime
import traceback
from hermes.utils.authorization import create_NDAX_signature

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
    def __init__(self, user_id, api_key, secret):
        self.user_id = user_id
        self.api_key = api_key
        self.secret = secret

    def get_authenticate_user_request(self):
        signature, nonce = create_NDAX_signature(
            self.user_id, self.api_key, self.secret
        )

        payload = {
            "APIKey": self.api_key,
            "Signature": signature,
            "UserId": str(self.user_id),
            "Nonce": str(nonce),
        }
        request = create_request(0, "AuthenticateUser", payload=payload)
        return request

    def get_authenticate_2fa_request(self, code):
        return create_request(
            MESSAGE_TYPES["REQUEST"], "Authenticate2FA", {"code": code}
        )



class NDAXSession:
    def __init__(self, user_id, apikey, secret, rate_limit=50):
        self.auth_manager = NDAXAuth(user_id, apikey, secret)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rate_limit=rate_limit
        self.call_counter = 0


    async def initialize_session(self):
        self.session = await websockets.connect(NDAX_URL)

    async def close(self):
        await self.session.close()

    async def send(self, message):

        await self.session.send(message)
        asyncio.create_task(self._increment_and_decrement_call_counter())

    @property
    def limited(self):
        return self.call_counter > self.rate_limit

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

    async def _wait_one_minute_then_clear_rate_limit(self):
        await asyncio.sleep(60)
        self.limited = False

    async def _increment_and_decrement_call_counter(self, interval=60):
        # Debug
        print('incrementing')
        self.call_counter += 1
        await asyncio.sleep(interval)
        print('decrementing')
        self.call_counter -= 1


