import uuid
import time
import random
import httpx
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks

app = FastAPI()

# --- CONFIGURATION ---
AUTH_URL = "https://email-api.preprod.cloud.unifonic.com/api/v1/oauth2/token"
WEBHOOK_URL = "https://email-api.preprod.cloud.unifonic.com/api/v1/public/webhook"
CLIENT_ID = "39ac2c38-0251-475a-82e3-652a29068d18"
CLIENT_SECRET = "g7RtW3Yd9HS9zzAzr+L8ZHY2e5TuD3PQY7kOTv39K6U="

async def dispatch_mock_events(data: dict):
    """Handles Auth and sends events to the webhook."""
    
    # 1. Get the Auth Token
    async with httpx.AsyncClient() as client:
        try:
            auth_res = await client.post(
                AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET
                }
            )
            auth_res.raise_for_status()
            token = auth_res.json().get("access_token")
        except Exception as e:
            print(f"Auth failed: {e}")
            return

        # 2. Prepare the 4 Mock Payloads
        to_email = data.get("personalizations", [{}])[0].get("to", [{}])[0].get("email")
        custom_args = data.get("custom_args", {})
        msg_id = f"message_{uuid.uuid4()}{random.randint(0,999)}"
        
        event_types = ["processed", "delivered", "open", "click"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 3. Send events sequentially (or with delays if preferred)
        for event_type in event_types:
            payload = {
                **custom_args,
                "email": to_email,
                "event": event_type,
                "sg_message_id": msg_id,
                "sg_event_id": f"Event_{event_type}_{uuid.uuid4()}",
                "timestamp": int(time.time()),
            }
            
            try:
                # Optional: Add a small sleep so events don't arrive at the exact same millisecond
                await asyncio.sleep(0.5) 
                response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
                print(f"Sent {event_type}: {response.status_code}")
            except Exception as e:
                print(f"Failed to send {event_type}: {e}")

@app.post("/")
async def webhook_handler(request: Request, background_tasks: BackgroundTasks):
    # Receive the incoming "send" request
    try:
        body = await request.json()
    except:
        return {"statusCode": 400, "body": "Invalid JSON"}

    # Validation
    if not body.get("personalizations"):
        return {"statusCode": 200, "body": "No personalizations found, ignoring."}

    # Run the heavy lifting (Auth + 4 API calls) in the background
    background_tasks.add_task(dispatch_mock_events, body)


    return {"statusCode": 202, "message": "Events queued for dispatch"}
