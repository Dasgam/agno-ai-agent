"""Получить актуальный перечень бесплатных моделей OpenRouter."""

import requests

from config import API_KEY

API_URL = "https://openrouter.ai/api/v1/models"


def get_free_models():
    headers = {"Accept": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    try:
        response = requests.get(API_URL, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError("Не удалось загрузить список моделей OpenRouter") from exc

    models = []
    for model in payload.get("data", []):
        model_id = model.get("id", "")
        if not model_id.endswith(":free"):
            continue
        models.append((model.get("name") or model_id, model_id, model.get("context_length") or 0))
    return sorted(models, key=lambda row: row[0].lower())


def main():
    models = get_free_models()
    print(f"Бесплатных моделей: {len(models)}")
    for num, (name, ident, context) in enumerate(models, start=1):
        print(f"{num:>3} | {name[:42]:42} | {ident:65} | {context}")


if __name__ == "__main__":
    main()
