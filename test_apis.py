"""Prueba mínima de conectividad para los proveedores configurados."""
from pathlib import Path

import requests
import yaml


def test_gemini(config: dict) -> None:
    provider = config["providers"]["gemini"]
    model = provider.get("model", "gemini-3.6-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        params={"key": provider.get("api_key", "")},
        json={"contents": [{"parts": [{"text": "Say hello in Spanish."}]}]},
        timeout=30,
    )
    print(f"Gemini [{model}]: HTTP {response.status_code}")
    if not response.ok:
        print(response.text[:500])
        if response.status_code == 404:
            models_response = requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": provider.get("api_key", "")},
                timeout=30,
            )
            if models_response.ok:
                models = models_response.json().get("models", [])
                supported = [
                    item["name"].removeprefix("models/")
                    for item in models
                    if "generateContent" in item.get("supportedGenerationMethods", [])
                ]
                print("Modelos Gemini disponibles para generateContent:")
                print("  " + ", ".join(supported))


def test_deepl(config: dict) -> None:
    provider = config["providers"]["deepl"]
    base_url = provider.get("base_url", "https://api-free.deepl.com/v2").rstrip("/")
    response = requests.post(
        f"{base_url}/translate",
        headers={"Authorization": f"DeepL-Auth-Key {provider.get('api_key', '')}"},
        data={"text": "Hello.", "source_lang": "EN", "target_lang": "ES"},
        timeout=30,
    )
    print(f"DeepL: HTTP {response.status_code}")
    if not response.ok:
        print(response.text[:500])


if __name__ == "__main__":
    config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    test_gemini(config)
    test_deepl(config)