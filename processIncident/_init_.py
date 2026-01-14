import json
import logging
import os
import azure.functions as func
from openai import AzureOpenAI

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("processIncident function started")

    try:
        # 1. Read input JSON
        try:
            incident = req.get_json()
        except Exception:
            return func.HttpResponse(
                "Invalid or missing JSON body",
                status_code=400
            )

        # 2. Load knowledge base
        try:
            with open("incident_kb.json", "r") as f:
                kb = json.load(f)
        except Exception as e:
            logging.error(f"KB load failed: {str(e)}")
            return func.HttpResponse(
                "Knowledge base file not found",
                status_code=500
            )

        # 3. Create Azure OpenAI client
        client = AzureOpenAI(
            api_key=os.environ.get("AZURE_OPENAI_KEY"),
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_version="2024-02-15-preview"
        )

        # 4. Build prompt
        prompt = f"""
You are an IT incident triage expert.

Using ONLY the historical incident knowledge below,
correct the fields of the new incident.

Historical Incident Knowledge:
{json.dumps(kb, indent=2)}

New Incident:
{json.dumps(incident, indent=2)}

Return STRICT JSON with these fields only:
- major_incident (true/false)
- recommended_priority
- recommended_category
- recommended_assignment_group
- confidence (0 to 1)
- reasoning
"""

        # 5. Call Azure OpenAI
        response = client.chat.completions.create(
            model="incident-poc",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        ai_output = response.choices[0].message.content

        # 6. Validate AI output is JSON
        try:
            parsed_output = json.loads(ai_output)
        except Exception:
            logging.error(f"AI returned non-JSON: {ai_output}")
            return func.HttpResponse(
                ai_output,
                status_code=200,
                mimetype="text/plain"
            )

        # 7. Return result
        return func.HttpResponse(
            json.dumps(parsed_output, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Unhandled error: {str(e)}")
        return func.HttpResponse(
            "Internal server error",
            status_code=500
        )
