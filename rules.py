"""
rules.py
--------
Represents the Declarative Rule Base of the system.

Each Rule is a simple symbolic production of the form:

    IF <if_concept> THEN <then_concept>

Rules are intentionally kept simple (single antecedent, single consequent)
so that the forward-chaining algorithm in reasoning_engine.py stays easy
to explain, while still being able to produce multi-step reasoning chains
when several rules are linked together.
"""

from database import Database


class Rule:
    """A simple data holder representing one declarative rule."""

    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.if_concept = row["if_concept"]
        self.then_concept = row["then_concept"]
        self.description = row["description"]
        self.created_at = row["created_at"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "if_concept": self.if_concept,
            "then_concept": self.then_concept,
            "description": self.description,
            "created_at": self.created_at,
        }

    def __repr__(self):
        return f"<Rule {self.name}: IF {self.if_concept} THEN {self.then_concept}>"


class RuleManager:
    """High level API for working with rules stored in the database."""

    def __init__(self, db: Database):
        self.db = db

    def add_rule(self, name, if_concept, then_concept, description=""):
        if not name or not name.strip():
            raise ValueError("Rule name cannot be empty.")
        if not if_concept or not if_concept.strip():
            raise ValueError("IF-concept cannot be empty.")
        if not then_concept or not then_concept.strip():
            raise ValueError("THEN-concept cannot be empty.")
        return self.db.add_rule(name, if_concept, then_concept, description)

    def update_rule(self, rule_id, name, if_concept, then_concept, description=""):
        if not name or not name.strip():
            raise ValueError("Rule name cannot be empty.")
        if not if_concept or not if_concept.strip():
            raise ValueError("IF-concept cannot be empty.")
        if not then_concept or not then_concept.strip():
            raise ValueError("THEN-concept cannot be empty.")
        self.db.update_rule(rule_id, name, if_concept, then_concept, description)

    def delete_rule(self, rule_id):
        self.db.delete_rule(rule_id)

    def get_all_rules(self):
        return [Rule(row) for row in self.db.get_all_rules()]

    def get_rule_by_id(self, rule_id):
        row = self.db.get_rule_by_id(rule_id)
        return Rule(row) if row else None
