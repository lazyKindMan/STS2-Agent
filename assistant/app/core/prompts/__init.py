import datetime
import os

from assistant.app.core.config import settings


def _load_prompt(filename: str, **kwargs) -> str:
    """Load a prompt template from this package."""
    with open(os.path.join(os.path.dirname(__file__), filename), "r", encoding="utf-8") as file:
        return file.read().format(
            agent_name=settings.PROJECT_NAME + " Agent",
            current_date_and_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **kwargs,
        )

def load_system_prompt(**kwargs) -> str:
    """Load the default chat system prompt."""
    return _load_prompt("system.md", **kwargs)

def load_sts_assist_prompt(**kwargs) -> str:
    """Load the STS assistant system prompt."""
    return _load_prompt("sts_assist_system.md", **kwargs)