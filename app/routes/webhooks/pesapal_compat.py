from fastapi import APIRouter, Request
from app.routes.webhooks.pesapal import ipn_handler

router = APIRouter()


@router.post("/webhooks/pesapal/ipn")
async def pesapal_ipn(request: Request):
    # Forward to the existing IPN handler for compatibility
    return await ipn_handler(request)
