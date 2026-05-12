"""Payment service: WeChat Pay Native + Alipay precreate, callback handling, VIP fulfillment."""

import json
import logging
import time
import random
import string
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.datetime_utils import naive_utc, to_utc_aware, utc_now
from app.models.order import Order
from app.models.user import User
from app.services.vip_pricing import PLAN_META

logger = logging.getLogger(__name__)


def generate_order_no() -> str:
    ts = time.strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.digits, k=6))
    return f"OV{ts}{rand}"


# ---------------------------------------------------------------------------
# WeChat Pay
# ---------------------------------------------------------------------------

_wxpay = None


def _get_wxpay():
    global _wxpay
    if _wxpay is not None:
        return _wxpay

    from wechatpayv3 import WeChatPay, WeChatPayType

    _wxpay = WeChatPay(
        wechatpay_type=WeChatPayType.NATIVE,
        mchid=settings.WECHAT_MCH_ID,
        private_key=settings.WECHAT_PRIVATE_KEY,
        cert_serial_no=settings.WECHAT_CERT_SERIAL,
        apiv3_key=settings.WECHAT_API_V3_KEY,
        appid=settings.WECHAT_APP_ID,
        notify_url=settings.WECHAT_NOTIFY_URL,
    )
    return _wxpay


def create_wechat_native_order(order: Order) -> str | None:
    """Call WeChat Pay Native API and return code_url for QR code."""
    from wechatpayv3 import WeChatPayType

    plan = PLAN_META[order.plan_id]
    wxpay = _get_wxpay()
    code, message = wxpay.pay(
        description=f"OmniVideo {plan['name']}",
        out_trade_no=order.order_no,
        amount={"total": order.amount},
        pay_type=WeChatPayType.NATIVE,
    )
    logger.info("WeChat pay response: code=%s message=%s", code, message)
    if code in (200, 201):
        data = json.loads(message)
        return data.get("code_url")
    logger.error("WeChat pay failed: %s %s", code, message)
    return None


def verify_wechat_notify(headers: dict, body: bytes) -> dict | None:
    """Verify WeChat callback signature and decrypt payload. Returns resource dict or None."""
    wxpay = _get_wxpay()
    try:
        result = wxpay.callback(headers=headers, body=body)
    except Exception:
        logger.exception("WeChat callback verification failed")
        return None

    if not result:
        logger.warning("WeChat callback: decrypt/verify returned empty (check apiv3_key & platform certs)")
        return None
    if result.get("event_type") != "TRANSACTION.SUCCESS":
        logger.info(
            "WeChat callback ignored: event_type=%s",
            result.get("event_type"),
        )
        return None
    resource = result.get("resource")
    if not isinstance(resource, dict):
        logger.warning("WeChat callback: resource is not a dict after decrypt")
        return None
    return resource


def fetch_wechat_transaction_id_if_paid(order: Order) -> str | None:
    """Query WeChat for order state; if SUCCESS and amount matches, return transaction_id.

    Used when async notify URL is unreachable (HTTP-only URL, NAT down, firewall).
    """
    wxpay = _get_wxpay()
    try:
        code, message = wxpay.query(out_trade_no=order.order_no)
    except Exception:
        logger.exception("WeChat query failed for %s", order.order_no)
        return None
    if code != 200:
        logger.warning("WeChat query %s: HTTP %s %s", order.order_no, code, (message or "")[:500])
        return None
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        logger.warning("WeChat query %s: invalid JSON", order.order_no)
        return None
    if data.get("trade_state") != "SUCCESS":
        return None
    total = data.get("amount", {}).get("total")
    if total is not None and int(total) != order.amount:
        logger.error(
            "WeChat query amount mismatch order=%s expect=%s got=%s",
            order.order_no,
            order.amount,
            total,
        )
        return None
    tid = data.get("transaction_id")
    return tid if tid else None


