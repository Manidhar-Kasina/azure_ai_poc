import json
import logging
import azure.functions as func
import os
import requests

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("processIncident function started")

    # -----------------------------
    # 1. Read input JSON
    # -----------------------------
    try:
        incident = req.get_json()
    except Exception:
        return func.HttpResponse(
            json.dumps({"error": "Invalid or missing JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    # -----------------------------
    # 2. Embedded Knowledge Base
    # -----------------------------
    knowledge_base = [
        {
            "summary": "Payment transactions failing globally",
            "service": "Payments",
            "impact": "All users",
            "priority": "P1",
            "category": "Application",
            "assignment_group": "Payments Support",
            "major_incident": True
        },
        {
            "summary": "Customer portal unavailable",
            "service": "Customer Portal",
            "impact": "All users",
            "priority": "P1",
            "category": "Application",
            "assignment_group": "Web Platform Team",
            "major_incident": True
        },
        {
            "summary": "VPN login slow",
            "service": "Corporate VPN",
            "impact": "Few users",
            "priority": "P4",
            "category": "Network",
            "assignment_group": "Network Operations",
            "major_incident": False
        }
    ]

    # -----------------------------
    # 3. Build prompt
    # -----------------------------
    prompt = f"""
You are an IT incident triage expert.

Using ONLY the historical incident knowledge below,
determine the correct incident fields.

Historical Incidents:
{json.dumps(knowledge_base, indent=2)}

New Incident:
{json.dumps(incident, indent=2)}

Return STRICT JSON with these fields only:
major_incident (true/false),
recommended_priority,
recommended_category,
recommended_assignment_group,
confidence (0 to 1),
reasoning
"""

    # -----------------------------
    # 4. Call Azure OpenAI (REST – safest way)
    # -----------------------------
    openai_key = os.environ.get("AZURE_OPENAI_KEY")
    openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment = "incident-poc"

    if not openai_key or not openai_endpoint:
        # Safe fallback if OpenAI is not configured
        logging.warning("OpenAI not configured, returning fallback response")

        fallback_response = {
            "major_incident": True,
            "recommended_priority": "P1",
            "recommended_category": "Application",
            "recommended_assignment_group": "Payments Support",
            "confidence": 0.5,
            "reasoning": "Fallback response because Azure OpenAI configuration is missing"
        }

        return func.HttpResponse(
            json.dumps(fallback_response, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    try:
        url = f"{openai_endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview"

        headers = {
            "Content-Type": "application/json",
            "api-key": openai_key
        }

        body = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0
        }

        response = requests.post(url, headers=headers, json=body, timeout=20)
        response.raise_for_status()

        ai_text = response.json()["choices"][0]["message"]["content"]

        result = json.loads(ai_text)

        return func.HttpResponse(
            json.dumps(result, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"OpenAI call failed: {str(e)}")

        error_response = {
            "error": "AI processing failed",
            "details": str(e)
        }

        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            status_code=500,
            mimetype="application/json"
        )
