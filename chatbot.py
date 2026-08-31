"""
chatbot.py
----------
Ties everything together: takes free-text user input, matches it against
the Knowledge Base, runs the Reasoning Engine (forward chaining), and
produces a natural-language response plus a stored "reasoning trace" that
the interface can display via the "Explain Reasoning" feature.

Also handles simple conversational intents (greetings, thanks, help,
about, mood) and two extra tools: quick-question suggestions and a
multi-answer "security checklist" scorer that runs several concepts
through the same forward-chaining engine at once.
"""

import random
import re
from datetime import datetime

from database import Database
from knowledge_base import KnowledgeBase
from rules import RuleManager
from reasoning_engine import ReasoningEngine
from mood import detect_mood, time_greeting

GREETING_PATTERNS = [r"\bhi\b", r"\bhello\b", r"\bhey\b", r"\bhowdy\b", r"\byo\b",
                      r"\bgood morning\b", r"\bgood evening\b", r"\bgood afternoon\b"]
THANKS_PATTERNS = [r"\bthank", r"\bthanks\b", r"\bappreciate\b", r"\bcheers\b"]
HELP_PATTERNS = [r"\bhelp\b", r"\bwhat can you do\b", r"\bcommands\b", r"\bfeatures\b"]
ABOUT_PATTERNS = [r"\babout\b", r"\bwho are you\b", r"\bwhat are you\b"]
BYE_PATTERNS = [r"\bbye\b", r"\bgoodbye\b", r"\bsee you\b", r"\bexit\b", r"\bquit\b"]

# A curated, friendlier set of quick-question chips shown in the UI -
# separate from the raw keyword list so the wording reads naturally.
QUICK_QUESTIONS = [
    "Is a strong password really necessary?",
    "Should I enable two-factor authentication?",
    "Is public Wi-Fi safe to use?",
    "Why should I install antivirus software?",
    "What happens if I never update my software?",
    "Should I use a VPN?",
    "Is it risky to skip backups?",
    "What if I get a phishing email?",
    "Are password managers worth it?",
    "What is juice jacking?",
    "Should I worry about ransomware?",
    "Do I need a firewall at home?",
]


