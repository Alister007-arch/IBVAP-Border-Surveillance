import sys
from pathlib import Path
import importlib

# Ensure project root is always in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    gr = importlib.import_module("gradio")
except ImportError:
    gr = None

try:
    from backend.api.app import app as fastapi_app  # Imports your existing FastAPI app instance
except ImportError:
    from api.app import app as fastapi_app


if gr is not None:
    # Minimal UI so Hugging Face Space initializes cleanly
    demo = gr.Interface(
        fn=lambda x: f"Border Surveillance API Status: Active. Echo: {x}",
        inputs="text",
        outputs="text",
        title="Border Surveillance AI Gateway",
        description="FastAPI Backend running on Hugging Face Spaces with 16GB RAM.",
    )

    # Mount FastAPI endpoints directly onto Gradio
    app = gr.mount_gradio_app(fastapi_app, demo, path="/ui")
else:
    app = fastapi_app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
