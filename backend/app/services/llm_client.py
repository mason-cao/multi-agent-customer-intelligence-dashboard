"""
Unified LLM client with provider adapters and mock mode.

Modes (auto-selected by available keys):
  - mock:      No API keys needed. Returns deterministic canned responses.
               Always used when no keys are set, or via LLMClient(mock=True).
  - anthropic: Activated when ANTHROPIC_API_KEY is set.
  - openai:    Activated when OPENAI_API_KEY is set.

Usage:
    from app.services.llm_client import LLMClient

    client = LLMClient()                  # auto-detects mode
    client = LLMClient(mock=True)         # force mock mode
    resp = client.complete(
        prompt="Analyze this customer",
        system="You are a data analyst",
        prompt_type="explanation",         # selects canned response in mock mode
        json_mode=True,                    # request JSON output
    )
    print(resp.content, resp.tokens_used, resp.model)
"""

import json
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------
@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    model: str
    raw_json: Optional[dict] = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Mock responses — keyed by prompt_type
# ---------------------------------------------------------------------------
MOCK_RESPONSES = {
    "sentiment": json.dumps({
        "sentiment_score": 0.2,
        "sentiment_label": "positive",
        "emotions": ["satisfaction"],
        "topics": ["product_quality"],
        "summary": "Customer expressed general satisfaction with the product.",
    }),
    "sentiment_batch": json.dumps([
        {
            "sentiment_score": 0.2,
            "sentiment_label": "positive",
            "emotions": ["satisfaction"],
            "topics": ["product_quality"],
            "summary": "Customer expressed general satisfaction with the product.",
        }
    ]),
    "explanation": (
        "This customer is at elevated risk primarily due to declining login "
        "frequency over the past 30 days and an unresolved billing support ticket."
    ),
    "narrative": json.dumps({
        "executive_summary": (
            "Luminosity Analytics serves 5,000 customers generating $7.3M in total "
            "revenue. The overall churn rate stands at 14.2%, with the At Risk "
            "segment showing a 3.2x higher churn rate than Champions. Sentiment "
            "analysis reveals that billing confusion and performance concerns are "
            "the top negative themes. The platform experienced elevated support "
            "volume during Q3 2024, consistent with the reported outage window. "
            "Mid-market customers represent the highest concentration of at-risk "
            "revenue. Engagement scores have stabilized in Q1 2025, suggesting "
            "recovery from the Q3 disruption. Key recommendation: prioritize "
            "retention outreach to the 47 high-value At Risk customers representing "
            "an estimated $180K in monthly recurring revenue."
        ),
        "key_metrics": [
            {"label": "Total Customers", "value": 5000, "trend": 0.03},
            {"label": "Monthly Revenue", "value": 425000, "trend": 0.05},
            {"label": "Churn Rate", "value": 0.142, "trend": -0.01},
            {"label": "Avg Sentiment", "value": 0.35, "trend": 0.08},
        ],
        "highlights": [
            "Engagement scores recovered to pre-outage levels in Q1 2025.",
            "Champions segment grew by 8% quarter-over-quarter.",
            "Support ticket resolution time improved by 15%.",
        ],
        "concerns": [
            "Mid-market At Risk segment has 3.2x average churn rate.",
            "Billing-related tickets increased 22% in the last 30 days.",
            "47 high-value customers are in the Critical risk tier.",
        ],
    }),
    "recommendation": json.dumps([
        {
            "target_type": "segment",
            "target_id": "at_risk",
            "action": "Launch a personalized check-in campaign for the 23 mid-market At Risk customers, focusing on billing confusion resolution and dedicated account manager assignment.",
            "rationale": "45% of At Risk customers mentioned billing issues in support tickets, and this segment has 3.2x the average churn rate.",
            "priority": "urgent",
            "expected_impact": "Estimated 15-20% reduction in churn for targeted customers, preserving ~$36K MRR.",
            "category": "retention",
        },
        {
            "target_type": "segment",
            "target_id": "champions",
            "action": "Introduce an early-access beta program for the Champions segment to increase feature adoption and strengthen loyalty.",
            "rationale": "Champions have the highest engagement but feature adoption plateaued at 7.2 features avg. Early access drives deeper usage.",
            "priority": "medium",
            "expected_impact": "5-10% increase in feature adoption, supporting upsell conversations.",
            "category": "upsell",
        },
    ]),
    "query": json.dumps({
        "answer": "Based on the available data, there are 12 enterprise customers with negative average sentiment scores who have renewal dates within the next 90 days.",
        "sources": [
            {"type": "sentiment_results", "id": "agg", "excerpt": "12 enterprise customers with avg sentiment < 0"},
            {"type": "subscriptions", "id": "agg", "excerpt": "Renewal dates between now and 90 days out"},
        ],
        "confidence": "medium",
        "sql_generated": "SELECT c.name, AVG(sr.sentiment_score) ... (mock)",
        "visualization_suggestion": "bar_chart",
    }),
    "anomaly_explanation": (
        "Revenue on this date was significantly above the 30-day rolling average. "
        "This coincides with the quarterly enterprise renewal cycle and a seasonal "
        "uptick in new subscriptions."
    ),
    "default": "This is a mock LLM response for development. Connect an API key to get real results.",
}


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------
class _AnthropicAdapter:
    """Wraps the Anthropic Python SDK."""

    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
    ) -> LLMResponse:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return LLMResponse(
            content=content,
            tokens_used=tokens,
            model=response.model,
        )


