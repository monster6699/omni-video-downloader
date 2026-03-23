from datetime import datetime

from pydantic import BaseModel


class PlanInfo(BaseModel):
    id: str
    name: str
    price: int
    duration_days: int
    description: str


class CreateOrderRequest(BaseModel):
    plan_id: str
    pay_method: str


class CreateOrderResponse(BaseModel):
    order_no: str
    qr_url: str
    amount: int
    pay_method: str


class OrderStatusResponse(BaseModel):
    order_no: str
    status: str
    plan_id: str
    amount: int
    pay_method: str
    paid_at: datetime | None = None
