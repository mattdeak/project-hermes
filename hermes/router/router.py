import asyncio
import json
import logging

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

    async def route(self, raw_message):
        message = json.loads(raw_message)

        message_fn = message["n"]
        payload = json.loads(message['o'])
        if message_fn == "SubscribeLevel2":  # Should update order book
            await self.orderbook.update(payload)

        elif message_fn == "Level2UpdateEvent":
            await self.orderbook.update(payload)
            await self.trader.recheck_orderbook_and_trade()

        elif message_fn == "GetAccountPositions":
            await self.account.process_account_positions(payload)

        elif message_fn == "OrderTradeEvent":  # Trade confirmation
            await self.trader.handle_trade_event(payload) 

        elif message_fn == 'SubscribeAccountEvents':
            if not payload['Subscribed']:
                raise ServerErrorMsg('Subscription to Account Events Failed')
            else:
                self.logger.info('Account Events Successfully Subscribed')

        elif message_fn == 'DepositTicketUpdateEvent':
            self.logger.info(f'Deposit Ticket Event: {payload}')

        elif message_fn in NDAXRouter.ACCOUNT_EVENTS:
            self.logger.warning(f'Unhandled account message. Not stopping op: {message_fn}')


        else:
            raise UnhandledMessageException(f"Message type not handled: {message_fn}")
