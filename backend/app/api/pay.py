"""Payment API: create orders, poll status, receive async notifications."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.pay import (
    CreateOrderRequest,
    CreateOrderResponse,
    OrderStatusResponse,
    PlanInfo,
)
from app.services.pay_service import (
    create_alipay_precreate_order,
    create_wechat_native_order,
    fetch_alipay_trade_no_if_paid,
    fetch_wechat_transaction_id_if_paid,
    fulfill_order,
    generate_order_no,
    verify_alipay_notify,
    verify_wechat_notify,
)
from app.services.vip_pricing import plans_for_api, price_fen_for_plan, valid_plan_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans(db: AsyncSession = Depends(get_db)):
    raw = await plans_for_api(db)
    return [PlanInfo(**p) for p in raw]


@router.post("/create", response_model=CreateOrderResponse)
async def create_order(
    req: CreateOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not valid_plan_id(req.plan_id):
        raise HTTPException(status_code=400, detail="无效的套餐")
    if req.pay_method not in ("wechat", "alipay"):
        raise HTTPException(status_code=400, detail="无效的支付方式")

    amount = await price_fen_for_plan(db, req.plan_id)
    order = Order(
        order_no=generate_order_no(),
        user_id=user.id,
        plan_id=req.plan_id,
        amount=amount,
        pay_method=req.pay_method,
        status="pending",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    if req.pay_method == "wechat":
        qr_url = create_wechat_native_order(order)
    else:
        qr_url = create_alipay_precreate_order(order)

    if not qr_url:
        order.status = "failed"
        await db.commit()
        raise HTTPException(status_code=502, detail="支付下单失败，请稍后重试")

    order.qr_url = qr_url
    await db.commit()

    return CreateOrderResponse(
        order_no=order.order_no,
        qr_url=qr_url,
        amount=order.amount,
        pay_method=order.pay_method,
    )


@router.get("/status/{order_no}", response_model=OrderStatusResponse)
async def poll_order_status(
    order_no: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Order).where(Order.order_no == order_no, Order.user_id == user.id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 异步通知可能因 notify 地址非 HTTPS / 穿透失效等未送达，轮询时用官方查单补单
    if order.status == "pending":
        ext_id: str | None = None
        if order.pay_method == "wechat":
            ext_id = fetch_wechat_transaction_id_if_paid(order)
        elif order.pay_method == "alipay":
            ext_id = fetch_alipay_trade_no_if_paid(order)
        if ext_id:
            order.transaction_id = ext_id
            await fulfill_order(order, db)
            await db.refresh(order)

    return OrderStatusResponse(
        order_no=order.order_no,
        status=order.status,
        plan_id=order.plan_id,
        amount=order.amount,
        pay_method=order.pay_method,
        paid_at=order.paid_at,
    )


@router.post("/notify/wechat")
async def wechat_notify(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    resource = verify_wechat_notify(dict(request.headers), body)
    if not resource:
        logger.warning(
            "WeChat notify rejected (len=%s headers have signature=%s)",
            len(body),
            bool(request.headers.get("wechatpay-signature")),
        )
        return PlainTextResponse(
            '{"code":"FAIL","message":"验签失败"}',
            status_code=400,
            media_type="application/json",
        )

    out_trade_no = resource.get("out_trade_no")
    transaction_id = resource.get("transaction_id")

    stmt = select(Order).where(Order.order_no == out_trade_no)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        logger.warning("WeChat notify: order %s not found", out_trade_no)
        return {"code": "SUCCESS", "message": "成功"}

    if order.status != "pending":
        return {"code": "SUCCESS", "message": "成功"}

    order.transaction_id = transaction_id
    await fulfill_order(order, db)

    return {"code": "SUCCESS", "message": "成功"}


@router.post("/notify/alipay")
async def alipay_notify(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    params = dict(form)

    if not verify_alipay_notify(params):
        logger.warning("Alipay notify: signature verification failed")
        return PlainTextResponse("fail")

    trade_status = params.get("trade_status")
    if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return PlainTextResponse("success")

    out_trade_no = params.get("out_trade_no")
    transaction_id = params.get("trade_no")

    stmt = select(Order).where(Order.order_no == out_trade_no)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        logger.warning("Alipay notify: order %s not found", out_trade_no)
        return PlainTextResponse("success")

    if order.status != "pending":
        return PlainTextResponse("success")

    order.transaction_id = transaction_id
    await fulfill_order(order, db)

    return PlainTextResponse("success")
