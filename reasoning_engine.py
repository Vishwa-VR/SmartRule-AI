"""
reasoning_engine.py
--------------------
The symbolic reasoning core of SmartRuleAI.

Implements FORWARD CHAINING: starting from a set of known/asserted facts
(concepts), the engine repeatedly scans the rule base and "fires" any rule
whose IF-concept is already known, adding its THEN-concept to the known
set. This repeats until no new facts can be derived (fixpoint reached).

The engine also records a step-by-step REASONING CHAIN so the interface
can later show the user exactly how a conclusion was reached, e.g.:

    Strong password
        -> (Strong Password Rule)
    Difficult to guess
        -> (Guessability Rule)
    Better account protection
"""

from knowledge_base import KnowledgeBase
from rules import RuleManager


class ReasoningStep:
    """One node in a reasoning chain: a concept that became known, and
    (optionally) the rule that produced it."""

    def __init__(self, concept, statement, rule=None, is_initial=False, polarity="neutral"):
        self.concept = concept
        self.statement = statement
        self.rule = rule            # Rule object that fired to produce this step, or None
        self.is_initial = is_initial  # True if this was a directly matched/known fact
        self.polarity = polarity

    def to_dict(self):
        return {
            "concept": self.concept,
            "label": self.concept.replace("_", " ").capitalize(),
            "statement": self.statement,
            "rule": self.rule.to_dict() if self.rule else None,
            "is_initial": self.is_initial,
            "polarity": self.polarity,
        }

    def __repr__(self):
        return f"<Step {self.concept} (initial={self.is_initial})>"


class ReasoningResult:
    """The full outcome of a forward-chaining run."""

    def __init__(self):
        self.chain = []          # ordered list of ReasoningStep
        self.fired_rules = []    # ordered list of Rule objects that fired
        self.known_concepts = set()
        self.new_concepts = []   # concepts derived (not part of the initial input)

    def has_new_conclusions(self):
        return len(self.new_concepts) > 0

    def to_dict(self):
        return {
            "chain": [s.to_dict() for s in self.chain],
            "fired_rules": [r.to_dict() for r in self.fired_rules],
            "known_concepts": sorted(self.known_concepts),
            "new_concepts": self.new_concepts,
        }


class ReasoningEngine:
    """Runs forward-chaining inference over the current facts/rules."""

    def __init__(self, kb: KnowledgeBase, rule_manager: RuleManager):
        self.kb = kb
        self.rule_manager = rule_manager

    def forward_chain(self, initial_concepts):
        """Run forward chaining starting from a list of known concept keys.

        Returns a ReasoningResult object containing the ordered chain of
        reasoning steps, the list of rules that fired, and the final set
        of all known concepts (initial + derived).
        """
        result = ReasoningResult()
        known = set()

        # Step 1: seed the chain with the initial (directly matched) facts
        for concept in initial_concepts:
            fact = self.kb.get_fact_by_concept(concept)
            if fact is None or concept in known:
                continue
            known.add(concept)
            result.chain.append(ReasoningStep(concept, fact.statement, rule=None,
                                               is_initial=True, polarity=fact.polarity))

        rules = self.rule_manager.get_all_rules()

        # Step 2: repeatedly apply rules until no new facts are derived
        changed = True
        while changed:
            changed = False
            for rule in rules:
                if rule.if_concept in known and rule.then_concept not in known:
                    fact = self.kb.get_fact_by_concept(rule.then_concept)
                    if fact is None:
                        continue  # rule points to an undefined concept - skip safely
                    known.add(rule.then_concept)
                    result.chain.append(
                        ReasoningStep(rule.then_concept, fact.statement, rule=rule,
                                      is_initial=False, polarity=fact.polarity)
                    )
                    result.fired_rules.append(rule)
                    result.new_concepts.append(rule.then_concept)
                    changed = True

        result.known_concepts = known
        return result

    def explain(self, result: ReasoningResult):
        """Build a human-readable, arrow-chain explanation string from a
        ReasoningResult, e.g.:

            Strong password
                |
                v  (Rule: Strong Password Rule)
            Difficult to guess
        """
        if not result.chain:
            return "No reasoning steps were recorded."

        lines = []
        for i, step in enumerate(result.chain):
            label = step.concept.replace("_", " ").capitalize()
            lines.append(label)
            if i < len(result.chain) - 1:
                next_step = result.chain[i + 1]
                if next_step.rule is not None:
                    lines.append(f"      |\n      v   (Rule: {next_step.rule.name})")
                else:
                    lines.append("      |\n      v")
        return "\n".join(lines)
