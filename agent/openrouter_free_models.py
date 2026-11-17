
"""Получение актуального списка бесплатных моделей OpenRouter."""

import requests

from config import API_KEY

API_URL = "https://openrouter.ai/api/v1/models"


def get_free_models():
    headers = {
        "Accept": "application/json",
    }

    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        response = requests.get(
            API_URL,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Не удалось получить модели OpenRouter: {exc}"
        ) from exc
    except ValueError as exc:
        raise RuntimeError(
            "OpenRouter вернул некорректный JSON"
        ) from exc

    models = []

    for model in data.get("data", []):
        model_id = model.get("id", "")

        if not model_id.endswith(":free"):
            continue

        name = model.get("name") or model_id
        context = model.get("context_length") or 0

        models.append((name, model_id, context))

    return sorted(
        models,
        key=lambda item: item[0].lower(),
    )


def main():
    models = get_free_models()

    if not models:
        print("Бесплатные модели не найдены.")
        return

    print(f"\nНайдено бесплатных моделей: {len(models)}\n")

    print(
        f"{'№':>3} | "
        f"{'Название модели':45} | "
        f"{'Код модели':65} | "
        f"{'Контекст':>10}"
    )

    print("-" * 135)

    for number, (name, model_id, context) in enumerate(
        models, start=1
    ):
        print(
            f"{number:>3} | "
            f"{name[:45]:45} | "
            f"{model_id[:65]:65} | "
            f"{context:>10}"
        )


if __name__ == "__main__":
    main()
