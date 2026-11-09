"""Digital-human-style user simulator built from a MICOL task.json.

The task's `intent` is the persona brief, `traits` are hard facts, and
`scripted_responses` become exact-reply rules — the same fields a Bluejay
digital human runs on, rendered into one system prompt for a text LLM.

The simulator ends the call by including [HANGUP] in a reply.

With a recognizer profile (`asr_profiles/<name>.md`) the caller writes `SAID:` (what it
speaks) and `HEARD:` (what the agent's speech recognizer transcribed); the agent only ever
receives HEARD. ` || ` inside HEARD splits it into separate agent-side turns.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

HANGUP = "[HANGUP]"
SPLIT = "||"
PROFILES = Path(__file__).parent / "asr_profiles"

# Kept byte-identical to the block the profiles were GEPA-tuned under.
CHANNEL = """

## How the agent receives your words
You are on a phone line. The agent never reads your words; it only gets what its speech
recognizer transcribed of your speech. Write every reply as exactly two lines:
SAID: <what you say out loud, following everything above>
HEARD: <the recognizer's transcript of what you said: the only text the agent receives>
Leave HEARD empty when nothing came through. Write " {split} " inside HEARD where the
recognizer cut your speech into two separate turns. Put {hangup} at the end of the SAID line.
How HEARD differs from SAID is described by this recognizer profile:

{profile}
"""

_SYSTEM = """You are role-playing a CUSTOMER on a phone call with a company's voice agent.
This is a text transcript of a spoken call: reply the way a person speaks, in one or two
short sentences, plain text only. Never break character, never mention being an AI or a
simulation, never help the agent beyond what your brief allows.

## Who you are
Name: {name}

## Your brief (follow it exactly)
{intent}

## Hard facts about you (never contradict these; do not volunteer facts you were not asked for)
{traits}

## Scripted replies (highest priority)
When the agent's last message matches a condition below, reply with EXACTLY the scripted
text, nothing more:
{scripted}

## Ending the call
When your brief says the call is over (or the agent has clearly finished), say your final
line and append {hangup} at the very end of the message. Append {hangup} to the same
message as your final words, never alone. If the agent's message is empty or silent twice
in a row, say "Hello?" once; if it stays silent, end the call with {hangup}.
"""


def _system_prompt(task: dict[str, Any]) -> str:
    traits = "\n".join(
        f"- {t['trait_name']}: {t['value']}" for t in task.get("traits") or []
    ) or "- (none)"
    lines = []
    for i, s in enumerate(task.get("scripted_responses") or [], 1):
        lines.append(
            f'{i}. IF: {s.get("match_phrase", "").strip()}\n   REPLY EXACTLY: "{s.get("response_value", "").strip()}"'
        )
    scripted = "\n".join(lines) or "(none)"
    return _SYSTEM.format(
        name=task.get("customer_name", "the caller"),
        intent=(task.get("intent") or "").strip(),
        traits=traits,
        scripted=scripted,
        hangup=HANGUP,
    )


def load_profile(name: str) -> str:
    """Profile name (`asr_profiles/<name>.md`) or a path to a profile file; '' = no channel."""
    if not name:
        return ""
    path = Path(name) if name.endswith(".md") else PROFILES / f"{name}.md"
    return path.read_text()


def system_prompt(task: dict[str, Any], profile: str = "") -> str:
    base = _system_prompt(task)
    if not profile:
        return base
    return base + CHANNEL.format(profile=profile.strip(), split=SPLIT, hangup=HANGUP)


def said_heard(text: str) -> tuple[str, str]:
    """Split a channel reply. A reply without a HEARD line came through verbatim."""
    said, sep, heard = text.partition("HEARD:")
    said = said.replace("SAID:", "", 1).strip()
    return (said, heard.strip()) if sep else (said, said)


# ---------------------------------------------------------------- recognizer draws
# An LLM cannot hit "do X 3.5% of the time" on its own, so the environment draws each
# turn's recognizer result from the profile's measured real rates and hands the caller
# the label. Outcomes the model renders (correct/minor/substantial/clipped) are told;
# mechanical ones (no transcription, streaming split, case, final punctuation) are
# also enforced on HEARD in code.

OUTCOMES = (("none", "rate_dropped"), ("clipped", "rate_truncated"),
            ("substantial", "rate_major"), ("minor", "rate_minor"))  # remainder: correct

DRAWS = """

