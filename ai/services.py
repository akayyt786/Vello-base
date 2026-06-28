import logging
import time
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def call_anthropic(api_key, model, messages, max_tokens, temperature, system=None):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        body["system"] = system
    t0 = time.time()
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        json=body,
        headers=headers,
        timeout=60,
    )
    latency_ms = int((time.time() - t0) * 1000)
    resp.raise_for_status()
    data = resp.json()
    content = data["content"][0]["text"] if data.get("content") else ""
    usage = data.get("usage", {})
    return {
        "content": content,
        "model": model,
        "provider": "anthropic",
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        },
        "latency_ms": latency_ms,
    }


def call_google(api_key, model, messages, max_tokens, temperature, system=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    body = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    t0 = time.time()
    resp = requests.post(url, json=body, headers=headers, timeout=60)
    latency_ms = int((time.time() - t0) * 1000)
    resp.raise_for_status()
    data = resp.json()
    content = ""
    try:
        content = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        pass
    usage_meta = data.get("usageMetadata", {})
    prompt_tokens = usage_meta.get("promptTokenCount", 0)
    completion_tokens = usage_meta.get("candidatesTokenCount", 0)
    return {
        "content": content,
        "model": model,
        "provider": "google",
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "latency_ms": latency_ms,
    }


def get_embeddings_openai(api_key, inputs, model):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {"input": inputs, "model": model}
    t0 = time.time()
    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        json=body,
        headers=headers,
        timeout=30,
    )
    latency_ms = int((time.time() - t0) * 1000)
    resp.raise_for_status()
    data = resp.json()
    embeddings = [item["embedding"] for item in data["data"]]
    usage = data.get("usage", {})
    return {
        "embeddings": embeddings,
        "model": model,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
        "latency_ms": latency_ms,
    }
