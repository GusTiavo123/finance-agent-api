import re
import unicodedata

from app.application.ports import GuardrailPort
from app.domain.errors import GuardrailViolationError

INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions|rules|prompts)",
        r"ignor[aá]\s+(todas?\s+)?(las\s+)?(instrucciones|reglas)\s+(anteriores|previas)",
        r"disregard\s+(your|the|all)\s+(system\s+)?(prompt|instructions|rules)",
        r"olvida\s+(todo\s+lo\s+anterior|tus\s+instrucciones|las\s+instrucciones)",
        r"(reveal|show|print|repeat)\b.{0,40}\b(system\s+prompt|initial\s+instructions)",
        r"(muestra|revela|imprime|repite)\b.{0,40}\b(system\s+prompt|prompt\s+del\s+sistema)",
        r"act[uú]a\s+como\s+si\s+no\s+tuvieras\s+(restricciones|reglas|filtros)",
        r"pretend\s+(you\s+have|to\s+have)\s+no\s+(restrictions|rules|guidelines)",
        r"\bjailbreak\b",
        r"\bDAN\s+mode\b",
    )
]


class RuleBasedGuardrail(GuardrailPort):
    def inspect(self, text: str) -> None:
        if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
            raise GuardrailViolationError("control characters are not allowed")
        normalized = _normalize(text)
        for pattern in INJECTION_PATTERNS:
            if pattern.search(normalized):
                raise GuardrailViolationError("the message looks like a prompt injection attempt")


def _normalize(text: str) -> str:
    composed = unicodedata.normalize("NFKC", text)
    return "".join(char for char in composed if unicodedata.category(char) != "Cf")
