from groq import Groq

from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


def chat_completion(
    messages: list[dict],
    model: str,
    tools: list[dict] | None = None,
    temperature: float = 0.3,
    response_format: dict | None = None,
):
    """Wrapper unique autour de l'API Groq — chat, sensibilisation ESS,
    ET l'agent d'analyse (via `tools` pour le tool calling).

    `temperature` : 0.3 par défaut (chat), mais l'agent d'analyse passe 0.0
    — une analyse de dossier doit être reproductible, pas créative.
    `response_format` : ex. {"type": "json_object"} pour forcer une sortie
    JSON valide (utilisé par la passe de réparation du verdict, cf.
    agent.py::_run_agent_loop)."""
    kwargs = {"model": model, "messages": messages, "temperature": temperature}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    if response_format:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message


def chat_completion_stream(messages: list[dict], model: str):
    """Variante streaming, réservée au chat conversationnel (pas de tool
    calling ici — l'agent d'analyse reste sur l'appel bloquant ci-dessus).
    Yield les fragments de texte au fur et à mesure de leur génération."""
    stream = client.chat.completions.create(
        model=model, messages=messages, temperature=0.3, stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
