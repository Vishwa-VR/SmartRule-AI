"""
mood.py
-------
A small, purely declarative (pattern-matching) mood detector, in the same
spirit as the rest of SmartRuleAI: instead of a black-box classifier, mood
is inferred from an explicit table of regex patterns, so the "why did it
think that" question is always answerable.

Two things live here:
  1. detect_mood(text)   - guesses the user's mood from their message
  2. time_greeting(now)  - builds a time-of-day aware greeting
"""

import re
from datetime import datetime

# Ordered by priority: the first matching mood wins.
MOOD_RULES = [
    ("distressed",
     [r"\bhack(ed|er)?\b", r"\bbreach", r"\bstolen\b", r"\bcompromised\b",
      r"\bscared\b", r"\bworried\b", r"\banxious\b", r"\bpanic", r"\bhelp me\b",
      r"\bransomware\b", r"\bfreaking out\b", r"\bterrified\b"],
     "😟", "That sounds stressful — let's sort it out together, one step at a time.",
     "border-color:var(--risk)"),
    ("frustrated",
     [r"\bfrustrat", r"\bannoyed\b", r"\bangry\b", r"\bugh\b", r"\bsick of\b",
      r"\bnot working\b", r"\bhate\b"],
     "😤", "I hear you — let's get this straightened out.", "border-color:var(--amber)"),
    ("tired",
     [r"\btired\b", r"\bexhausted\b", r"\bcan'?t be bothered\b", r"\btoo lazy\b",
      r"\bno energy\b"],
     "😴", "Let's keep this quick and painless.", "border-color:var(--muted)"),
    ("happy",
     [r"\bthanks\b", r"\bthank you\b", r"\bawesome\b", r"\bgreat\b", r"\blove\b",
      r"\bnice\b", r"\bcool\b", r"\bhappy\b", r"\bexcited\b", r"😀|😊|🙂|😄"],
     "😊", "Glad to hear it!", "border-color:var(--safe)"),
    ("curious",
     [r"\bwhy\b", r"\bhow\b", r"\bwhat if\b", r"\bcurious\b", r"\bwonder(ing)?\b"],
     "🤔", "Good question — let's dig in.", "border-color:var(--accent)"),
]

DEFAULT_MOOD = ("neutral", "🙂", None, "border-color:var(--line)")


def detect_mood(text: str):
    """Return (mood_key, emoji, empathetic_prefix_or_None, accent_css)."""
    lower = (text or "").lower()
    for mood_key, patterns, emoji, prefix, accent in MOOD_RULES:
        if any(re.search(p, lower) for p in patterns):
            return mood_key, emoji, prefix, accent
    return DEFAULT_MOOD


def time_greeting(now: datetime = None):
    """Return a (greeting_text, emoji, part_of_day) tuple based on the
    current server time."""
    now = now or datetime.now()
    hour = now.hour

    if 5 <= hour < 12:
        part, emoji = "morning", "🌅"
        text = "Good morning! Ready to lock down your digital life before the day gets busy?"
    elif 12 <= hour < 17:
        part, emoji = "afternoon", "☀️"
        text = "Good afternoon! Let's talk cybersecurity while the coffee's still warm."
    elif 17 <= hour < 22:
        part, emoji = "evening", "🌆"
        text = "Good evening! A great time to review today's security habits."
    else:
        part, emoji = "night", "🌙"
        text = "Burning the midnight oil? I'm here if you want to talk security."

    return text, emoji, part
