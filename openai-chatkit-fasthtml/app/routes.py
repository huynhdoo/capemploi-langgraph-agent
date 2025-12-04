"""Routes for ChatKit FastHTML application."""

import json
import logging
from typing import Any, Optional

from fasthtml.common import Request, Response
import httpx

from .config import ChatKitConfig, AppConfig, ThemeConfig, ColorScheme, validate_config
from .session import (
    create_chatkit_session,
    create_or_get_session_cookie,
    build_session_cookie_header,
    extract_upstream_error,
    CreateSessionRequest,
)


logger = logging.getLogger(__name__)
is_production = not AppConfig.DEBUG


def json_resp(obj: Any, status_code: int = 200, headers: Optional[dict] = None) -> Response:
    """Build a JSON Response compatible with fasthtml's Response.

    This helper ensures we always return a Response with a JSON body
    and the proper Content-Type header. It also preserves any provided
    headers.
    """
    body = json.dumps(obj)
    # Try to create Response using common signature
    try:
        resp = Response(body, status=status_code)
    except TypeError:
        # Fallback if Response expects (content, status_code)
        resp = Response(body, status_code)

    # Ensure headers dict exists and apply JSON content-type
    try:
        resp.headers["Content-Type"] = "application/json"
    except Exception:
        # If Response doesn't expose headers as dict, try setting attribute
        try:
            resp.headers = {"Content-Type": "application/json"}
        except Exception:
            pass

    if headers:
        try:
            resp.headers.update(headers)
        except Exception:
            # If headers isn't a dict or update fails, ignore additional headers
            pass

    return resp


async def handle_create_session(request: Request) -> Response:
    """Handle POST requests to create a ChatKit session.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        JSON response with session token or error
    """
    if request.method != "POST":
        return json_resp(
            {"error": "Method not allowed"},
            status_code=405,
        )
    
    try:
        # Parse request body
        try:
            body = await request.json()
        except json.JSONDecodeError:
            body = {}
        
        request_data = CreateSessionRequest(**body) if body else CreateSessionRequest()
        
        # Get or create session
        headers_dict = dict(request.headers) if request.headers else {}
        user_id, session_cookie = await create_or_get_session_cookie(headers_dict)
        
        # Resolve workflow ID
        workflow_id = (
            request_data.workflow.get("id") if request_data.workflow else None
        ) or ChatKitConfig.WORKFLOW_ID
        
        if not workflow_id:
            return json_resp(
                {"error": "Missing workflow id"},
                status_code=400,
            )
        
        # Log request (non-production only)
        if not is_production:
            logger.info(
                f"[create-session] handling request: {workflow_id}",
                extra={"body": body},
            )
        
        # Create ChatKit session
        try:
            session_response = await create_chatkit_session(
                api_key=ChatKitConfig.OPENAI_API_KEY,
                workflow_id=workflow_id,
                user_id=user_id,
                file_upload_enabled=(
                    request_data.chatkit_configuration.get("file_upload", {})
                    .get("enabled", False)
                    if request_data.chatkit_configuration
                    else False
                ),
                api_base=ChatKitConfig.API_BASE,
            )
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return json_resp(
                {"error": str(e)},
                status_code=500,
            )
        except httpx.HTTPError as e:
            logger.error(f"ChatKit API error: {e}")
            # Attempt to extract error details
            try:
                error_data = e.response.json() if hasattr(e, "response") else {}
            except Exception:
                error_data = {}
            
            error_msg = extract_upstream_error(error_data)
            return json_resp(
                {"error": f"Session creation failed: {error_msg}"},
                status_code=e.response.status_code if hasattr(e, "response") else 500,
            )
        
        # Log success (non-production only)
        if not is_production:
            logger.info("[create-session] session created successfully")
        
        # Return response with session cookie
        response = json_resp(session_response, status_code=200)
        response.headers["Set-Cookie"] = build_session_cookie_header(session_cookie)
        return response
        
    except Exception as e:
        logger.error(f"Unexpected error in create_session: {e}", exc_info=True)
        return json_resp(
            {"error": "Internal server error"},
            status_code=500,
        )


async def handle_health_check(request: Request) -> Response:
    """Health check endpoint.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        JSON response with health status
    """
    is_valid, error_msg = validate_config()
    
    if not is_valid:
        return json_resp(
            {
                "status": "unhealthy",
                "error": error_msg,
            },
            status_code=503,
        )
    
    return json_resp(
        {
            "status": "healthy",
            "workflow_id": ChatKitConfig.WORKFLOW_ID,
        },
        status_code=200,
    )


async def handle_config(request: Request) -> Response:
    """Return client-safe configuration.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        JSON response with configuration
    """
    theme = request.query_params.get("theme", "light")
    scheme = ColorScheme.DARK if theme == "dark" else ColorScheme.LIGHT
    
    return json_resp(
        {
            "workflow_id": ChatKitConfig.WORKFLOW_ID,
            "greeting": ChatKitConfig.GREETING,
            "placeholder": ChatKitConfig.PLACEHOLDER_INPUT,
            "prompts": [
                {
                    "label": p.label,
                    "prompt": p.prompt,
                    "icon": p.icon,
                }
                for p in ChatKitConfig.STARTER_PROMPTS
            ],
            "theme": ThemeConfig.get_theme_config(scheme),
            "endpoint": AppConfig.CREATE_SESSION_ENDPOINT,
        },
        status_code=200,
    )
