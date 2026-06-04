import os

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.middleware.auth import require_user

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

PRICE_IDS = {
    "pro": os.environ.get("STRIPE_PRICE_PRO", ""),
    "creator": os.environ.get("STRIPE_PRICE_CREATOR", ""),
    "studio": os.environ.get("STRIPE_PRICE_STUDIO", ""),
}

PLAN_LIMITS = {"free": 3, "pro": 30, "creator": 100, "studio": 999999}


@router.post("/create-checkout")
async def create_checkout(body: dict, authorization: str = Header(default="")):
    user = await require_user(authorization)
    plan = body.get("plan", "pro")
    price_id = PRICE_IDS.get(plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan}")
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    success_url = body.get("success_url", "http://localhost:3000/ja/dashboard")
    cancel_url = body.get("cancel_url", "http://localhost:3000/ja/pricing")

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        client_reference_id=user["id"],
        customer_email=user["email"],
        metadata={"plan": plan, "user_id": user["id"]},
    )
    return {"checkout_url": session.url}


@router.get("/portal")
async def billing_portal(return_url: str = "http://localhost:3000/ja/account", authorization: str = Header(default="")):
    user = await require_user(authorization)
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    # Supabase からcustomer_idを取得
    from app.middleware.auth import _get_supabase, AUTH_ENABLED
    if not AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Auth not configured")

    sb = _get_supabase()
    result = sb.table("profiles").select("stripe_customer_id").eq("id", user["id"]).single().execute()
    customer_id = result.data.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=404, detail="No billing account found")

    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(alias="stripe-signature", default="")):
    payload = await request.body()

    if not WEBHOOK_SECRET:
        return JSONResponse({"status": "webhook_secret_not_configured"})

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    await _handle_event(event)
    return {"status": "ok"}


async def _handle_event(event: dict):
    from app.middleware.auth import _get_supabase, AUTH_ENABLED
    if not AUTH_ENABLED:
        return

    sb = _get_supabase()
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = data.get("client_reference_id")
        plan = data.get("metadata", {}).get("plan", "free")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if user_id:
            sb.table("profiles").update({
                "plan": plan,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "subscription_status": "active",
            }).eq("id", user_id).execute()

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        customer_id = data.get("customer")
        status = data.get("status", "inactive")
        plan = "free" if event_type == "customer.subscription.deleted" else None

        update = {"subscription_status": status}
        if plan:
            update["plan"] = plan

        sb.table("profiles").update(update).eq("stripe_customer_id", customer_id).execute()
