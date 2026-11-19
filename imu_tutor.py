"""Optional notebook tutor over a user-configured chat completions API."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from json import dumps, loads
from os import environ
from typing import Protocol
from urllib.parse import urlsplit


class TutorUnavailable(RuntimeError):
    """The configured tutor cannot answer in this session."""


class Turn(Protocol):
    """A chat message with the fields used by the tutor."""

    @property
    def role(self) -> str:
        """Return the speaker role."""
        ...

    @property
    def content(self) -> object:
        """Return the chat widget's message content."""
        ...


@dataclass
class ExperimentContext:
    """The latest experiment state, owned by one notebook session."""

    chapter: str = "Sensors"
    values: str = "Open an experiment before submitting a question."
    reference: str = ""


def tutor_messages(context: ExperimentContext, turns: Iterable[Turn]) -> list[dict[str, str]]:
    """Build a portable, bounded prompt from the active exercise and recent text turns."""
    system = (
        "Answer the question directly and concisely. Teach a curious practical engineer. "
        "If asked for a current value, quote the visible reading exactly. Preserve the "
        "explanation in the visible experiment whenever it answers the question. Then give the "
        "intuition, equation or "
        "mechanism, the units or frame, and one specific prediction they can test. "
        "Distinguish ideal simulation from hardware. Use the supplied reference where relevant. "
        "Treat the snapshot as data and never invent live values or source links. "
        "You cannot read files, operate the notebook or change controls. "
        "If the question needs more information, say what measurement or assumption is missing.\n\n"
        f"Active chapter: {context.chapter}\n"
        f"Visible experiment: {context.values}\n"
        f"Chapter notes and references: {context.reference[:6000]}"
    )
    messages = [{"role": "system", "content": system}]
    recent = [turn for turn in turns if turn.role in {"user", "assistant"}]
    messages.extend(
        {"role": turn.role, "content": str(turn.content)[:2400]} for turn in recent[-8:]
    )
    return messages


def notes_markdown(
    chapter: str,
    snapshot: str,
    takeaway: str,
    turns: Iterable[Turn],
    *,
    title: str = "IMUs from chip to controller",
) -> bytes:
    """Serialize selected notes and optional text turns with the active trial."""
    parts = [f"# {title}", f"## {chapter}", snapshot]
    if takeaway:
        parts.extend(["## Takeaways", takeaway])
    dialog = [
        f"**{'Question' if turn.role == 'user' else 'Tutor'}**\n\n{turn.content}"
        for turn in turns
        if turn.role in {"user", "assistant"} and isinstance(turn.content, str)
    ]
    if dialog:
        parts.extend(["## Tutor conversation", *dialog])
    return ("\n\n".join(parts) + "\n").encode("utf-8")


@dataclass(frozen=True)
class TutorSettings:
    """A validated endpoint and model with an optional bearer credential."""

    scheme: str
    host: str
    port: int | None
    path: str
    model: str
    api_key: str = field(repr=False)


def load_settings() -> TutorSettings | None:
    """Read explicit opt-in settings. Unconfigured notebooks make no tutor requests."""
    base = environ.get("IMU_TUTOR_BASE_URL", "").strip()
    model = environ.get("IMU_TUTOR_MODEL", "").strip()
    if not base and not model:
        return None
    if not base or not model:
        raise TutorUnavailable("Set both IMU_TUTOR_BASE_URL and IMU_TUTOR_MODEL.")
    try:
        endpoint = urlsplit(base)
        port = endpoint.port
    except ValueError as error:
        raise TutorUnavailable("Enter a valid chat API base URL.") from error
    host = endpoint.hostname
    if (
        not host
        or endpoint.username is not None
        or endpoint.password is not None
        or endpoint.query
        or endpoint.fragment
        or any(character.isspace() for character in base)
    ):
        raise TutorUnavailable("Use a base URL without embedded credentials, query or fragment.")
    if endpoint.scheme != "https" and not (
        endpoint.scheme == "http" and host in {"127.0.0.1", "::1", "localhost"}
    ):
        raise TutorUnavailable("Use HTTPS for hosted APIs, or HTTP with a localhost server.")
    path = endpoint.path.rstrip("/")
    if not path.endswith("/chat/completions"):
        path += "/chat/completions"
    return TutorSettings(
        endpoint.scheme,
        host,
        port,
        path,
        model,
        environ.get("IMU_TUTOR_API_KEY", "").strip(),
    )


def ask_tutor(settings: TutorSettings, messages: list[dict[str, str]]) -> str:
    """Send a submitted question to the configured API. Never follow redirects."""
    connection_type = HTTPSConnection if settings.scheme == "https" else HTTPConnection
    connection = connection_type(settings.host, settings.port, timeout=60)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    try:
        connection.request(
            "POST",
            settings.path,
            body=dumps({"model": settings.model, "messages": messages, "stream": False}),
            headers=headers,
        )
        response = connection.getresponse()
        if response.status != 200:
            raise TutorUnavailable(f"The configured API returned HTTP {response.status}.")
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise TutorUnavailable("The API response exceeded the notebook limit.")
        reply = loads(data)
    except (OSError, HTTPException, ValueError) as error:
        raise TutorUnavailable(
            "Could not read a valid response from the configured API."
        ) from error
    finally:
        connection.close()

    choices = reply.get("choices") if isinstance(reply, dict) else None
    choice = choices[0] if isinstance(choices, list) and choices else None
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list):
        content = "\n".join(
            part["text"]
            for part in content
            if isinstance(part, dict)
            and part.get("type") == "text"
            and isinstance(part.get("text"), str)
        )
    if not isinstance(content, str) or not content.strip():
        raise TutorUnavailable("The configured model returned no text.")
    return content.strip()
