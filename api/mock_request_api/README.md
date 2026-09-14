# Employee Requests Mock API

This FastAPI service exposes three deterministic operations for watsonx Orchestrate:

- `resolve_employee`
- `submit_request`
- `check_request_status`

## Run locally on Windows

Open Command Prompt in this folder and run:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` to test the API.

## Create a temporary public link with ngrok

Keep the API terminal open. In a second terminal, install/configure ngrok and run:

```bat
ngrok http 8000
```

Copy the HTTPS forwarding URL. Replace `https://YOUR-PUBLIC-API-URL` in
`openapi_orchestrate.json` with that URL. Upload the edited file to watsonx
Orchestrate as an OpenAPI tool.

The ngrok terminal must remain open. A new free ngrok session may produce a new URL,
so update and re-import the OpenAPI file if the URL changes.

## Deploy for a stable demo link

1. Put this folder in a GitHub repository.
2. Create a Python web service on a host that supports FastAPI.
3. Use `pip install -r requirements.txt` as the build command.
4. Use `uvicorn app:app --host 0.0.0.0 --port $PORT` as the start command.
5. Copy the service's public HTTPS URL.
6. Replace the placeholder server URL in `openapi_orchestrate.json`.
7. Test `<public-url>/docs`, then import the OpenAPI file into Orchestrate.

The JSON store is suitable only for a controlled, single-user demo. A host with an
ephemeral filesystem may reset the requests file after a restart or redeployment.
