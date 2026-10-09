"""
AURIX Learning Resonance Engine
===============================

AURIX does not classify the user's emotional state.

Instead, it learns which interaction behavior works best in context.

Learning method:
    LinUCB contextual bandit

Possible interaction actions:
    brief_direct
    normal
    detailed
    clarify
    silence

Only explicit feedback updates the learning policy in this version.
This prevents AURIX from pretending that it knows whether the user
liked a response.
"""

import json
import os
import re

import numpy as np


# ===============================================================
# ACTION SPACE
# ===============================================================

ACTIONS = (
    "brief_direct",
    "normal",
    "detailed",
    "clarify",
    "silence",
)

FEATURE_COUNT = 11


# ===============================================================
# SIGNAL EXTRACTION
# ===============================================================

def extract_signals(user_input):
    """
    Extract observable conversational signals.

    These are interaction features, NOT emotion labels.
    """

    text = (
        user_input
        if isinstance(user_input, str)
        else ""
    ).strip()

    lower = text.lower()

    words = re.findall(
        r"\b[\w'-]+\b",
        lower,
    )

    word_count = len(words)

    question = (
        "?" in text
        or lower.startswith(
            (
                "what ",
                "why ",
                "how ",
                "when ",
                "where ",
                "who ",
                "can ",
                "could ",
                "would ",
                "should ",
                "is ",
                "are ",
            )
        )
    )

    command = lower.startswith(
        (
            "open ",
            "show ",
            "tell ",
            "explain ",
            "read ",
            "summarize ",
            "create ",
            "make ",
            "look ",
            "find ",
            "give ",
        )
    )

    direct_request = (
        question
        or command
    )

    low_information = (
        word_count <= 2
        or lower in {
            "hmm",
            "hm",
            "mmm",
            "okay",
            "ok",
            "ugh",
            "...",
            "whatever",
        }
    )

    problem_language = any(
        phrase in lower
        for phrase in (
            "not working",
            "doesn't work",
            "doesnt work",
            "error",
            "failed",
            "stuck",
            "bug",
            "wrong",
            "again",
            "issue",
        )
    )

    detail_request = any(
        phrase in lower
        for phrase in (
            "explain",
            "step by step",
            "in detail",
            "detailed",
            "full code",
            "everything",
            "complete code",
        )
    )

    repeated_punctuation = bool(
        re.search(
            r"[!?]{2,}|\.{3,}",
            text,
        )
    )

    gratitude = any(
        phrase in lower
        for phrase in (
            "thank you",
            "thanks",
            "perfect",
            "great",
        )
    )

    correction_language = any(
        phrase in lower
        for phrase in (
            "wrong",
            "not that",
            "i said",
            "i meant",
            "that's not",
            "thats not",
        )
    )

    return {
        "word_count": word_count,
        "direct_request": direct_request,
        "low_information": low_information,
        "problem_language": problem_language,
        "detail_request": detail_request,
        "repeated_punctuation": repeated_punctuation,
        "gratitude": gratitude,
        "correction_language": correction_language,
    }


# ===============================================================
# CONTEXT VECTOR
# ===============================================================

def context_vector(
    user_input,
    state=None,
):
    """
    Convert the current interaction into a numeric context vector
    used by the contextual-bandit learner.
    """

    signals = extract_signals(
        user_input
    )

    state = state or {}

    brevity = float(
        state.get(
            "response_brevity",
            0.50,
        )
    )

    initiative = float(
        state.get(
            "desired_initiative",
            0.35,
        )
    )

    certainty = float(
        state.get(
            "certainty",
            0.30,
        )
    )

    word_scale = min(
        signals["word_count"] / 40.0,
        1.0,
    )

    vector = np.array(
        [
            1.0,  # bias
            word_scale,
            float(signals["direct_request"]),
            float(signals["low_information"]),
            float(signals["problem_language"]),
            float(signals["detail_request"]),
            float(signals["repeated_punctuation"]),
            float(signals["gratitude"]),
            brevity,
            initiative,
            certainty,
        ],
        dtype=float,
    )

    return vector, signals


# ===============================================================
# ACTION ELIGIBILITY
# ===============================================================

def eligible_actions(signals):
    """
    Apply safety/appropriateness rules before learning chooses an action.

    Important:
    Silence must never ignore a clear user request.
    """

    allowed = set(ACTIONS)

    if signals["direct_request"]:
        allowed.discard(
            "silence"
        )

    if signals["detail_request"]:
        allowed.discard(
            "silence"
        )

        allowed.discard(
            "brief_direct"
        )

    if signals["problem_language"]:
        allowed.discard(
            "silence"
        )

    # Silence is only available for low-information,
    # non-direct conversational input.
    if not signals["low_information"]:
        allowed.discard(
            "silence"
        )

    if not allowed:
        allowed = {
            "normal"
        }

    return sorted(
        allowed
    )


# ===============================================================
# LINUCB CONTEXTUAL BANDIT
# ===============================================================

