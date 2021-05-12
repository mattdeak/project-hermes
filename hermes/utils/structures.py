from dataclasses import dataclass

@dataclass
class Order:
    instrument_id: int
    side: int
    quantity: float
    order_type: int
    limit_price: float = 999999  # Just in case
    time_in_force: int = 1
