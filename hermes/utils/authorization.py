import hmac
import json
from random import randint
import hashlib


def create_NDAX_signature(user_id, api_key, secret):
    nonce = randint(100000, 999999)
    msg = f'{nonce}{user_id}{api_key}'.encode()
    key = bytes(secret, 'utf-8')
    signature = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return signature, nonce