class LinUCBBandit:
    """
    Simple contextual-bandit learner.

    For every possible action we maintain:

        A = feature covariance matrix
        b = reward-weighted feature vector

    LinUCB estimates:

        expected reward
        +
        uncertainty bonus

    This lets AURIX balance:

        exploitation
        using behaviors that have worked before

    with:

        exploration
        trying less-tested behaviors when appropriate
    """

    def __init__(
        self,
        path="aurix_bandit.json",
        alpha=0.65,
    ):

        self.path = path
        self.alpha = float(alpha)
        self.dimension = FEATURE_COUNT

        self.A = {}
        self.b = {}

        self._initialize()

        if os.path.exists(
            self.path
        ):
            self.load()

    # -----------------------------------------------------------
    # INITIALIZE
    # -----------------------------------------------------------

    def _initialize(self):

        for action in ACTIONS:

            self.A[action] = np.eye(
                self.dimension,
                dtype=float,
            )

            self.b[action] = np.zeros(
                self.dimension,
                dtype=float,
            )

    # -----------------------------------------------------------
    # SCORE ONE ACTION
    # -----------------------------------------------------------

    def score(
        self,
        action,
        x,
    ):

        if action not in ACTIONS:

            raise ValueError(
                f"Unknown action: {action}"
            )

        x = np.asarray(
            x,
            dtype=float,
        )

        if x.shape != (
            self.dimension,
        ):

            raise ValueError(
                "Context vector has wrong dimension."
            )

        A_inv = np.linalg.inv(
            self.A[action]
        )

        theta = (
            A_inv
            @ self.b[action]
        )

        expected_reward = float(
            theta
            @ x
        )

        uncertainty = float(
            np.sqrt(
                x
                @ A_inv
                @ x
            )
        )

        return (
            expected_reward
            +
            self.alpha
            * uncertainty
        )

    # -----------------------------------------------------------
    # CHOOSE ACTION
    # -----------------------------------------------------------

    def choose(
        self,
        x,
        allowed_actions=None,
    ):

        allowed = (
            list(allowed_actions)
            if allowed_actions
            else list(ACTIONS)
        )

        if not allowed:

            allowed = [
                "normal"
            ]

        scores = {
            action: self.score(
                action,
                x,
            )
            for action in allowed
        }

        chosen = max(
            scores,
            key=scores.get,
        )

        return chosen, scores

    # -----------------------------------------------------------
    # LEARN FROM FEEDBACK
    # -----------------------------------------------------------

    def update(
        self,
        action,
        x,
        reward,
    ):

        if action not in ACTIONS:
            return

        x = np.asarray(
            x,
            dtype=float,
        )

        if x.shape != (
            self.dimension,
        ):
            return

        reward = float(
            max(
                -1.0,
                min(
                    1.0,
                    reward,
                ),
            )
        )

        self.A[action] += np.outer(
            x,
            x,
        )

        self.b[action] += (
            reward
            * x
        )

        self.save()

    # -----------------------------------------------------------
    # SAVE LEARNING
    # -----------------------------------------------------------

    def save(self):

        data = {
            "version": 1,
            "alpha": self.alpha,
            "dimension": self.dimension,
            "actions": {},
        }

        for action in ACTIONS:

            data["actions"][action] = {
                "A": (
                    self.A[action]
                    .tolist()
                ),

                "b": (
                    self.b[action]
                    .tolist()
                ),
            }

        with open(
            self.path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
            )

    # -----------------------------------------------------------
    # LOAD LEARNING
    # -----------------------------------------------------------

    def load(self):

        try:

            with open(
                self.path,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(
                    file
                )

            if (
                data.get(
                    "dimension"
                )
                != self.dimension
            ):

                return

            action_data = data.get(
                "actions",
                {}
            )

            for action in ACTIONS:

                item = action_data.get(
                    action
                )

                if not item:
                    continue

                A = np.asarray(
                    item.get(
                        "A"
                    ),
                    dtype=float,
                )

                b = np.asarray(
                    item.get(
                        "b"
                    ),
                    dtype=float,
                )

                if A.shape == (
                    self.dimension,
                    self.dimension,
                ):

                    self.A[action] = A

                if b.shape == (
                    self.dimension,
                ):

                    self.b[action] = b

        except Exception:

            # A corrupt learning file must not prevent AURIX
            # from starting.
            self._initialize()


# ===============================================================
# RESPONSE POLICY DIRECTIVES
# ===============================================================

def policy_directive(action):
    """
    Convert a learned action into a response-style instruction
    for the reasoning model.
    """

    directives = {

        "brief_direct": """
Give the useful answer or next action immediately.
Keep the response short.
Avoid unnecessary reassurance or conversational padding.
Do not ask a follow-up unless it is required.
""",

        "normal": """
Give a clear and natural AURIX response.
Match the amount of detail to the user's request.
Avoid unnecessary padding.
""",

        "detailed": """
Give a detailed response.
Explain systematically.
Include technical detail when it materially improves understanding.
""",

        "clarify": """
If the user asked a question you can answer, answer it first - even if the
honest answer is that you lack the evidence, and why.
Only then, if something is genuinely unclear, ask exactly one concise
clarifying question. Never reply to a question with only a question.
""",

        "silence": """
Do not produce a spoken response.
Intentional silence is the selected interaction behavior.
""",
    }

    return directives.get(
        action,
        directives["normal"],
    )


# ===============================================================
# EXPLICIT FEEDBACK
# ===============================================================

FEEDBACK_REWARDS = {

    "feedback good": 1.0,

    "feedback perfect": 1.0,

    "feedback bad": -1.0,

    "feedback wrong": -1.0,

    "feedback too long": -0.75,

    "feedback more detail": -0.60,

    "feedback unnecessary": -1.0,

    "feedback should have replied": -1.0,
}


def feedback_reward(
    normalized_command
):
    """
    Translate explicit user feedback into a bounded learning reward.

    No feedback is inferred from facial expressions, tone, or silence.
    """

    return FEEDBACK_REWARDS.get(
        normalized_command
    )