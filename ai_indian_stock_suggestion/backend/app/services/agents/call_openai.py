from openai import OpenAI

from ai_indian_stock_suggestion.backend.app.config import OPENAI_API_KEY

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to your environment or .env file."
        )
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def chat_completion(
    *,
    system_prompt: str,
    user_content: str,
    model: str,
    temperature: float,
) -> str:
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    text = response.choices[0].message.content
    return (text or "").strip()
