"""Sentiment configuration shared by computation and validation."""


TOPIC_KEYWORDS = {
    "billing_confusion": [
        "billing", "invoice", "charge", "payment", "price",
        "pricing", "cost", "subscription", "renew",
    ],
    "performance": [
        "slow", "performance", "speed", "timeout", "latency",
        "loading", "lag", "timing out",
    ],
    "missing_feature": [
        "feature", "missing", "need", "wish", "request",
        "roadmap", "ability", "would like",
    ],
    "onboarding": [
        "onboard", "setup", "getting started", "learning curve",
        "training", "documentation",
    ],
    "data_quality": [
        "data", "sync", "export", "import", "csv",
        "corrupt", "report", "accurate",
    ],
    "integration": [
        "integration", "api", "connect", "third-party",
        "plugin", "webhook", "integrate",
    ],
    "support_quality": [
        "support", "help", "responsive", "resolved",
        "response time", "team",
    ],
    "usability": [
        "ui", "interface", "intuitive", "confusing",
        "user experience", "ux", "design", "easy to use",
    ],
    "reliability": [
        "down", "outage", "crash", "bug", "error",
        "broken", "fail", "issue", "unstable",
    ],
    "security": [
        "security", "password", "auth", "sso",
        "permission", "access", "sign-on",
    ],
    "value": [
        "value", "worth", "roi", "productive",
        "efficiency", "save", "hours",
    ],
    "communication": [
        "communicate", "update", "notify",
        "announcement", "changelog",
    ],
}

EMOTION_KEYWORDS = {
    "frustration": [
        "frustrated", "annoying", "annoyed", "ridiculous",
        "unacceptable", "fed up", "terrible",
    ],
    "satisfaction": [
        "happy", "pleased", "satisfied", "great",
        "excellent", "love", "wonderful",
    ],
    "disappointment": [
        "disappointed", "let down", "expected more",
        "unfortunate", "disappointing",
    ],
    "enthusiasm": [
        "amazing", "impressed", "fantastic",
        "excited", "incredible",
    ],
    "confusion": [
        "confusing", "unclear", "don't understand",
        "complicated", "lost", "steep",
    ],
    "gratitude": [
        "thanks", "thank", "appreciate", "grateful", "helpful",
    ],
    "anxiety": [
        "worried", "concerned", "risk", "afraid",
        "uncertain", "confidence",
    ],
}

POSITIVE_WORDS = frozenset({
    "love", "great", "excellent", "amazing", "fantastic", "impressed",
    "helpful", "responsive", "intuitive", "easy", "wonderful", "perfect",
    "saved", "efficient", "recommend", "best", "appreciate", "better",
})

NEGATIVE_WORDS = frozenset({
    "frustrated", "broken", "terrible", "worst", "awful", "horrible",
    "disappointed", "slow", "crash", "bug", "fail", "failed", "poor",
    "unacceptable", "confusing", "corrupt", "lost", "cancel", "alternative",
})

CATEGORY_SCORES = {
    "cancellation": -0.70,
    "bug_report": -0.50,
    "technical": -0.30,
    "billing": -0.30,
    "feature_request": -0.10,
    "onboarding": 0.00,
}

PRIORITY_MODIFIERS = {
    "urgent": -0.15,
    "high": -0.05,
    "medium": 0.00,
    "low": 0.05,
}

RESOLUTION_MODIFIERS = {
    "resolved": 0.15,
    "open": 0.00,
    "escalated": -0.10,
}

NEGATIVE_THRESHOLD = -0.20

POSITIVE_THRESHOLD = 0.20
