import os
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
import base64
from io import BytesIO
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
import time
import uuid

app = FastAPI(title="ShowUI-2B OpenAI Compatible API")

# Model configuration
model_dir = os.path.dirname(os.path.abspath(__file__))
LOCAL_MODEL_PATH = os.path.join(model_dir, "models--showlab--ShowUI-2B")
MODEL_ID = "showlab/ShowUI-2B"
device = "cuda" if torch.cuda.is_available() else "cpu"

# Set max pixels to avoid OOM for large screenshots
# ShowUI-2B/Qwen2-VL specific configuration
min_pixels = 256 * 28 * 28
max_pixels = 1344 * 28 * 28

print(f"Loading model {MODEL_ID} to {device} (Cache: {LOCAL_MODEL_PATH})...")
model = Qwen2VLForConditionalGeneration.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
    trust_remote_code=True,
    cache_dir=LOCAL_MODEL_PATH
)
processor = AutoProcessor.from_pretrained(
    MODEL_ID, 
    min_pixels=min_pixels, 
    max_pixels=max_pixels,
    cache_dir=LOCAL_MODEL_PATH
)
print("Model loaded successfully.")

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7

def decode_image(image_data: str) -> Image.Image:
    if image_data.startswith("data:image"):
        image_data = image_data.split(",")[1]
    
    img_bytes = base64.b64decode(image_data)
    return Image.open(BytesIO(img_bytes))

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "showlab"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # Extract images and text from messages
    # ShowUI-2B is usually used with a single image + query
    start_time = time.time()
    print(f"\n[ShowUI API] Received request for model: {request.model}")
    
    text_query = ""
    images = []
    
    for message in request.messages:
        if isinstance(message.content, str):
            if message.role == "user":
                text_query += message.content + "\n"
        elif isinstance(message.content, list):
            for part in message.content:
                if part.get("type") == "text":
                    text_query += part.get("text", "") + "\n"
                elif part.get("type") == "image_url":
                    image_url = part.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:image"):
                        images.append(decode_image(image_url))
                    else:
                        # Fetch image from URL if needed, but for now assume base64
                        raise HTTPException(status_code=400, detail="Only base64 image_url is supported for now")

    if not images:
        print("[ShowUI API] Error: No image provided in request")
        raise HTTPException(status_code=400, detail="At least one image is required for ShowUI-2B")

    print(f"[ShowUI API] Processing query: \"{text_query.strip()[:50]}...\" with {len(images)} image(s)")

    # Prepare inputs for Qwen2-VL
    # Based on transformers documentation for Qwen2-VL
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": images[-1]}, # Use the last image
                {"type": "text", "text": text_query.strip()},
            ],
        }
    ]

    # Preparation for inference
    print(f"[ShowUI API] Image count: {len(images)}, Image size: {images[-1].size if images else 'N/A'}")
    print(f"[ShowUI API] Text query length: {len(text_query.strip())}")
    print("[ShowUI API] Preparing vision-language inputs...")
    
    # ShowUI-2B/Qwen2-VL specific: Use the standard template
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    print(f"[ShowUI API] Template text length: {len(text)}")
    
    image_inputs, video_inputs = process_vision_info(messages)
    
    print(f"[ShowUI API] image_inputs type: {type(image_inputs)}, length: {len(image_inputs) if isinstance(image_inputs, list) else 'N/A'}")
    if image_inputs:
        print(f"[ShowUI API] First image tensor shape: {image_inputs[0].shape if hasattr(image_inputs[0], 'shape') else 'N/A'}")
    else:
        print("[ShowUI API] WARNING: image_inputs is EMPTY!")

    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    print(f"[ShowUI API] Processed inputs keys: {inputs.keys()}")
    print(f"[ShowUI API] Input shape info - input_ids: {inputs.input_ids.shape}, pixel_values: {inputs.get('pixel_values', {}).shape if 'pixel_values' in inputs else 'N/A'}")
    
    inputs = inputs.to(device)

    # Inference
    print(f"[ShowUI API] Starting model inference on {device} (Input tokens: {inputs.input_ids.shape[1]})...")
    inference_start = time.time()
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs, 
            max_new_tokens=request.max_tokens,
            # 添加一些生成参数以防过早停止
            repetition_penalty=1.1,
            do_sample=False
        )
        
        input_len = inputs.input_ids.shape[1]
        generated_ids_trimmed = [
            out_ids[input_len:] for out_ids in generated_ids
        ]
        
        print(f"[ShowUI API] Generated tokens count: {len(generated_ids_trimmed[0])}")
        
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
    
    inference_duration = time.time() - inference_start
    total_duration = time.time() - start_time
    
    print(f"[ShowUI API] Inference complete in {inference_duration:.2f}s")
    if not output_text.strip():
        print("[ShowUI API] Model response is EMPTY!")
        print(f"[ShowUI API] Generated IDs (first 10): {generated_ids_trimmed[0][:10].tolist()}")
    else:
        print(f"[ShowUI API] Model response: \n{output_text}")
    print(f"[ShowUI API] Total request time: {total_duration:.2f}s")

    # Format response in OpenAI style
    response_id = f"chatcmpl-{uuid.uuid4()}"
    return {
        "id": response_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": output_text,
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": -1, # Token counting not implemented for simplicity
            "completion_tokens": -1,
            "total_tokens": -1
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
