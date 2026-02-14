from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class Message:
    content: str
    metadata: Dict[str, Any]
