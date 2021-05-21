import asyncio
import json
import logging
from hermes.utils.synchronization import SingletonResetEvent
from hermes.utils.structures import NDAXMessage

BTCCAD_ID = 1
BTCUSDT_ID = 82
USDTCAD_ID = 80


class UnhandledMessageException(Exception):
    pass


class ServerErrorMsg(Exception):
    pass


class NDAXRouter:
    ACCOUNT_EVENTS = [
        "AccountPositionEvent",
        "CancelAllOrdersRejectEvent",
        "CancelOrderRejectEvent",
        "CancelReplaceOrderRejectEvent",
        "MarketStatusUpdate",
        "NewOrderRejectEvent",
        "OrderStateEvent",
        "OrderTradeEvent",
        "PendingDepositUpdate",
    ]


    def __init__(self, session, account, orderbook, trader):
        self.account = account
        self.session = session
        self.orderbook = orderbook
        self.trader = trader
        self.logger = logging.getLogger(self.__class__.__name__)
        self.reset_event = SingletonResetEvent.instance()

    async def route(self, raw_message):
        message = self.parse_message_safely(raw_message)
        if not message:
            return

        message_fn = message.message_fn
        payload = message.payload

        if message_fn == "SubscribeLevel2":  # Should update order book
            self.logger.info("Subscription Message Received")
            await self.orderbook.update(payload)

        elif message_fn == "Level2UpdateEvent":
            await self.orderbook.update(payload)
            await self.trader.recheck_orderbook_and_trade()

        elif message_fn == "GetAccountPositions":
            await self.account.process_account_positions(payload)

        elif message_fn == "OrderTradeEvent":  # Trade confirmation
            await self.trader.handle_trade_event(payload)

        elif message_fn == "OrderStateEvent":
            await self.trader.handle_state_change_event(payload)

        elif message_fn == "SubscribeAccountEvents":
            if not payload["Subscribed"]:
                raise ServerErrorMsg("Subscription to Account Events Failed")
            else:
                self.logger.info("Account Events Successfully Subscribed")

        elif message_fn == "DepositTicketUpdateEvent":
            self.logger.info(f"Deposit Ticket Event: {payload}")

        elif message_fn == "SendOrder":
            self.logger.info(f"SendOrder Response: {message}")

        elif message_fn == 'NewOrderRejectEvent':
            self.logger.error(f'Order Rejected: {message}')

        elif message_fn in NDAXRouter.ACCOUNT_EVENTS:
            self.logger.warning(
                f"Unhandled account message. Not stopping op: {message_fn}"
            )

        else:
            self.logger.error(
                f"Unhandled account message. Not stopping op: {message_fn}"
            )

    def parse_message_safely(self, raw_message):
        """parse_message_safely.
        If the message can be parsed, parse it and return

        :param raw_message: raw json-encoded bytes message
        """
        try:
            message = json.loads(raw_message)

            message_fn = message["n"]
            payload = json.loads(message["o"])
            return NDAXMessage(message, message_fn, payload)
        except json.decoder.JSONDecodeError as e:
            self.logger.error(f'Json Decode Error on message: {raw_message}. Requesting reset.')
            self.reset_event.set()
            return None