class Chatbot:
    """The conversational front-end of the Declarative Rules / Symbolic
    Reasoning engine."""

    def __init__(self, db: Database):
        self.db = db
        self.kb = KnowledgeBase(db)
        self.rule_manager = RuleManager(db)
        self.engine = ReasoningEngine(self.kb, self.rule_manager)
        self.last_result = None      # last ReasoningResult, for "Explain Reasoning"
        self.last_matched = []       # concepts directly matched from the last message
        self.last_user_message = ""

    # ------------------------------------------------------------------
    def _matches_any(self, text, patterns):
        return any(re.search(p, text) for p in patterns)

    # ------------------------------------------------------------------
    def get_response(self, user_text: str):
        """Main entry point. Returns a dict with the bot's reply plus
        metadata (mood, matched concepts, reasoning trace) for the UI."""

        if user_text is None or not user_text.strip():
            raise ValueError("Message cannot be empty.")

        cleaned = user_text.strip()
        lower = cleaned.lower()
        self.last_user_message = cleaned

        mood_key, mood_emoji, mood_prefix, mood_accent = detect_mood(cleaned)

        # Log the user's message in conversation history
        self.db.add_conversation("user", cleaned, mood_key)

        response = None
        trace = None
        matched = []

        # --- Simple conversational intents -----------------------------
        if self._matches_any(lower, GREETING_PATTERNS):
            greet_text, greet_emoji, _ = time_greeting()
            response = (f"Hey there {greet_emoji}! I'm SmartRuleAI, a rule-based cybersecurity "
                        "assistant. Ask me about passwords, two-factor authentication, public "
                        "Wi-Fi, antivirus software, backups, phishing, and more — I'll reason "
                        "through the consequences using my declarative rule base.")
            self._reset_trace()

        elif self._matches_any(lower, THANKS_PATTERNS):
            response = "You're welcome! Let me know if you'd like me to reason about another topic."
            self._reset_trace()

        elif self._matches_any(lower, HELP_PATTERNS):
            response = (
                "I can help you explore cybersecurity concepts using symbolic reasoning.\n\n"
                "Try asking things such as:\n"
                "  - \"Is a strong password good?\"\n"
                "  - \"What happens if I use a weak password?\"\n"
                "  - \"Should I enable two-factor authentication?\"\n"
                "  - \"Is public Wi-Fi safe?\"\n"
                "  - \"Why should I install antivirus software?\"\n\n"
                "After I answer, open 'Explain reasoning' to see the exact chain of facts and "
                "rules that led to my conclusion. You can also try the Security Checklist tool "
                "in the sidebar for a full score, or browse the Knowledge Base and Rule Base."
            )
            self._reset_trace()

        elif self._matches_any(lower, ABOUT_PATTERNS):
            response = ("I am SmartRuleAI - a chatbot built on Declarative Rules and Symbolic "
                        "Reasoning. Instead of a black-box AI model, I use an explicit Knowledge "
                        "Base of facts and an explicit Rule Base, and I derive new conclusions "
                        "using forward-chaining inference, so every answer I give can be fully "
                        "explained.")
            self._reset_trace()

        elif self._matches_any(lower, BYE_PATTERNS):
            response = "Goodbye! Stay safe online. 👋"
            self._reset_trace()

        else:
            # --- Symbolic reasoning path -------------------------------------
            matched = self.kb.match_concepts(cleaned)
            self.last_matched = matched

            if not matched:
                response = (
                    "I couldn't match that to anything in my knowledge base yet. "
                    "Try asking about passwords, two-factor authentication, public Wi-Fi, "
                    "antivirus software, backups, VPNs, phishing, or ransomware - "
                    "or add a new fact/rule from the Knowledge Base panel!"
                )
                self._reset_trace()
            else:
                result = self.engine.forward_chain(matched)
                self.last_result = result
                trace = result.to_dict()
                response = self._build_response(matched, result)

        # Empathetic prefix only makes sense on the reasoning / fallback
        # path, never on short conversational replies like "thanks".
        if mood_prefix and matched:
            response = f"{mood_prefix}\n\n{response}"

        self.db.add_conversation("bot", response, mood_key)

        return {
            "response": response,
            "mood": mood_key,
            "mood_emoji": mood_emoji,
            "mood_accent": mood_accent,
            "matched": matched,
            "trace": trace,
        }

    # ------------------------------------------------------------------
    def _reset_trace(self):
        self.last_result = None
        self.last_matched = []

    # ------------------------------------------------------------------
    def _build_response(self, matched, result):
        matched_labels = ", ".join(c.replace("_", " ") for c in matched)
        lines = [f"I recognized the following in your message: {matched_labels}."]

        if result.has_new_conclusions():
            lines.append("\nUsing my declarative rules, I derived the following conclusion(s):")
            for concept in result.new_concepts:
                fact = self.kb.get_fact_by_concept(concept)
                if fact:
                    lines.append(f"  -> {fact.statement}")
            lines.append("\nOpen 'Explain reasoning' to see the full step-by-step chain.")
        else:
            lines.append("\nI know this concept, but no additional rules currently apply to it. "
                         "You can add a new rule from the Rule Base panel to extend my reasoning.")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def get_history(self):
        return self.db.get_all_conversations()

    def clear_history(self):
        self.db.clear_conversations()
        self._reset_trace()

    def search_history(self, keyword):
        return self.db.search_conversations(keyword)

    # ------------------------------------------------------------------
    # Extra tools
    # ------------------------------------------------------------------
    def random_tip(self):
        facts = self.kb.get_all_facts()
        if not facts:
            return None
        return random.choice(facts)

    def quick_questions(self, n=6):
        return random.sample(QUICK_QUESTIONS, k=min(n, len(QUICK_QUESTIONS)))

    def run_checklist(self, answers: dict):
        """Run a batch of checklist answers through the same forward-chaining
        engine used by chat. `answers` maps a checklist item id straight to
        the concept that should be asserted (e.g. {'password': 'strong_password'}).
        Returns a dict with a score, a rating, the full reasoning result, and
        targeted recommendations for every risky concept that was asserted or
        derived.
        """
        initial_concepts = [c for c in answers.values() if c]
        if not initial_concepts:
            raise ValueError("No checklist answers were provided.")

        result = self.engine.forward_chain(initial_concepts)

        good = sum(1 for step in result.chain if step.polarity == "good")
        risk = sum(1 for step in result.chain if step.polarity == "risk")
        total = good + risk
        score = round((good / total) * 100) if total else 0

        if score >= 85:
            rating = "Excellent"
        elif score >= 65:
            rating = "Good"
        elif score >= 40:
            rating = "Needs improvement"
        else:
            rating = "At risk"

        recommendations = []
        for step in result.chain:
            if step.polarity == "risk":
                recommendations.append({
                    "concept": step.concept,
                    "label": step.concept.replace("_", " ").capitalize(),
                    "statement": step.statement,
                })

        self.db.add_conversation(
            "user", f"[Security checklist submitted - {len(initial_concepts)} answers]", "neutral")
        self.db.add_conversation(
            "bot", f"[Security checklist result - score {score}% ({rating})]", "neutral")

        return {
            "score": score,
            "rating": rating,
            "good_count": good,
            "risk_count": risk,
            "trace": result.to_dict(),
            "recommendations": recommendations,
        }
