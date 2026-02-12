# Project Implementation Plan: AI Voice Bot for Loan Analysis

## Phase 1: Environment Setup & Core Infrastructure
**Goal:** Establish a working development environment with all necessary dependencies and configurations.

**Steps:**
1.  **Install Dependencies:** Update `requirements.txt` with `pipecat-ai` and its specific service modules (Twilio, Deepgram, Google), along with `fastapi`, `uvicorn`, and `pymongo`.
2.  **Verify API Keys:** Ensure `.env` is correctly loaded and all keys are valid. *Completed.*
3.  **Core Application Structure:** Create the basic FastAPI app structure in `backend/main.py` that will host our WebSocket endpoint.
4.  **Ngrok Setup:** (User Task) You will need to run ngrok to expose port 8000 so Twilio can reach your local machine.

## Phase 2: Building the Voice Pipeline (The "Bot")
**Goal:** Create the Pipecat pipeline that connects detailed speech-to-text, LLM processing, and text-to-speech.

**Steps:**
1.  **Twilio Transport:** Configure the `TwilioWebsocketInputTransport` and `TwilioWebsocketOutputTransport` to handle audio streams from the phone call.
2.  **Deepgram STT Service:** Set up Deepgram as the "ears" to transcribe user speech in real-time.
3.  **Gemini LLM Service:** Configure Google Gemini as the "brain." We will create a `system_prompt` that defines the bot's persona (Bank Loan Officer) and its goal (assess loan interest).
4.  **Deepgram TTS Service:** Set up Deepgram as the "mouth" to speak the LLM's responses back to the user.
5.  **Pipeline Construction:** Write the code to link these services together: `Transport -> STT -> LLM -> TTS -> Transport`.

## Phase 3: Call Management & Execution (Making it Ring)
**Goal:** capability to initiate an outbound call and handle the incoming audio stream.

**Steps:**
1.  **Outbound Call Endpoint:** Create an API endpoint (e.g., `/call-customer`) that triggers a Twilio outbound call to a specific number.
2.  **WebSocket Handler:** Create the FastAPI WebSocket route (e.g., `/twilio-stream`) that Twilio will connect to when the call is answered.
3.  **TwiML Response:** Configure the TwiML (Twilio Markup Language) to tell Twilio, "Connect this call to my WebSocket stream."

## Phase 4: Data Analysis & Persistence (The "Bank" Logic)
**Goal:** Save the result of the conversation (Interest Level) to MongoDB.

**Steps:**
1.  **Database Connection:** Set up `motor` (async MongoDB driver) to connect to your local MongoDB instance.
2.  **Conversation Analysis:** Refine the Gemini system prompt to output a JSON structure at the end of the call (e.g., `{"interest_level": "High", "reason": "..."}`).
3.  **Save Results:** Implement a step in the pipeline (or a post-call hook) to parse this analysis and save it to the `loan_interests` collection in MongoDB.

## Phase 5: Testing & Refinement
**Goal:** Verify the system works with real phone calls.

**Steps:**
1.  **End-to-End Test:** Run the server, start ngrok, and trigger a call to your own phone.
2.  **Latency Check:** Ensure there isn't too much delay between speaking and hearing a response.
3.  **Prompt Tuning:** Adjust the system prompt if the bot is too pushy or not understanding correctly.