## Recognizer draws
Each message you receive ends with a line like
[recognizer draw: outcome=minor; split=no; final_punctuation=yes; lowercase=no]
It is the recognizer's result for your next reply, already decided. Never mention it and never
let it change what you SAY. Render HEARD to match it exactly:
- outcome=correct: every word recognized; only the recognizer's own formatting differs.
- outcome=minor: one or two local word errors. If the line has a name or a long number, put the error there.
- outcome=substantial: one badly damaged region (several digits wrong or missing, a name decoded as other words, a short phrase misrecognized); the rest stays accurate.
- outcome=clipped: a real span at the start or end of what you said is lost; the rest stays as recognized.
- outcome=none: nothing came through; leave HEARD empty.
- split=yes: cut HEARD into two segments with " {split} " at a natural boundary. split=no: one segment.
- final_punctuation=no: HEARD ends without a period, question mark or exclamation mark.
- lowercase=yes: all of HEARD is lowercase.
The draw overrides any rate, share or probability in the profile above.
"""

_CLAUSE_END = re.compile(r"(?<=[.?!,])\s+")
_FINAL_PUNCT = re.compile(r"[.?!…]+$")


def load_rates(profile: str) -> dict[str, float]:
    """Measured real rates next to a profile: `asr_profiles/<name>.stats.json`."""
    path = Path(profile).with_suffix(".stats.json") if profile.endswith(".md") else PROFILES / f"{profile}.stats.json"
    return {k: v for k, v in json.loads(path.read_text()).items() if isinstance(v, (int, float))}


def draw(rates: dict[str, float], key: str) -> dict[str, Any]:
    """One turn's recognizer result; the same key always gives the same draw."""
    rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))
    u, outcome, edge = rng.random(), "correct", 0.0
    for name, rate_key in OUTCOMES:
        edge += rates.get(rate_key, 0.0)
        if u < edge:
            outcome = name
            break
    return {"outcome": outcome,
            "split": rng.random() < rates.get("rate_split", 0.0),
            "final_punctuation": rng.random() >= rates.get("fmt_no_terminal", 0.0),
            "lowercase": rng.random() < rates.get("fmt_lower_only", 0.0)}


def draw_line(d: dict[str, Any]) -> str:
    yn = lambda b: "yes" if b else "no"  # noqa: E731
    return (f"[recognizer draw: outcome={d['outcome']}; split={yn(d['split'])}; "
            f"final_punctuation={yn(d['final_punctuation'])}; lowercase={yn(d['lowercase'])}]")


def enforce(heard: str, d: dict[str, Any]) -> str:
    """Apply the mechanical parts of a draw to HEARD whatever the model wrote."""
    if d["outcome"] == "none":
        return ""
    segs = [s.strip() for s in heard.split(SPLIT) if s.strip()]
    if not segs:
        return ""
    if not d["split"]:
        segs = [" ".join(segs)]
    elif len(segs) == 1:
        parts = _CLAUSE_END.split(segs[0], maxsplit=1)
        segs = parts if len(parts) == 2 and all(p.strip() for p in parts) else segs
    if d["lowercase"]:
        segs = [s.lower() for s in segs]
    if not d["final_punctuation"]:
        segs[-1] = _FINAL_PUNCT.sub("", segs[-1]).rstrip()
    return f" {SPLIT} ".join(segs)


class UserSim:
    def __init__(self, llm, task: dict[str, Any], profile: str = "", *,
                 rates: dict[str, float] | None = None, draw_key: str = ""):
        self.llm = llm
        self.channel = bool(profile)
        self.rates = rates if self.channel else None
        self.draw_key = draw_key
        self.turn = 0
        self.last_said = ""
        self.last_draw: dict[str, Any] | None = None
        prompt = system_prompt(task, profile)
        if self.rates is not None:
            prompt += DRAWS.format(split=SPLIT)
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": prompt}]

    def reply(self, agent_text: str) -> tuple[str, bool]:
        """Feed the agent's spoken text; return (text the agent receives, hangup)."""
        content = agent_text or "(silence)"
        self.last_draw = None
        if self.rates is not None:
            self.last_draw = draw(self.rates, f"{self.draw_key}|{self.turn}")
            content = f"{content}\n\n{draw_line(self.last_draw)}"
        self.turn += 1
        self.messages.append({"role": "user", "content": content})
        out = self.llm.chat(self.messages)
        text = (out.get("content") or "").strip()
        self.messages.append({"role": "assistant", "content": text})
        hangup = HANGUP in text
        text = text.replace(HANGUP, "")
        if not self.channel:
            self.last_said = text.strip()
            return self.last_said, hangup
        self.last_said, heard = said_heard(text)
        if self.last_draw is not None:
            heard = enforce(heard, self.last_draw)
        return heard, hangup


def temperature(task: dict[str, Any]) -> float:
    creativity = ((task.get("behaviors") or {}).get("creativity")) or 0
    return float(creativity)
