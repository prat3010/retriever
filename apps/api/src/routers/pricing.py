import json

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key
from src.adapters.database.connection import tenant_session
from src.adapters.database.models import ConfigurationDb

router = APIRouter(prefix="/v1", tags=["Pricing"])

DEFAULT_PRICING = {
    "inr": {
        "currency": "INR",
        "symbol": "₹",
        "plans": [
            {
                "id": "starter_inr",
                "name": "Starter",
                "price": "1,999",
                "period": "/month",
                "popular": False,
                "description": "Ideal for small websites, blogs, and personal projects.",
                "features": [
                    "1 Workspace / Tenant",
                    "20 Documents (~50MB)",
                    "1,000 Chat Queries / mo",
                    "Llama 3.3 70B & Gemini 2.5",
                    "Standard Support",
                ],
                "cta": "Start 7-Day Free Trial",
                "stripeUrl": "https://buy.stripe.com/test_starter_inr",
            },
            {
                "id": "pro_inr",
                "name": "Pro",
                "price": "5,999",
                "period": "/month",
                "popular": True,
                "description": "For growing businesses, legal teams, and e-commerce stores.",
                "features": [
                    "5 Workspaces / Tenants",
                    "100 Documents (~500MB)",
                    "5,000 Chat Queries / mo",
                    "Remove 'Powered by' Branding",
                    "Presigned Citation PDF Downloads",
                    "Priority Hybrid Search & Re-ranking",
                ],
                "cta": "Upgrade to Pro",
                "stripeUrl": "https://buy.stripe.com/test_pro_inr",
            },
            {
                "id": "business_inr",
                "name": "Business",
                "price": "14,999",
                "period": "/month",
                "popular": False,
                "description": "For agencies, medical networks, and high-traffic platforms.",
                "features": [
                    "Unlimited Workspaces",
                    "500 Documents (~2.5GB)",
                    "20,000 Chat Queries / mo",
                    "Dedicated Private Tenant RLS Isolation",
                    "Custom Domain Mapping",
                    "99.9% Uptime SLA & 24/7 Support",
                ],
                "cta": "Get Business Plan",
                "stripeUrl": "https://buy.stripe.com/test_business_inr",
            },
        ],
    },
    "usd": {
        "currency": "USD",
        "symbol": "$",
        "plans": [
            {
                "id": "starter_usd",
                "name": "Starter",
                "price": "29",
                "period": "/month",
                "popular": False,
                "description": "Ideal for small websites, blogs, and personal projects.",
                "features": [
                    "1 Workspace / Tenant",
                    "20 Documents (~50MB)",
                    "1,000 Chat Queries / mo",
                    "Llama 3.3 70B & Gemini 2.5",
                    "Standard Support",
                ],
                "cta": "Start 7-Day Free Trial",
                "stripeUrl": "https://buy.stripe.com/test_starter_usd",
            },
            {
                "id": "pro_usd",
                "name": "Pro",
                "price": "79",
                "period": "/month",
                "popular": True,
                "description": "For growing businesses, legal teams, and e-commerce stores.",
                "features": [
                    "5 Workspaces / Tenants",
                    "100 Documents (~500MB)",
                    "5,000 Chat Queries / mo",
                    "Remove 'Powered by' Branding",
                    "Presigned Citation PDF Downloads",
                    "Priority Hybrid Search & Re-ranking",
                ],
                "cta": "Upgrade to Pro",
                "stripeUrl": "https://buy.stripe.com/test_pro_usd",
            },
            {
                "id": "business_usd",
                "name": "Business",
                "price": "199",
                "period": "/month",
                "popular": False,
                "description": "For agencies, medical networks, and high-traffic platforms.",
                "features": [
                    "Unlimited Workspaces",
                    "500 Documents (~2.5GB)",
                    "20,000 Chat Queries / mo",
                    "Dedicated Private Tenant RLS Isolation",
                    "Custom Domain Mapping",
                    "99.9% Uptime SLA & 24/7 Support",
                ],
                "cta": "Get Business Plan",
                "stripeUrl": "https://buy.stripe.com/test_business_usd",
            },
        ],
    },
}


class UpdatePricingRequest(BaseModel):
    pricing: dict = Field(..., description="Complete pricing JSON structure for INR and USD plans")


@router.get(
    "/config/pricing",
    status_code=status.HTTP_200_OK,
)
async def get_pricing_config() -> dict:
    """Retrieve public SaaS pricing packages for INR and USD tiers."""
    try:
        async with tenant_session(bypass_rls=True) as session:
            from sqlalchemy import select
            stmt = select(ConfigurationDb).where(ConfigurationDb.key == "rag_pricing_packages")
            res = await session.execute(stmt)
            config_entry = res.scalar_one_or_none()
            if config_entry and config_entry.value:
                val = config_entry.value
                return val if isinstance(val, dict) else json.loads(val)
    except Exception:
        pass
    return DEFAULT_PRICING


@router.put(
    "/admin/config/pricing",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def update_pricing_config(payload: UpdatePricingRequest) -> dict:
    """Update active SaaS pricing packages in database (Admin only)."""
    async with tenant_session(bypass_rls=True) as session:
        from sqlalchemy import select
        stmt = select(ConfigurationDb).where(ConfigurationDb.key == "rag_pricing_packages")
        res = await session.execute(stmt)
        config_entry = res.scalar_one_or_none()

        if config_entry:
            config_entry.value = payload.pricing
            config_entry.version += 1
        else:
            new_entry = ConfigurationDb(
                key="rag_pricing_packages",
                value=payload.pricing,
                version=1,
            )
            session.add(new_entry)
        await session.commit()
    return {"status": "updated", "pricing": payload.pricing}