def fetch_alipay_trade_no_if_paid(order: Order) -> str | None:
    """Query Alipay trade status; if paid and amount matches, return trade_no."""
    alipay = _get_alipay()
    try:
        result = alipay.api_alipay_trade_query(out_trade_no=order.order_no)
    except Exception:
        logger.exception("Alipay query failed for %s", order.order_no)
        return None
    if not result or str(result.get("code")) != "10000":
        return None
    status = result.get("trade_status")
    if status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return None
    total_yuan = result.get("total_amount")
    if total_yuan is not None:
        expected = f"{order.amount / 100:.2f}"
        if str(total_yuan) != expected:
            logger.error(
                "Alipay query amount mismatch order=%s expect=%s got=%s",
                order.order_no,
                expected,
                total_yuan,
            )
            return None
    trade_no = result.get("trade_no")
    return trade_no if trade_no else None


# ---------------------------------------------------------------------------
# Alipay
# ---------------------------------------------------------------------------

_alipay = None


def _wrap_pem(key: str, key_type: str = "RSA PRIVATE KEY") -> str:
    """Wrap raw base64 key with PEM headers if missing."""
    key = key.strip()
    if key.startswith("-----"):
        return key
    return f"-----BEGIN {key_type}-----\n{key}\n-----END {key_type}-----"


def _get_alipay():
    global _alipay
    if _alipay is not None:
        return _alipay

    from alipay import AliPay

    _alipay = AliPay(
        appid=settings.ALIPAY_APP_ID,
        app_notify_url=settings.ALIPAY_NOTIFY_URL,
        app_private_key_string=_wrap_pem(settings.ALIPAY_PRIVATE_KEY, "RSA PRIVATE KEY"),
        alipay_public_key_string=_wrap_pem(settings.ALIPAY_PUBLIC_KEY, "PUBLIC KEY"),
        sign_type="RSA2",
        debug=False,
    )
    return _alipay


def create_alipay_precreate_order(order: Order) -> str | None:
    """Call Alipay trade.precreate and return qr_code URL."""
    plan = PLAN_META[order.plan_id]
    alipay = _get_alipay()
    amount_yuan = f"{order.amount / 100:.2f}"
    result = alipay.api_alipay_trade_precreate(
        out_trade_no=order.order_no,
        total_amount=amount_yuan,
        subject=f"OmniVideo {plan['name']}",
    )
    logger.info("Alipay precreate response: %s", result)
    if result.get("code") == "10000":
        return result.get("qr_code")
    logger.error("Alipay precreate failed: %s", result)
    return None


def verify_alipay_notify(params: dict) -> bool:
    """Verify Alipay async notification RSA2 signature."""
    alipay = _get_alipay()
    signature = params.pop("sign", None)
    params.pop("sign_type", None)
    if not signature:
        return False
    return alipay.verify(params, signature)


# ---------------------------------------------------------------------------
# VIP fulfillment
# ---------------------------------------------------------------------------

async def fulfill_order(order: Order, db: AsyncSession) -> None:
    """Mark order as paid and grant VIP to the user."""
    if order.status != "pending":
        logger.warning("Order %s already fulfilled (status=%s)", order.order_no, order.status)
        return

    plan = PLAN_META[order.plan_id]
    duration = timedelta(days=plan["duration_days"])

    res = await db.execute(
        select(User.is_vip, User.vip_expire_at).where(User.id == order.user_id)
    )
    row = res.first()
    if not row:
        logger.error("User %s not found for order %s", order.user_id, order.order_no)
        return

    is_vip, vip_expire_at = row[0], row[1]

    now = utc_now()
    exp = to_utc_aware(vip_expire_at)
    if is_vip and exp and exp > now:
        new_expire = naive_utc(exp + duration)
    else:
        new_expire = naive_utc(now + duration)

    # 使用 Core UPDATE，避免同请求内多次加载 User 时 ORM 身份映射未把变更刷进库的问题
    result = await db.execute(
        update(User)
        .where(User.id == order.user_id)
        .values(
            is_vip=True,
            vip_expire_at=new_expire,
            ai_quota=9999,
            vip_plan_id=order.plan_id,
            updated_at=func.now(),
        )
    )
    if result.rowcount == 0:
        logger.warning(
            "VIP update rowcount=0 (user missing or values unchanged?) user_id=%s order=%s",
            order.user_id,
            order.order_no,
        )

    order.status = "paid"
    order.paid_at = naive_utc(now)

    await db.commit()
    logger.info(
        "Order %s fulfilled: user=%s vip_expire_at=%s",
        order.order_no,
        order.user_id,
        new_expire,
    )
