import json
from typing import Optional, Any

from langchain_core.messages import BaseMessage, convert_to_openai_messages
from langchain_core.runnables import RunnableConfig
from langgraph.constants import END
from langgraph.graph.state import (
    CompiledStateGraph,
    Command,
)

from assistant.app.core.config import settings
from assistant.app.core.logging import logger
from assistant.app.core.prompts.__init import load_sts_assist_prompt
from assistant.app.schemas.sts_state import STSChoiceOption, STSDecision, STSAssistGraphState
from assistant.app.services.llm import  LLMService


class STSAssistAgent:
    """Builds and runs the STS assistant graph."""

    def __init__(self):
        """Initialize STS assistant graph dependencies."""
        self.llm_service = LLMService()
        self._graph: Optional[CompiledStateGraph] = None
        logger.info(
            "sts_assist_agent_initialized",
            model=settings.DEFAULT_LLM_MODEL,
            environment=settings.ENVIRONMENT.value,
        )

    @staticmethod
    def _get_session_id(config: RunnableConfig) -> str:
        """Extract thread id from runnable config."""
        return str(config.get("configurable", {}).get("thread_id", "unknown"))

    @staticmethod
    def _normalize_messages(messages: list[Any]) -> list[dict[str, str]]:
        """Convert message payloads to OpenAI-style role/content dicts."""
        normalized: list[dict[str, str]] = []
        allowed_roles = {"system", "user", "assistant"}

        for item in messages:
            if isinstance(item, dict):
                role = item.get("role")
                content = item.get("content")
                if role in allowed_roles and content:
                    normalized.append({"role": str(role), "content": str(content)})
                continue

            if isinstance(item, BaseMessage):
                for payload in convert_to_openai_messages([item]):
                    role = payload.get("role")
                    content = payload.get("content")
                    if role in allowed_roles and content:
                        normalized.append({"role": str(role), "content": str(content)})

        return normalized

    @staticmethod
    def _extract_json_payload(content: str) -> str:
        """Extract a JSON object from plain text or fenced content."""
        stripped = content.strip()

        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if "\n" in stripped:
                stripped = stripped.split("\n", 1)[1]
            if "\n```" in stripped:
                stripped = stripped.rsplit("\n```", 1)[0]

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            return stripped[start: end + 1]

        return stripped

    @staticmethod
    def _safe_fallback_decision(options: list[STSChoiceOption], reason: str) -> STSDecision:
        """Build a deterministic fallback decision."""
        option_ids = [option.option_id for option in options]
        chosen = option_ids[0] if option_ids else None
        return STSDecision(
            chosen_option_id=chosen,
            reasoning=reason,
            confidence=0.2 if chosen else 0.0,
            risk_tags=["fallback_used"],
            candidate_rankings=option_ids,
        )

    def _parse_decision(self, content: str, options: list[STSChoiceOption]) -> STSDecision:
        """Parse model output into a validated decision object."""
        option_ids = [option.option_id for option in options]

        try:
            payload = self._extract_json_payload(content)
            parsed = json.loads(payload)
            decision = STSDecision.model_validate(parsed)
        except Exception as error:
            logger.warning(
                "sts_assist_decision_parse_failed",
                error=str(error),
            )
            return self._safe_fallback_decision(options, "I could not parse model output, so I used a safe fallback.")

        if decision.chosen_option_id and decision.chosen_option_id not in option_ids:
            logger.warning(
                "sts_assist_invalid_choice_id",
                chosen_option_id=decision.chosen_option_id,
            )
            decision = decision.model_copy(update={"chosen_option_id": option_ids[0] if option_ids else None})

        if not decision.candidate_rankings:
            decision = decision.model_copy(update={"candidate_rankings": option_ids})
        else:
            filtered_rankings = [option_id for option_id in decision.candidate_rankings if option_id in option_ids]
            decision = decision.model_copy(update={"candidate_rankings": filtered_rankings or option_ids})

        return decision

    @staticmethod
    def _build_assistant_text(decision: STSDecision, options: list[STSChoiceOption]) -> str:
        """Build a concise assistant message from the structured decision."""
        labels = {option.option_id: option.label for option in options}

        if not decision.chosen_option_id:
            return decision.reasoning or "I need more context before recommending an option."

        option_label = labels.get(decision.chosen_option_id, decision.chosen_option_id)
        return (
            f"recommended option: {option_label} ({decision.chosen_option_id}). "
            f"reason: {decision.reasoning} "
            f"confidence: {decision.confidence:.2f}"
        )

    async def _observe(self, state: STSAssistGraphState) -> Command:
        """Validate state before invoking the LLM."""
        if state.choice_context is None or not state.choice_context.options:
            decision = self._safe_fallback_decision(
                [],
                "I need a non-empty choice_context.options list to make a recommendation.",
            )
            return Command(
                update={
                    "decision": decision.model_dump(),
                    "messages": [{"role": "assistant", "content": decision.reasoning}],
                },
                goto=END,
            )

        return Command(goto="suggest")

    async def _suggest(self, state: STSAssistGraphState, config: RunnableConfig) -> Command:
        """Generate a recommendation for the current choice context."""
        session_id = self._get_session_id(config)
        options = state.choice_context.options if state.choice_context else []

        system_prompt = load_sts_assist_prompt(
            long_term_memory=state.long_term_memory or "No long-term memory available.",
            run_snapshot=json.dumps(state.run_meta.model_dump(), ensure_ascii=True),
            player_snapshot=json.dumps(state.player.model_dump(), ensure_ascii=True),
            combat_snapshot=json.dumps(state.combat.model_dump(), ensure_ascii=True),
            choice_snapshot=json.dumps(state.choice_context.model_dump() if state.choice_context else {},
                                       ensure_ascii=True),
        )

        normalize_messages = self._normalize_messages(state.messages)
        if not normalize_messages:
            normalized_messages = [
                {
                    "role": "user",
                    "content": "Analyze the current choice context and recommend the best option."
                }
            ]

        try:
            response = await self.llm_service.call([
                    {"role": "system", "content": system_prompt},
                    *normalized_messages,
                ])
        finally:
