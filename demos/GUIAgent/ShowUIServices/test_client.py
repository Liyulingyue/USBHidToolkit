import requests
import base64
import json

def test_showui_service():
    url = "http://localhost:8005/v1/chat/completions"
    
    # Load a sample image (you might need to provide a valid path or use a dummy)
    # Here we just show how to call it
    print("Testing ShowUI Service...")
    
    # Example base64 (empty for illustration)
    # In practice, you'd load an image: 
    # with open("screen.png", "rb") as f: img_b64 = base64.b64encode(f.read()).decode()
    img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==" 
    
    payload = {
        "model": "showlab/ShowUI-2B",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Click on the start button"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Note: Make sure the service is running on http://localhost:8005")
    test_showui_service()
