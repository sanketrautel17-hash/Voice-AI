import os
import json
import asyncio
from typing import Optional

from fastapi import APIRouter, Request, Response, WebSocket, HTTPException
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect
from commons.logger import logger

log = logger(__name__)
from dotenv import load_dotenv

from core.pipeline import bot
from core.apis.schemas.call_schemas import DialoutResponse, DialoutRequest
from core.db.database import get_database

load_dotenv()

router = APIRouter()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
PUBLIC_URL = os.getenv("PUBLIC_URL")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


@router.post("/dialout", response_model=DialoutResponse)
async def handle_dialout_request(request: DialoutRequest):
    """
    Handle outbound call request and initiate call via Twilio.
    """
    to_number = request.to_number

    if not PUBLIC_URL:
        raise HTTPException(status_code=500, detail="PUBLIC_URL is not set in .env")

    # Construct TwiML directly to avoiding an extra HTTP round-trip
    # Use /ws endpoint as per the new structure
    stream_url = f"wss://{PUBLIC_URL.replace('https://', '').replace('http://', '')}/ws"

    # Construct TwiML using the helper library for safety and parameters
    response = VoiceResponse()
    connect = Connect()
    stream = connect.stream(url=stream_url)

    # Pass metadata to the WebSocket (Useful for the Bot to know who it's talking to)
    stream.parameter(name="to_number", value=to_number)
    response.append(connect)

    twiml_instruction = str(response)

    log.info(f"Initiating call to {to_number} with direct TwiML stream to {stream_url}")

    try:
        call = twilio_client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            twiml=twiml_instruction,
            method="POST",
        )
    except Exception as e:
        log.error(f"Failed to initiate Twilio call: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate call: {str(e)}"
        )

    return DialoutResponse(
        call_sid=call.sid, status="call_initiated", to_number=to_number
    )


# Alias for backward compatibility if needed
@router.post("/call-customer", include_in_schema=False)
async def call_customer_alias(to_number: str):
    return await handle_dialout_request(DialoutRequest(to_number=to_number))


@router.post("/twiml")
async def get_twiml(request: Request):
    """
    Return TwiML instructions for connecting call to WebSocket.
    """
    response = VoiceResponse()
    connect = Connect()
    # Ensure wss:// protocol for WebSocket
    stream_url = f"wss://{PUBLIC_URL.replace('https://', '').replace('http://', '')}/ws"
    connect.stream(url=stream_url)
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handle WebSocket connection from Twilio Media Streams.
    """
    try:
        await websocket.accept()
        log.info("WebSocket connection accepted for outbound call")

        # 1. Wait for the initial 'start' message from Twilio to get the Stream SID
        start_message = None

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["event"] == "connected":
                log.info("Received connected event, waiting for start...")
                continue
            elif message["event"] == "start":
                start_message = message
                # Log any custom parameters we passed in TwiML
                custom_params = start_message["start"].get("customParameters", {})
                log.info(f"Stream parameters received: {custom_params}")
                break
            else:
                log.warning(f"Ignoring unexpected event: {message['event']}")

        stream_sid = start_message["start"]["streamSid"]
        call_sid = start_message["start"]["callSid"]

        # Pass the custom params (like to_number) to the bot if needed later
        # For now, just logging it is enough
        to_number = start_message["start"].get("customParameters", {}).get("to_number")

        log.info(
            f"Stream started with SID: {stream_sid} for Call SID: {call_sid} (To: {to_number})"
        )

        # 2. Hand off to the Bot logic
        await bot(websocket, stream_sid, call_sid)
    except Exception as e:
        log.error(f"Error in websocket_endpoint: {e}")
        await websocket.close()


# ... existing imports ...
from typing import List, Any
from bson import ObjectId


# Helper to convert ObjectId to string
def serialize_mongo_doc(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


@router.get("/calls")
async def get_calls():
    """
    Retrieve call history with analysis.
    """
    db = get_database()
    calls_cursor = db["calls"].find().sort("start_time", -1).limit(50)
    calls = await calls_cursor.to_list(length=50)
    return [serialize_mongo_doc(call) for call in calls]


# Alias for backward compatibility
@router.websocket("/twilio-stream")
async def twilio_stream_alias(websocket: WebSocket):
    await websocket_endpoint(websocket)
