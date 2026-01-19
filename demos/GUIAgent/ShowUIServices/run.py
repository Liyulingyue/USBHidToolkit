import uvicorn
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ShowUI-2B OpenAI Compatible API")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8005, help="Port to bind to")
    args = parser.parse_args()

    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)
