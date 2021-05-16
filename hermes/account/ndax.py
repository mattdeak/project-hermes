from hermes.exchanges.ndax import create_request, NDAXSession
from collections import defaultdict
import logging


class NDAXAccount:
    def __init__(self, session, account_id):
        self.session = session
        self.account_id = account_id
        self.positions = defaultdict(float)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def request_account_update(self):
        req = create_request(0, 'GetAccountPositions',{'OMSId': 1, 'AccountId': self.account_id})
        await self.session.send(req)

    async def process_account_positions(self, account_position_payload):
        for entry in account_position_payload:
            instrument_id = entry['ProductId']
            amount = entry['Amount']
            if amount > 0.0:
                self.positions[instrument_id] = amount

        self.logger.info(f'Account Updated:\n {self.positions}')




