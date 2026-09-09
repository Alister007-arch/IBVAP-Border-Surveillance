import gradio as gr
from main import app as fastapi_app  # Imports your existing FastAPI app instance

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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
