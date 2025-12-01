"""
Workshop Demo UI

Interactive controller for PROMIS exchange scenarios
Shows technical challenges in distributed PROM systems
"""

import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List, Dict
import logging
from datetime import datetime

# Configuration
SITE_A_URL = os.getenv("SITE_A_URL", "http://hapi-site-a:8080/fhir")
SITE_B_URL = os.getenv("SITE_B_URL", "http://hapi-site-b:8080/fhir")
TERMINOLOGY_URL = os.getenv("TERMINOLOGY_URL", "http://terminology-proxy:3000/fhir")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PROMIS Workshop Demo",
    description="Interactive scenarios for multi-site PROM exchange",
    version="1.0.0"
)

client = httpx.AsyncClient(timeout=30.0)


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Workshop demo UI"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PROMIS Workshop Demo</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #2c3e50; }
            .card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .scenario {
                border-left: 4px solid #3498db;
                padding-left: 15px;
            }
            .success { border-left-color: #27ae60; }
            .warning { border-left-color: #f39c12; }
            .error { border-left-color: #e74c3c; }
            button {
                background: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                margin: 5px;
            }
            button:hover { background: #2980b9; }
            .endpoint {
                background: #ecf0f1;
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
                font-family: 'Courier New', monospace;
            }
            .result {
                margin-top: 20px;
                padding: 15px;
                background: #ecf0f1;
                border-radius: 4px;
                max-height: 400px;
                overflow-y: auto;
            }
            pre {
                background: #2c3e50;
                color: #ecf0f1;
                padding: 15px;
                border-radius: 4px;
                overflow-x: auto;
            }
        </style>
    </head>
    <body>
        <h1>🏥 Multi-Site PROMIS Exchange Workshop</h1>

        <div class="card">
            <h2>System Status</h2>
            <div id="status">Checking...</div>
            <button onclick="checkStatus()">Refresh Status</button>
        </div>

        <div class="card">
            <h2>Available Scenarios</h2>

            <div class="scenario success">
                <h3>✅ Scenario 1: Basic PROMIS Exchange</h3>
                <p>Demonstrates successful data transfer between sites</p>
                <button onclick="runScenario('basic')">Run Scenario</button>
            </div>

            <div class="scenario warning">
                <h3>⚠️ Scenario 2: Version Mismatch</h3>
                <p>Shows scoring algorithm version conflict (v1.0 vs v2.0)</p>
                <button onclick="runScenario('version-mismatch')">Run Scenario</button>
            </div>

            <div class="scenario error">
                <h3>❌ Scenario 3: Missing Translation</h3>
                <p>Demonstrates missing Turkish translation fallback</p>
                <button onclick="runScenario('missing-translation')">Run Scenario</button>
            </div>

            <div class="scenario warning">
                <h3>⚠️ Scenario 4: LOINC Panel API</h3>
                <p>Shows new LOINC panel structure API (not in standard)</p>
                <button onclick="runScenario('loinc-panel')">Run Scenario</button>
            </div>
        </div>

        <div class="card">
            <h2>Endpoints</h2>
            <div class="endpoint">Site A: <a href="http://localhost:8081/fhir/metadata" target="_blank">http://localhost:8081/fhir</a></div>
            <div class="endpoint">Site B: <a href="http://localhost:8082/fhir/metadata" target="_blank">http://localhost:8082/fhir</a></div>
            <div class="endpoint">Terminology: <a href="http://localhost:3000" target="_blank">http://localhost:3000</a></div>
            <div class="endpoint">API Docs: <a href="/docs" target="_blank">/docs</a></div>
        </div>

        <div class="card">
            <h2>Result</h2>
            <div class="result" id="result">
                <em>Select a scenario to see results...</em>
            </div>
        </div>

        <script>
            async function checkStatus() {
                const statusDiv = document.getElementById('status');
                statusDiv.innerHTML = 'Checking...';

                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();

                    let html = '<table style="width: 100%"><tr><th>Component</th><th>Status</th></tr>';
                    for (const [key, value] of Object.entries(data)) {
                        const status = value === 'ok' ? '✅ OK' : '❌ Error';
                        html += `<tr><td>${key}</td><td>${status}</td></tr>`;
                    }
                    html += '</table>';
                    statusDiv.innerHTML = html;
                } catch (error) {
                    statusDiv.innerHTML = '❌ Error checking status';
                }
            }

            async function runScenario(scenario) {
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '<em>Running scenario...</em>';

                try {
                    const response = await fetch(`/api/scenarios/${scenario}`);
                    const data = await response.json();

                    let html = `<h3>${data.name}</h3>`;
                    html += `<p>${data.description}</p>`;
                    html += '<h4>Steps:</h4><ol>';

                    for (const step of data.steps) {
                        const icon = step.success ? '✅' : step.warning ? '⚠️' : '❌';
                        html += `<li>${icon} ${step.description}`;
                        if (step.details) {
                            html += `<pre>${JSON.stringify(step.details, null, 2)}</pre>`;
                        }
                        html += '</li>';
                    }

                    html += '</ol>';

                    if (data.conclusion) {
                        html += `<h4>Conclusion:</h4><p><strong>${data.conclusion}</strong></p>`;
                    }

                    resultDiv.innerHTML = html;
                } catch (error) {
                    resultDiv.innerHTML = `<p style="color: red">Error: ${error.message}</p>`;
                }
            }

            // Check status on load
            checkStatus();
        </script>
    </body>
    </html>
    """


@app.get("/api/status")
async def status():
    """Check status of all components"""
    status_results = {}

    # Check Site A
    try:
        response = await client.get(f"{SITE_A_URL}/metadata", timeout=5.0)
        status_results["site_a"] = "ok" if response.status_code == 200 else "error"
    except:
        status_results["site_a"] = "error"

    # Check Site B
    try:
        response = await client.get(f"{SITE_B_URL}/metadata", timeout=5.0)
        status_results["site_b"] = "ok" if response.status_code == 200 else "error"
    except:
        status_results["site_b"] = "error"

    # Check Terminology Proxy
    try:
        response = await client.get(f"{TERMINOLOGY_URL.replace('/fhir', '')}/health", timeout=5.0)
        status_results["terminology"] = "ok" if response.status_code == 200 else "error"
    except:
        status_results["terminology"] = "error"

    return status_results


@app.get("/api/scenarios/{scenario_id}")
async def run_scenario(scenario_id: str):
    """Run a specific demo scenario"""

    if scenario_id == "basic":
        return await scenario_basic_exchange()
    elif scenario_id == "version-mismatch":
        return await scenario_version_mismatch()
    elif scenario_id == "missing-translation":
        return await scenario_missing_translation()
    elif scenario_id == "loinc-panel":
        return await scenario_loinc_panel()
    else:
        raise HTTPException(status_code=404, detail="Scenario not found")


async def scenario_basic_exchange():
    """Scenario 1: Basic PROMIS data exchange"""
    steps = []

    # Step 1: Get Questionnaire from Site A
    try:
        response = await client.get(
            f"{SITE_A_URL}/Questionnaire?url=http://loinc.org/Questionnaire/62629-8",
            timeout=10.0
        )
        if response.status_code == 200:
            steps.append({
                "description": "Retrieved PROMIS Pain Interference questionnaire from Site A",
                "success": True,
                "details": {"status": "200 OK", "count": response.json().get("total", 0)}
            })
        else:
            steps.append({
                "description": "Questionnaire not found (will be loaded by package installer)",
                "warning": True,
                "details": {"status": response.status_code}
            })
    except Exception as e:
        steps.append({
            "description": f"Error retrieving questionnaire: {str(e)}",
            "success": False
        })

    # Step 2: Terminology lookup
    try:
        response = await client.get(
            f"{TERMINOLOGY_URL}/ValueSet/$expand?url=http://loinc.org/vs/LL358-3",
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            steps.append({
                "description": "Retrieved PROMIS answer options from terminology service",
                "success": True,
                "details": {
                    "expansion_size": len(data.get("expansion", {}).get("contains", [])),
                    "sample": data.get("expansion", {}).get("contains", [])[0] if data.get("expansion", {}).get("contains") else None
                }
            })
    except Exception as e:
        steps.append({
            "description": f"Error retrieving terminology: {str(e)}",
            "success": False
        })

    return {
        "name": "Scenario 1: Basic PROMIS Exchange",
        "description": "Demonstrates successful questionnaire and terminology lookup",
        "steps": steps,
        "conclusion": "✅ Basic FHIR operations work correctly. Standard APIs sufficient for simple exchange."
    }


async def scenario_version_mismatch():
    """Scenario 2: Version mismatch between sites"""
    steps = []

    # Step 1: Get answer list with v1.0
    try:
        response = await client.get(
            f"{TERMINOLOGY_URL.replace('/fhir', '')}/loinc/AnswerList/LL358-3?version=1.0",
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            v1_ordinals = {item["code"]: item["extension"][0]["valueDecimal"]
                          for item in data["expansion"]["contains"]}
            steps.append({
                "description": "Site A: Retrieved answer list with v1.0 ordinals",
                "success": True,
                "details": {"ordinals": v1_ordinals}
            })
    except Exception as e:
        steps.append({"description": f"Error: {str(e)}", "success": False})

    # Step 2: Get answer list with v2.0
    try:
        response = await client.get(
            f"{TERMINOLOGY_URL.replace('/fhir', '')}/loinc/AnswerList/LL358-3?version=2.0",
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            v2_ordinals = {item["code"]: item["extension"][0]["valueDecimal"]
                          for item in data["expansion"]["contains"]}
            steps.append({
                "description": "Site B: Retrieved answer list with v2.0 ordinals (REVERSED!)",
                "warning": True,
                "details": {"ordinals": v2_ordinals}
            })

            # Compare
            differences = {code: {"v1": v1_ordinals.get(code), "v2": v2_ordinals.get(code)}
                          for code in v1_ordinals.keys()}
            steps.append({
                "description": "DANGER: Ordinal values are REVERSED between versions!",
                "success": False,
                "details": {"differences": differences}
            })
    except Exception as e:
        steps.append({"description": f"Error: {str(e)}", "success": False})

    return {
        "name": "Scenario 2: Version Mismatch",
        "description": "Demonstrates scoring algorithm version conflict",
        "steps": steps,
        "conclusion": "⚠️ CRITICAL: Same response scores differently on each site! Need version-aware validation APIs."
    }


async def scenario_missing_translation():
    """Scenario 3: Missing translation handling"""
    steps = []

    # Step 1: German (exists)
    try:
        response = await client.get(
            f"{TERMINOLOGY_URL.replace('/fhir', '')}/loinc/AnswerList/LL358-3?displayLanguage=de",
            timeout=10.0
        )
        if response.status_code == 200:
            steps.append({
                "description": "German translation: ✅ Available",
                "success": True
            })
    except Exception as e:
        steps.append({"description": f"Error: {str(e)}", "success": False})

    # Step 2: Turkish (partially missing)
    try:
        response = await client.get(
            f"{TERMINOLOGY_URL.replace('/fhir', '')}/loinc/AnswerList/LL358-3?displayLanguage=tr",
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            missing_count = sum(1 for item in data["expansion"]["contains"]
                              if "_extension" in item)
            steps.append({
                "description": f"Turkish translation: ⚠️ {missing_count} items missing",
                "warning": True,
                "details": {
                    "total": len(data["expansion"]["contains"]),
                    "missing": missing_count
                }
            })
    except Exception as e:
        steps.append({"description": f"Error: {str(e)}", "success": False})

    return {
        "name": "Scenario 3: Missing Translation",
        "description": "Shows fallback behavior for incomplete translations",
        "steps": steps,
        "conclusion": "❌ Products must implement fallback logic. No standard way to request 'best available' translation."
    }


async def scenario_loinc_panel():
    """Scenario 4: LOINC Panel API (NEW)"""
    steps = []

    # Step 1: Try standard LOINC FHIR service (will fail)
    steps.append({
        "description": "Standard LOINC FHIR service: ❌ No panel structure API exists",
        "success": False,
        "details": {"api": "https://fhir.loinc.org/Panel/62629-8", "status": "Not Found"}
    })

    # Step 2: Use our enhanced API
    try:
        response = await client.get(
            f"{TERMINOLOGY_URL.replace('/fhir', '')}/loinc/Panel/62629-8?format=Questionnaire",
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            steps.append({
                "description": "Enhanced API: ✅ Converts LOINC panel to FHIR Questionnaire",
                "success": True,
                "details": {
                    "panel": "62629-8",
                    "item_count": len(data.get("item", [])),
                    "sample_item": data.get("item", [{}])[0] if data.get("item") else None
                }
            })
    except Exception as e:
        steps.append({"description": f"Error: {str(e)}", "success": False})

    return {
        "name": "Scenario 4: LOINC Panel API",
        "description": "Demonstrates need for LOINC-specific enhancement APIs",
        "steps": steps,
        "conclusion": "⚠️ Standard doesn't support auto-generation of questionnaires from LOINC panels. Enhanced APIs needed!"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
