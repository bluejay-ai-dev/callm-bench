"""Said -> heard channel measurement shared by corpus analysis and GEPA scoring.

`said` is what the caller spoke (SAID, or the digital human in voice MICOL), `heard` is what the
agent's speech recognizer produced for it. Everything here is pure text; no network.
"""

from __future__ import annotations

import difflib
import re

UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine".split())}
TEENS = {w: 10 + i for i, w in enumerate(
    "ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate(
    "twenty thirty forty fifty sixty seventy eighty ninety".split())}
ORDINALS = {w: i + 1 for i, w in enumerate((
    "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth "
    "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth").split())}
ORDINALS.update({"twentieth": 20, "thirtieth": 30})
CANON = {"ok": "okay", "mm": "mhm", "hmm": "mhm", "mmhmm": "mhm", "mmhm": "mhm", "mhmm": "mhm"}
DROP = {"dollars", "dollar", "cents", "th", "st", "nd", "rd", "um", "uh"}
TERMINAL = re.compile(r"[.?!…\"”')]\s*$")
DIGIT_WORD_RUN = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|oh)\b[, ]+(zero|one|two|three|four|five|six|seven|eight|nine|oh)\b")
SPELLED = re.compile(r"\b[A-Za-z]\b[,\- ]+\b[A-Za-z]\b[,\- ]+\b[A-Za-z]\b")
CLASSES = ("exact", "minor", "major", "truncated", "dropped")


def _num(t: str) -> int | None:
    for table in (UNITS, TEENS, TENS, ORDINALS):
        if t in table:
            return table[t]
    return None


def _words_to_digits(tokens: list[str]) -> list[str]:
    out, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if t in TENS and nxt != "zero" and (_num(nxt) or 10) < 10:
            out.append(str(TENS[t] + _num(nxt))); i += 2; continue
        if nxt == "hundred" and (_num(t) or 10) < 10 and t not in ORDINALS:
            base, j = _num(t) * 100, i + 2
            if j < len(tokens) and tokens[j] == "and":
                j += 1
            a = tokens[j] if j < len(tokens) else ""
            b = tokens[j + 1] if j + 1 < len(tokens) else ""
            if a in TENS and b in UNITS and b != "zero":
                base += TENS[a] + UNITS[b]; j += 2
            elif _num(a) is not None and a not in ORDINALS:
                base += _num(a); j += 1
            out.append(str(base)); i = j; continue
        n = _num(t)
        if n is not None:
            out.append(str(n))
        elif t == "oh" and ((out and out[-1].isdigit()) or nxt in UNITS):
            out.append("0")
        elif t == "double" and nxt in UNITS:
            out += [str(UNITS[nxt])] * 2; i += 2; continue
        else:
            out.append(t)
        i += 1
    return out


def norm(text: str) -> list[str]:
    """Content tokens: case, punctuation and number formatting removed; digits exploded."""
    t = text.lower().replace("’", "'").replace("‘", "'")
    t = re.sub(r"\b(mm-hmm|mm-hm|uh-huh|mm hmm)\b", "mhm", t)
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    t = re.sub(r"(\d)", r" \1 ", t)
    toks = [CANON.get(w.strip("'"), w.strip("'")) for w in t.split()]
    toks = [c for w in _words_to_digits([w for w in toks if w])
            for c in ([w] if not w.isdigit() else list(w)) if c not in DROP]
    return [w for k, w in enumerate(toks) if not (
        w == "and" and 0 < k < len(toks) - 1 and toks[k - 1].isdigit() and toks[k + 1].isdigit())]


def _flat(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def collapse_partials(heard: list[str]) -> list[str]:
    """grok/nova log cumulative streaming partials; keep only the last segment of each prefix chain."""
    out: list[str] = []
    for h in (h for h in heard if h.strip()):
        if out:
            cur, nxt = _flat(out[-1]), _flat(h)
            if cur and len(nxt) >= len(cur) and difflib.SequenceMatcher(
                    None, cur, nxt[: len(cur)], autojunk=False).ratio() >= 0.8:
                out[-1] = h
                continue
        out.append(h)
    return out


def align(said: list[str], heard: list[str]) -> list[dict]:
    """Token-align a call's said utterances against its heard segments (monotonic)."""
    S, So, H, Ho = [], [], [], []
    for k, u in enumerate(said):
        for w in norm(u):
            S.append(w); So.append(k)
    for k, h in enumerate(heard):
        for w in norm(h):
            H.append(w); Ho.append(k)
    per = [{"sub": 0, "del": 0, "ins": 0, "hit": 0, "segs": set(), "status": [], "heard_toks": []} for _ in said]
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, S, H, autojunk=False).get_opcodes():
        if tag in ("equal", "replace"):
            for k in range(i2 - i1):
                u = per[So[i1 + k]]
                if k < j2 - j1:
                    key = "hit" if tag == "equal" else "sub"
                    u[key] += 1; u["status"].append("=" if key == "hit" else "s")
                    u["segs"].add(Ho[j1 + k]); u["heard_toks"].append(H[j1 + k])
                else:
                    u["del"] += 1; u["status"].append("d")
            for k in range(i2 - i1, j2 - j1):
                u = per[So[i2 - 1]]; u["ins"] += 1; u["heard_toks"].append(H[j1 + k])
        elif tag == "delete":
            for k in range(i1, i2):
                per[So[k]]["del"] += 1; per[So[k]]["status"].append("d")
        else:  # insert: count only when it sits inside a segment the utterance already owns
            owner = So[i1 - 1] if i1 > 0 else (So[0] if So else None)
            for k in range(j1, j2):
                if owner is not None and (Ho[k] in per[owner]["segs"] or (j1 > 0 and Ho[k] == Ho[j1 - 1])):
                    per[owner]["ins"] += 1; per[owner]["heard_toks"].append(H[k])
    return per


