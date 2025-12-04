"""Main FastHTML application for ChatKit."""

import logging
import sys
from pathlib import Path

from fasthtml.common import (
    Script,
    Link,
    Meta,
    Title,
    fast_app,
)
import uvicorn

try:
    # When package is imported (recommended)
    from .config import AppConfig, ChatKitConfig, validate_config
    from .routes import handle_create_session, handle_health_check, handle_config
    from .components import ChatKitContainer, Header, MainLayout
except ImportError:
    # Allow running the file directly: `python app/main.py`
    # Fallback to absolute imports when the module has no parent package
    from app.config import AppConfig, ChatKitConfig, validate_config
    from app.routes import handle_create_session, handle_health_check, handle_config
    from app.components import ChatKitContainer, Header, MainLayout


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if AppConfig.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Validate configuration on startup
is_valid, error_msg = validate_config()
if not is_valid:
    logger.error(f"Configuration error: {error_msg}")
    if not AppConfig.DEBUG:
        sys.exit(1)

# Create FastHTML app using fast_app which handles static files automatically
static_dir = Path(__file__).parent / "static"
app, route = fast_app(
    debug=AppConfig.DEBUG,
    title="ChatKit Starter",
    static_path=str(static_dir),
)

# Ensure static files are properly mounted
app.static_route_exts(prefix='/static/', static_path=str(static_dir))


# Route: GET /
@route("/")
def home():
    """Serve the main ChatKit page."""
    # Create ChatKit components
    chatkit_container, error_overlay, init_script = ChatKitContainer(
        workflow_id=ChatKitConfig.WORKFLOW_ID,
        session_endpoint=AppConfig.CREATE_SESSION_ENDPOINT,
        placeholder=ChatKitConfig.PLACEHOLDER_INPUT,
        greeting=ChatKitConfig.GREETING,
    )
    
    header = Header()
    main_layout = MainLayout(header, chatkit_container, error_overlay)
    
    return (
        Title("ChatKit - OpenAI"),
        Link(rel="stylesheet", href="/static/styles.css"),
        Meta(name="color-scheme", content="light dark"),
        # Load ChatKit web component FIRST (without defer) so it's available for initialization
        Script(src="https://chatkit.openai.com/assets/chatkit.js"),
        main_layout,
        init_script,
    )


# Route: POST /api/create-session
@route("/api/create-session", methods=["POST"])
async def create_session(request):
    """Create a ChatKit session."""
    return await handle_create_session(request)


# Route: GET /api/health
@route("/api/health")
async def health(request):
    """Health check endpoint."""
    return await handle_health_check(request)


# Route: GET /api/config
@route("/api/config")
async def config(request):
    """Get client configuration."""
    return await handle_config(request)


def run():
    """Run the FastHTML application."""
    logger.info(
        f"Starting ChatKit FastHTML server on {AppConfig.HOST}:{AppConfig.PORT}"
    )
    
    uvicorn.run(
        "app.main:app" if AppConfig.DEBUG else app,
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        reload=AppConfig.DEBUG,
        log_level="debug" if AppConfig.DEBUG else "info",
    )


if __name__ == "__main__":
    run()