class _OpenAIAdapter:
    """Wraps the OpenAI Python SDK."""

    def __init__(self, api_key: str):
        import openai
        self._client = openai.OpenAI(api_key=api_key)

    def complete(
        self,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
        json_mode: bool = False,
    ) -> LLMResponse:
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        )
        choice = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return LLMResponse(
            content=choice or "",
            tokens_used=tokens,
            model=model,
        )


class _MockAdapter:
    """Returns deterministic canned responses. No network calls."""

    def complete(
        self,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
        prompt_type: str = "default",
    ) -> LLMResponse:
        content = MOCK_RESPONSES.get(prompt_type, MOCK_RESPONSES["default"])
        # Simulate token count from content length
        tokens = max(10, len(content) // 4)
        return LLMResponse(
            content=content,
            tokens_used=tokens,
            model="mock",
        )


# ---------------------------------------------------------------------------
# Unified client
# ---------------------------------------------------------------------------
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
    "mock": "mock",
}


class LLMClient:
    """
    Unified LLM client. Auto-selects provider from available API keys.

    Priority: mock (if forced) > anthropic > openai > mock (fallback).
    """

    def __init__(self, mock: bool = False):
        self._adapter = None
        self._provider = "mock"
        self._total_tokens = 0

        if mock:
            self._adapter = _MockAdapter()
            self._provider = "mock"
        elif settings.anthropic_api_key:
            try:
                self._adapter = _AnthropicAdapter(settings.anthropic_api_key)
                self._provider = "anthropic"
            except Exception as e:
                logger.warning("anthropic_init_failed", error=str(e))
                self._adapter = _MockAdapter()
        elif settings.openai_api_key:
            try:
                self._adapter = _OpenAIAdapter(settings.openai_api_key)
                self._provider = "openai"
            except Exception as e:
                logger.warning("openai_init_failed", error=str(e))
                self._adapter = _MockAdapter()
        else:
            self._adapter = _MockAdapter()

        logger.info("llm_client_initialized", provider=self._provider)

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def is_mock(self) -> bool:
        return self._provider == "mock"

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    def default_model(self) -> str:
        return DEFAULT_MODELS[self._provider]

    def complete(
        self,
        prompt: str,
        system: str = "You are a helpful data analyst.",
        model: Optional[str] = None,
        max_tokens: int = 2048,
        json_mode: bool = False,
        prompt_type: str = "default",
    ) -> LLMResponse:
        """
        Send a completion request.

        Args:
            prompt: The user message / main prompt content.
            system: System instruction.
            model: Model ID. If None, uses provider default.
            max_tokens: Max tokens in response.
            json_mode: If True, request JSON output from the model.
            prompt_type: Used in mock mode to select canned response.
                         Ignored by live providers.
        """
        resolved_model = model or self.default_model()

        if self.is_mock:
            resp = self._adapter.complete(
                prompt=prompt,
                system=system,
                model=resolved_model,
                max_tokens=max_tokens,
                prompt_type=prompt_type,
            )
            self._total_tokens += resp.tokens_used
            return resp

        # Live provider — retry up to 2 times on transient errors
        last_error = None
        for attempt in range(3):
            try:
                if self._provider == "anthropic":
                    resp = self._adapter.complete(
                        prompt=_maybe_add_json_instruction(prompt, json_mode),
                        system=system,
                        model=resolved_model,
                        max_tokens=max_tokens,
                    )
                else:  # openai
                    resp = self._adapter.complete(
                        prompt=prompt,
                        system=system,
                        model=resolved_model,
                        max_tokens=max_tokens,
                        json_mode=json_mode,
                    )

                # If json_mode, validate the response parses
                if json_mode:
                    resp.raw_json = _parse_json(resp.content)
                    if resp.raw_json is None and attempt < 2:
                        logger.warning(
                            "json_parse_retry",
                            attempt=attempt,
                            content_preview=resp.content[:200],
                        )
                        prompt = (
                            prompt
                            + "\n\nIMPORTANT: Your previous response was not valid JSON. "
                            "Please respond with ONLY valid JSON, no markdown fencing."
                        )
                        continue

                self._total_tokens += resp.tokens_used
                logger.info(
                    "llm_complete",
                    provider=self._provider,
                    model=resp.model,
                    tokens=resp.tokens_used,
                    json_mode=json_mode,
                )
                return resp

            except Exception as e:
                last_error = e
                is_transient = _is_transient_error(e)
                logger.warning(
                    "llm_error",
                    provider=self._provider,
                    attempt=attempt,
                    transient=is_transient,
                    error=str(e),
                )
                if not is_transient or attempt == 2:
                    break
                time.sleep(2 ** attempt)

        # All retries exhausted — raise
        raise RuntimeError(
            f"LLM call failed after 3 attempts ({self._provider}): {last_error}"
        ) from last_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _maybe_add_json_instruction(prompt: str, json_mode: bool) -> str:
    """Anthropic doesn't have a native JSON mode, so we add an instruction."""
    if not json_mode:
        return prompt
    return (
        prompt
        + "\n\nRespond with ONLY valid JSON. No markdown fencing, no explanation outside the JSON."
    )


def _parse_json(text: str) -> Optional[dict]:
    """Try to parse JSON from LLM output, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` fencing
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    error_str = str(error).lower()
    transient_signals = [
        "rate_limit",
        "rate limit",
        "429",
        "timeout",
        "timed out",
        "500",
        "502",
        "503",
        "overloaded",
        "capacity",
    ]
    return any(signal in error_str for signal in transient_signals)
