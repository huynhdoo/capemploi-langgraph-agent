"""FastHTML components for ChatKit application."""

from fasthtml.common import Div, Script, Button, Span


def ChatKitContainer(
    workflow_id: str,
    session_endpoint: str = "/api/create-session",
    placeholder: str = "Ask anything...",
    greeting: str = "How can I help you today?",
):
    """
    ChatKit component that initializes the OpenAI ChatKit web component.
    
    Args:
        workflow_id: The ChatKit workflow ID
        session_endpoint: The endpoint to create sessions
        placeholder: The placeholder text for the input
        greeting: The greeting message
        
    Returns:
        A tuple of (container_div, initialization_script)
    """
    
    # Container for the ChatKit component
    container = Div(
        Div(
            cls="spinner",
        ),
        id="chatkit-container",
        cls="chatkit-container loading",
    )
    
    # Error overlay
    error_overlay = Div(
        Div(
            Div(
                "Error",
                cls="error-overlay-title",
            ),
            Div(
                id="error-message",
                cls="error-overlay-message",
            ),
            Button(
                "Retry",
                id="retry-button",
                cls="error-overlay-button",
                onclick="window.retryChatKit && window.retryChatKit()",
            ),
            cls="error-overlay-content",
        ),
        id="error-overlay",
        cls="error-overlay",
        style="display: none;",
    )
    
    # Initialization script
    init_script = Script(
          f"""
  (function initializeChatKit() {{
    const CONFIG = {{
      workflowId: `{workflow_id}`,
      sessionEndpoint: `{session_endpoint}`,
      placeholder: `{placeholder}`,
      greeting: `{greeting}`,
    }};

  console.log('[ChatKit] Config loaded:', CONFIG);

  const chatkitContainer = document.getElementById('chatkit-container');
  const errorOverlay = document.getElementById('error-overlay');
  const errorMessage = document.getElementById('error-message');
  const retryButton = document.getElementById('retry-button');
  const themeToggle = document.getElementById('theme-toggle');

  let chatkitElement = null;

  function showError(message, retryable = true) {{
    console.error('[ChatKit]', message);
    if (errorMessage) {{
      errorMessage.textContent = message;
    }}
    if (errorOverlay) {{
      errorOverlay.style.display = 'flex';
    }}
    if (retryButton && !retryable) {{
      retryButton.style.display = 'none';
    }}
  }}

  function hideError() {{
    if (errorOverlay) {{
      errorOverlay.style.display = 'none';
    }}
  }}

  function toggleTheme() {{
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateChatkitTheme();
  }}

  function initializeTheme() {{
    const saved = localStorage.getItem('theme');
    const prefer = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = saved ? saved === 'dark' : prefer;
    
    if (isDark) {{
      document.documentElement.classList.add('dark');
    }}
    
    if (themeToggle) {{
      themeToggle.addEventListener('click', toggleTheme);
    }}
  }}

  function updateChatkitTheme() {{
    if (chatkitElement) {{
      const isDark = document.documentElement.classList.contains('dark');
      chatkitElement.theme = isDark ? 'dark' : 'light';
    }}
  }}

  async function createSession() {{
    try {{
      console.log('[ChatKit] Creating session...');
      const response = await fetch(CONFIG.sessionEndpoint, {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
        }},
        credentials: 'include',
        body: JSON.stringify({{
          workflow: {{ id: CONFIG.workflowId }},
          chatkit_configuration: {{
            file_upload: {{ enabled: false }},
          }},
        }}),
      }});

      if (!response.ok) {{
        const error = await response.json();
        throw new Error(error.error || `HTTP ${{response.status}}: Failed to create session`);
      }}

      const session = await response.json();
      console.log('[ChatKit] Session created:', session.id);
      return session;
    }} catch (error) {{
      console.error('[ChatKit] Session creation error:', error);
      throw error;
    }}
  }}

  async function initChatKit() {{
    try {{
      console.log('[ChatKit] Initializing ChatKit component...');
      
      // Wait for ChatKit component to be available (max 5 seconds)
      let attempts = 0;
      const maxAttempts = 50; // 50 * 100ms = 5 seconds
      
      while (!customElements.get('openai-chatkit') && attempts < maxAttempts) {{
        if (attempts === 0) {{
          console.log('[ChatKit] Waiting for ChatKit web component to load...');
        }}
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
      }}
      
      if (!customElements.get('openai-chatkit')) {{
        showError('ChatKit component not loaded. Please refresh the page.');
        console.error('[ChatKit] Component "openai-chatkit" not found after 5 seconds');
        return;
      }}

      console.log('[ChatKit] ChatKit component loaded after', attempts * 100, 'ms');
      hideError();

      // Create session
      const session = await createSession();
      
      // Create ChatKit element
      chatkitElement = document.createElement('openai-chatkit');
      // Use client_secret as the sessionToken for authentication
      chatkitElement.sessionToken = session.client_secret;
      chatkitElement.placeholder = CONFIG.placeholder;
      chatkitElement.greetingText = CONFIG.greeting;
      
      console.log('[ChatKit] ChatKit element created with session:', session.id);
      console.log('[ChatKit] Using client_secret for authentication');
      
      updateChatkitTheme();

      if (chatkitContainer) {{
        chatkitContainer.innerHTML = '';
        chatkitContainer.appendChild(chatkitElement);
        console.log('[ChatKit] ChatKit element mounted to DOM');
      }} else {{
        console.error('[ChatKit] Container not found!');
      }}
    }} catch (error) {{
      showError(`Failed to initialize ChatKit: ${{error.message}}`);
      console.error('[ChatKit] Initialization error:', error);
      if (retryButton) {{
        retryButton.onclick = initChatKit;
      }}
    }}
  }}

  // Initialize on DOM ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => {{
      initializeTheme();
      initChatKit();
    }});
  }} else {{
    initializeTheme();
    initChatKit();
  }}

  // Expose retry function
  window.retryChatKit = initChatKit;
}})();
        """,
        defer=True,
    )
    
    return container, error_overlay, init_script


def Header():
    """Header component with theme toggle."""
    return Div(
        Div(
            Span(
                "ChatKit",
                style="font-size: 1.5rem; font-weight: 600;",
            ),
            Button(
                "🌓",
                id="theme-toggle",
                cls="theme-toggle",
                title="Toggle dark mode",
            ),
            cls="container",
            style="display: flex; justify-content: space-between; align-items: center;",
        ),
        cls="header",
        id="header",
    )


def MainLayout(header, chatkit_container, error_overlay):
    """Main layout component."""
    return Div(
        header,
        Div(
            chatkit_container,
            error_overlay,
            cls="main",
        ),
        cls="main-wrapper",
        style="display: flex; flex-direction: column; height: 100vh;",
    )
