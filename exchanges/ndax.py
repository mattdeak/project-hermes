import asyncio
import json
import websockets
import requests
from enum import Enum
import uuid

SECRET_PATH = "secrets/ndax.json"
NDAX_URL = "wss://api.ndax.io"


MESSAGE_TYPES = {
    "REQUEST": 0,
    "REPLY": 1,
    "SUBSCRIBE": 2,
    "EVENT": 3,
    "UNSUB": 4,
    "ERROR": 5,
}


class MFAError(Exception):
    pass


class AuthError(Exception):
    pass


def create_request(message_type: int, function_name: str, payload: str):
    i = 12345  # TODO thjis should be different/random
    return {"m": message_type, "i": i, "n": function_name, "o": payload}


class NDAXAuth:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_authenticate_user_request(self):
        return create_request(
            MESSAGE_TYPES["REQUEST"],
            "AuthenticateUser",
            json.dumps({"username": self.username, "password": self.password}),
        )

    def get_authenticate_2fa_request(self, code):
        return create_request(
            MESSAGE_TYPES["REQUEST"], "Authenticate2FA", json.dumps({"code": code})
        )


class NDAXSession:
    def __init__(self, username, password, apikey):
        self.auth_manager = NDAXAuth(username, password)

    async def initialize_session(self):
        self.session = await websockets.connect(NDAX_URL)

    async def close(self):
        await self.session.close()

    async def _send_and_receive(self, req):
        await self.session.send(json.dumps(req))
        response = await self.session.recv()
        return json.loads(response)

    async def authenticate(self):
        auth_req = self.auth_manager.get_authenticate_user_request()

        response = await self._send_and_receive(auth_req)
        payload = json.loads(response['o'])

        if payload["Authenticated"] and payload["Requires2FA"]:
            self.session_token = await self._authenticate_mfa()

    async def _authenticate_mfa(self):
        mfa_code = input("Enter MFA: >")
        req = self.auth_manager.get_authenticate_2fa_request(mfa_code)
        response = await self._send_and_receive(req)
        payload = json.loads(response["o"])

        if payload["Authenticated"]:
            return payload["SessionToken"]
        else:
            raise MFAError(f"MFA Failed: {payload}")

    async def subscribe(self):
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
        json.dumps({"username": username, "password": password}),
    )


with open(SECRET_PATH, "r") as secret_file:
    data = json.load(secret_file)
    secret = data["secret"]

connection_payload = {}


async def connect(uri):
    async with websockets.connect(NDAX_URL) as websocket:

        await websocket.send()
        response = await websocket.recv()
        print(response)
