"""
knowledge_base.py
------------------
Represents the Declarative Knowledge Base of the system: a collection of
FACTS expressed as simple (concept -> statement) pairs.

A "concept" is a short symbolic key such as `strong_password`.
A "statement" is the human-readable sentence describing that concept.
"keywords" is a comma separated list of words/phrases that, if found in a
user's message, indicate that this fact/concept is being referred to.
"category" groups facts for the sidebar browser (passwords, network, ...).
"polarity" marks a fact as "good" (protective), "risk" (dangerous), or
"neutral" - used for chat-bubble coloring and the security checklist score.

This module never talks to the interface directly - it only manages facts,
which keeps the "declarative" part of the project cleanly separated from
both the inference logic (reasoning_engine.py) and the interface (app.py).
"""

from database import Database


class Fact:
    """A simple data holder representing one declarative fact/concept."""

    def __init__(self, row):
        self.id = row["id"]
        self.concept = row["concept"]
        self.statement = row["statement"]
        self.keywords = row["keywords"]
        self.category = row["category"] if "category" in row.keys() else "general"
        self.polarity = row["polarity"] if "polarity" in row.keys() else "neutral"
        self.is_base = bool(row["is_base"])
        self.created_at = row["created_at"]

    def keyword_list(self):
        if not self.keywords:
            return [self.concept.replace("_", " ")]
        return [k.strip() for k in self.keywords.split(",") if k.strip()]

    def to_dict(self):
        return {
            "id": self.id,
            "concept": self.concept,
            "label": self.concept.replace("_", " ").capitalize(),
            "statement": self.statement,
            "keywords": self.keywords,
            "category": self.category,
            "polarity": self.polarity,
            "is_base": self.is_base,
            "created_at": self.created_at,
        }

    def __repr__(self):
        return f"<Fact {self.concept}: {self.statement}>"


class KnowledgeBase:
    """High level API for working with facts stored in the database."""

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------
    def add_fact(self, concept, statement, keywords="", is_base=1, category="general", polarity="neutral"):
        if not concept or not concept.strip():
            raise ValueError("Concept name cannot be empty.")
        if not statement or not statement.strip():
            raise ValueError("Statement cannot be empty.")
        return self.db.add_fact(concept, statement, keywords, is_base=is_base,
                                 category=category or "general", polarity=polarity or "neutral")

    def update_fact(self, fact_id, concept, statement, keywords="", category="general", polarity="neutral"):
        if not concept or not concept.strip():
            raise ValueError("Concept name cannot be empty.")
        if not statement or not statement.strip():
            raise ValueError("Statement cannot be empty.")
        self.db.update_fact(fact_id, concept, statement, keywords,
                             category=category or "general", polarity=polarity or "neutral")

    def delete_fact(self, fact_id):
        self.db.delete_fact(fact_id)

    def get_all_facts(self):
        return [Fact(row) for row in self.db.get_all_facts()]

    def get_fact_by_concept(self, concept):
        row = self.db.get_fact_by_concept(concept)
        return Fact(row) if row else None

    def get_fact_by_id(self, fact_id):
        row = self.db.get_fact_by_id(fact_id)
        return Fact(row) if row else None

    # ------------------------------------------------------------------
    # Symbolic matching: turn free-text user input into known concepts
    # ------------------------------------------------------------------
    def match_concepts(self, text: str):
        """Scan free text and return a list of concept keys whose keywords
        appear in the text. This is the bridge between natural language
        chat input and the symbolic reasoning engine.

        Longer keywords are checked first so that a more specific phrase
        (e.g. "no backups") wins over a shorter, looser one when both
        could plausibly appear in the same sentence.
        """
        text = text.lower()
        matched = []
        facts = sorted(self.get_all_facts(),
                        key=lambda f: max((len(k) for k in f.keyword_list()), default=0),
                        reverse=True)
        for fact in facts:
            for kw in fact.keyword_list():
                if kw and kw in text:
                    matched.append(fact.concept)
                    break
        return matched