def classify(u: dict, n: int) -> str:
    if n == 0 or u["hit"] + u["sub"] == 0:
        return "dropped"
    st = "".join(u["status"])
    tail, head = len(st) - len(st.rstrip("d")), len(st) - len(st.lstrip("d"))
    if (tail >= 2 and tail / n >= 0.2) or (head >= 2 and head / n >= 0.2):
        return "truncated"
    wer = (u["sub"] + u["del"] + u["ins"]) / n
    return "exact" if wer == 0 else "minor" if wer <= 0.15 else "major"


def call_records(said: list[str], heard: list[str], name: str = "", skip_last: bool = True) -> list[dict]:
    """One record per said utterance. The final utterance is skipped when it was dropped:
    the goodbye before hangup is usually never logged, which is not a channel event."""
    per = align(said, heard)
    name_toks = [w for w in norm(name) if len(w) > 1]
    recs = []
    for k, (u, raw) in enumerate(zip(per, said)):
        toks = norm(raw)
        cls = classify(u, len(toks))
        if cls == "dropped" and k == len(said) - 1 and skip_last:
            continue
        sd = [w for w in toks if w.isdigit()]
        hd = [w for w in u["heard_toks"] if w.isdigit()]
        names = [w for w in name_toks if w in toks]
        recs.append({
            "idx": k, "said": raw, "heard": " || ".join(heard[j] for j in sorted(u["segs"])),
            "cls": cls, "n": len(toks), "err": u["sub"] + u["del"] + u["ins"],
            "split": len(u["segs"]) > 1,
            "digits": (sd == hd) if len(sd) >= 3 else None, "n_digits": len(sd),
            "names": all(w in u["heard_toks"] for w in names) if names else None,
            "spelled": bool(SPELLED.search(raw)),
        })
    return recs


def surface(heard: list[str]) -> dict[str, int]:
    """Formatting fingerprint of a recognizer: casing, numerals, punctuation."""
    segs = [h for h in heard if h.strip()]
    return {
        "segs": len(segs),
        "lower_only": sum(1 for h in segs if h == h.lower() and re.search("[a-z]", h)),
        "numerals": sum(1 for h in segs if re.search(r"\d", h)),
        "digit_words": sum(1 for h in segs if DIGIT_WORD_RUN.search(h.lower())),
        "no_terminal": sum(1 for h in segs if not TERMINAL.search(h.strip())),
        "words": sum(len(h.split()) for h in segs),
    }


def pool(records: list[dict], surf: list[dict]) -> dict[str, float]:
    """Channel rates over a set of calls; the comparison unit for GEPA and reports."""
    n = max(1, len(records))
    out = {f"rate_{c}": sum(r["cls"] == c for r in records) / n for c in CLASSES}
    out["rate_split"] = sum(r["split"] for r in records) / n
    tok = sum(r["n"] for r in records)
    out["wer"] = sum(r["err"] for r in records if r["cls"] != "dropped") / max(1, tok)
    for key in ("digits", "names"):
        vals = [r[key] for r in records if r[key] is not None and r["cls"] != "dropped"]
        out[f"{key}_ok"] = sum(vals) / len(vals) if vals else float("nan")
    segs = max(1, sum(s["segs"] for s in surf))
    for key in ("lower_only", "numerals", "digit_words", "no_terminal"):
        out[f"fmt_{key}"] = sum(s[key] for s in surf) / segs
    out["words_per_seg"] = sum(s["words"] for s in surf) / segs
    out["n_utts"] = len(records)
    return out


if __name__ == "__main__":
    same = lambda a, b: norm(a) == norm(b)  # noqa: E731
    assert same("Rivertide at five hundred forty-nine ninety-nine", "Rivertide at $549.99")
    assert same("three hundred ninety-nine dollars and ninety-nine cents", "$399.99")
    assert same("January fifth, twenty twenty six", "January 5th, 2026")
    assert same("two, one, two, five, five, five, zero, one, nine, four", "212-555-0194")
    assert same("Okay. Mm-hmm.", "OK, mhm")
    assert collapse_partials(["I said put me", "I said put me through.", "Bye."]) == ["I said put me through.", "Bye."]
    r = call_records(["My name is Hal Brenner, two one two five five five zero one nine four.", "Yes."],
                     ["My name is Hal Brunner, 212-555-0194.", "Yes."], name="HAL BRENNER")
    assert [x["cls"] for x in r] == ["minor", "exact"] and r[0]["digits"] and r[0]["names"] is False, r
    print("channel self-check ok")
