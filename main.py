from fastapi import FastAPI, Request
from crew_backend import run_crew_backend
import json
from tools import log_agent_action

app = FastAPI()

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/vapi-webhook")
async def vapi_webhook(request: Request):
    payload = await request.json()
    log_agent_action("SYSTEM", "Webhook received from Vapi/ngrok.")
    
    # Extract tool calls from known Vapi payload variants.
    message = payload.get("message", {})
    tool_calls = (
        message.get("toolCalls")
        or message.get("tool_calls")
        or payload.get("toolCalls")
        or payload.get("tool_calls")
        or []
    )
    if not tool_calls:
        log_agent_action("SYSTEM", "No tool calls found in webhook payload.")
        return {"results": []}

    results = []
    for tool_call in tool_calls:
        tool_call_id = tool_call.get("id")
        function_payload = tool_call.get("function", {})
        args = function_payload.get("arguments", {})
        
        # Parse arguments if Vapi sends them as a string
        if isinstance(args, str):
            args = json.loads(args)

        name = args.get("customer_name", "Customer")
        symptom = args.get("symptom", "unknown")
        date = args.get("date", "soon")
        time = args.get("time", "anytime")

        # Run the multi-agent backend!
        final_response = run_crew_backend(name, symptom, date, time)

        # Return exactly what Vapi needs to speak back to the user
        results.append({
            "toolCallId": tool_call_id,
            "result": final_response
        })

    return {"results": results}