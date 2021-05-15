from dataclasses import dataclass
from typing import Optional

@dataclass
class Order:
    instrument_id: int
    side: int
    quantity: float
    order_type: int
    limit_price: float = 999999  # Just in case
    time_in_force: int = 1
    expected_price: Optional[float] = None
