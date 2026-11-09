"""MICOL scoring: tool-call, handoff-path and final-database adherence.

Pure functions over a call's tool trace and final database; no model calls.
Combined pass is AND of the three checks.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from micol.bench import INDUSTRIES as INDUSTRY_ROOT


HANDOFF_TOOLS = frozenset({
    "transfer_to_identity", "transfer_to_scheduling", "transfer_to_coverage",
    "transfer_to_cosmetic", "transfer_to_billing", "transfer_to_clinical",
    "transfer_to_human",
})


INDUSTRY_HANDOFF_TOOLS: dict[str, frozenset[str]] = {
    "healthcare": HANDOFF_TOOLS,
    "legal": frozenset({
        "transfer_to_screening", "transfer_to_intake",
        "transfer_to_scheduling", "transfer_to_client_services",
    }),
    "customer-support": frozenset({
        "transfer_to_verification", "transfer_to_orders",
        "transfer_to_returns", "transfer_to_service",
        "transfer_to_membership", "transfer_to_fraud",
    }),
}


OFFICE_TABLES = ("patients", "appointments", "waitlist")


INDUSTRY_OFFICE_TABLES: dict[str, tuple[str, ...]] = {
    "healthcare": OFFICE_TABLES,
    "legal": (
        "intakes", "intake_notes", "documents", "holds",
        "evaluations", "messages", "escalations",
    ),
    "customer-support": (
        "customers", "orders", "order_items", "order_cancellations",
        "delivery_changes", "membership_changes", "holds",
        "refunds", "rmas", "return_labels", "price_matches",
        "protection_plans", "service_appointments", "escalations",
        "scam_reports",
    ),
}


PROSE_ARG_KEYS = frozenset({
    "notes", "patient_safe_message",
})


FACT_ARG_KEYS = frozenset({
    "full_name", "first_name", "last_name", "dob", "zip", "carrier",
    "member_id", "destination", "queue", "location_id", "provider_id",
    "slot_id", "appointment_id", "start", "end", "new_start", "new_end",
    "service_date", "group_number", "channel", "template_id",
    "medication_name", "visit_class", "topic", "service", "order_type",
    "appointment_type_code", "cancellation_reason_code", "fee_line_item_id",
    "line_item_id", "next_intent", "subscriber_relationship",
})


INDUSTRY_PROSE_ARG_KEYS: dict[str, frozenset[str]] = {
    "healthcare": PROSE_ARG_KEYS,
    "legal": frozenset({"summary", "note", "message", "handoff_summary", "full_name"}),
    "customer-support": frozenset({
        "topic", "fee", "query", "issue", "full_name", "phone",
        "reason",
    }),
}


INDUSTRY_FACT_ARG_KEYS: dict[str, frozenset[str]] = {
    "healthcare": FACT_ARG_KEYS,
    "legal": frozenset({
        "opposing_party", "practice_area", "state", "incident_date",
        "reason_code", "slot_id", "confirmation_token", "matter_id",
        "channel", "for_whom", "provider", "evaluation_id", "attorney_id",
        "phone", "earliest_date", "reason",
    }),
    "customer-support": frozenset({
        "order_number", "postal_code", "card_last4", "reason_code",
        "rma_number", "sku", "competitor", "competitor_price",
        "in_stock", "opened", "service_type",
        "fee_disclosed_acknowledged", "proration_acknowledged",
        "confirmation_token",
    }),
}


def handoff_tools_for(industry: str | None) -> frozenset[str]:
    if industry and industry in INDUSTRY_HANDOFF_TOOLS:
        return INDUSTRY_HANDOFF_TOOLS[industry]
    return HANDOFF_TOOLS


def office_tables_for(industry: str | None) -> tuple[str, ...]:
    if industry and industry in INDUSTRY_OFFICE_TABLES:
        return INDUSTRY_OFFICE_TABLES[industry]
    return OFFICE_TABLES


def fact_arg_keys_for(industry: str | None) -> frozenset[str]:
    if industry and industry in INDUSTRY_FACT_ARG_KEYS:
        return INDUSTRY_FACT_ARG_KEYS[industry]
    return FACT_ARG_KEYS


def prose_arg_keys_for(industry: str | None) -> frozenset[str]:
    if industry and industry in INDUSTRY_PROSE_ARG_KEYS:
        return INDUSTRY_PROSE_ARG_KEYS[industry]
    return PROSE_ARG_KEYS


KEEP_ARG_TYPES = frozenset({"number", "integer", "boolean"})


KEEP_ARG_FORMATS = frozenset({"date", "date-time"})


IGNORE_ROW_KEYS = frozenset({"created_at", "description"})


LEGAL_IGNORE_ROW_KEYS = frozenset({
    "message", "summary", "note",
    "slot_id", "starts_at", "attorney_id", "datetime",
    "caller_id", "reason",
})


LEGAL_EXTRA_OK_TABLES = frozenset({
    "messages", "intake_notes", "documents", "holds", "evaluations",
    # reception.md says both "look them up" first and "take nothing" for adjusters and
    # represented callers; an agent that looks the caller up before escalating creates a
    # caller row the take-nothing reading does not. Expected rows stay required.
    "callers",
})


# free-text the agent writes in its own words: a return reason the caller never
# states (rmas/holds column, nested in holds.payload JSON) and the service
# appointment's issue text ("will not charge" vs "Aurora Pro will not charge").
# Both are already prose args in INDUSTRY_PROSE_ARG_KEYS for the tool-call check.
CS_IGNORE_ROW_KEYS = frozenset({"reason", "issue"})


PHONE_KEY_RE = re.compile(r"phone|_e164$", re.I)


# ISO date + hour + minute; seconds, micros, and timezone are optional.
_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"
    r"(?::\d{2}(?:\.\d+)?)?"
    r"(?:Z|[+-]\d{2}:?\d{2})?$"
)


_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {}


def expected_state(task: dict[str, Any]) -> Any:
    return task.get("exp_db_state")


def _digits_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def _is_phone_key(key: str) -> bool:
    return bool(PHONE_KEY_RE.search(key))


def _ignore_row_keys(industry: str | None) -> frozenset[str]:
    if industry == "legal":
        return IGNORE_ROW_KEYS | LEGAL_IGNORE_ROW_KEYS
    if industry == "customer-support":
        return IGNORE_ROW_KEYS | CS_IGNORE_ROW_KEYS
    return IGNORE_ROW_KEYS


def _minute_datetime(value: Any) -> Any:
    """Collapse datetime-like strings to date+hour+minute (drop seconds/micros)."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not _DATETIME_RE.match(text):
        return value
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%Y-%m-%dT%H:%M")


def _canon_amount(value: str) -> str:
    """'$399.99' / '399.99 dollars' / '399.99' are one amount the caller stated."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", value)
    if not m:
        return value.strip().casefold()
    return f"{float(m.group(0).replace(',', '')):.2f}"


_NO_PAYMENT = frozenset({"", "none", "not stated", "not requested", "no", "n/a", "na", "nothing"})


def _canon_payment(value: str) -> str:
    """Payment method the scammer asked for: 'none' / 'not stated' / '' mean none;
    'gift card' and 'gift cards' are the same method."""
    text = value.strip().casefold()
    if text in _NO_PAYMENT:
        return "none"
    return re.sub(r"s\b", "", text)


def _canon_row(row: Any, industry: str | None = None) -> Any:
    if not isinstance(row, dict):
        return row
    ignore = _ignore_row_keys(industry)
    out: dict[str, Any] = {}
    for key, value in row.items():
        if key in ignore:
            continue
        if key == "payload" and isinstance(value, str):
            # holds.payload is a JSON blob; ignored free-text keys hide inside it.
            try:
                parsed = json.loads(value)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                out[key] = json.dumps(
                    {k: v for k, v in parsed.items() if k not in ignore},
                    sort_keys=True,
                )
                continue
        if isinstance(value, str) and _is_phone_key(key):
            out[key] = _digits_phone(value)
        elif isinstance(value, str) and key == "amount_text":
            out[key] = _canon_amount(value)
        elif isinstance(value, str) and key == "payment_requested":
            out[key] = _canon_payment(value)
        elif isinstance(value, str):
            # collapse T15:30 vs T15:30:00 first; casefold after so dump seconds
            # cannot disagree with a minute-precision seed.
            collapsed = _minute_datetime(value)
            out[key] = collapsed.strip().casefold() if isinstance(collapsed, str) else collapsed
        else:
            out[key] = _minute_datetime(value)
    return out


def office_canonical(state: Any, industry: str | None = None) -> dict[str, Any]:
    """Industry write tables from GET /state."""
    src = state if isinstance(state, dict) else {}
    out: dict[str, Any] = {}
    for table in office_tables_for(industry):
        rows = src.get(table) or []
        if not isinstance(rows, list):
            rows = []
        canon = [_canon_row(row, industry) for row in rows]
        if table == "waitlist":
            # autogenerated waitlist ids are not part of the agent contract;
            # extra listings would otherwise steal id=1 and fail subset match.
            canon = [
                {k: v for k, v in row.items() if k != "id"} if isinstance(row, dict) else row
                for row in canon
            ]
        out[table] = sorted(
            canon,
            key=lambda row: json.dumps(row, sort_keys=True, default=str),
        )
    return out


def _row_fingerprint(row: Any) -> str:
    return json.dumps(row, sort_keys=True, default=str)


def _constrained_fields(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"_value": row}
    return {key: value for key, value in row.items() if value not in ("", None)}


def _legal_row_covered(expected: Any, actual_rows: list[Any]) -> bool:
    want = _constrained_fields(expected)
    for actual in actual_rows:
        got = actual if isinstance(actual, dict) else {}
        if all(_values_equal(key, value, got.get(key)) for key, value in want.items()):
            return True
    return False


def _legal_table_match(expected_rows: list[Any], actual_rows: list[Any], *, extras_ok: bool) -> bool:
    if extras_ok:
        if not expected_rows:
            return True
        return all(_legal_row_covered(row, actual_rows) for row in expected_rows)
    if len(expected_rows) != len(actual_rows):
        return False
    remaining = list(actual_rows)
    for expected in expected_rows:
        match_at = next(
            (i for i, actual in enumerate(remaining) if _legal_row_covered(expected, [actual])),
            None,
        )
        if match_at is None:
            return False
        remaining.pop(match_at)
    return True


def _scam_report_row_matches(expected: Any, actual: Any) -> bool:
    """Match a report by its facts and either supplied contact channel."""
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return expected == actual
    contact_keys = ("phone", "email")
    expected_facts = {key: value for key, value in expected.items() if key not in contact_keys}
    actual_facts = {key: value for key, value in actual.items() if key not in contact_keys}
    if expected_facts != actual_facts:
        return False
    supplied = [key for key in contact_keys if _present_nonempty(actual.get(key))]
    if not supplied:
        return False
    return all(
        _present_nonempty(expected.get(key))
        and _values_equal(key, expected.get(key), actual.get(key))
        for key in supplied
    )


def _scam_reports_match(expected_rows: list[Any], actual_rows: list[Any]) -> bool:
    """Require the same reports while allowing the prompt's phone-or-email route."""
    if len(expected_rows) != len(actual_rows):
        return False
    remaining = list(actual_rows)
    for expected in expected_rows:
        match_at = next(
            (i for i, actual in enumerate(remaining) if _scam_report_row_matches(expected, actual)),
            None,
        )
        if match_at is None:
            return False
        remaining.pop(match_at)
    return True


def office_states_match(expected: Any, actual: Any, industry: str | None = None) -> bool:
    """Healthcare: patients/appointments exact; waitlist subset when expected non-empty.
    Legal: mutation tables match on constrained fields. Empty expected intakes /
    escalations still require empty actual. Empty expected messages, intake_notes,
    documents, holds, and evaluations allow extra live rows (packets, optional notes,
    and a booking after intake is already complete)."""
    exp = office_canonical(expected, industry)
    act = office_canonical(actual, industry)
    if industry == "healthcare":
        if exp["patients"] != act["patients"]:
            return False
        if exp["appointments"] != act["appointments"]:
            return False
        if not exp["waitlist"]:
            return act["waitlist"] == []
        actual_keys = {_row_fingerprint(row) for row in act["waitlist"]}
        return all(_row_fingerprint(row) in actual_keys for row in exp["waitlist"])
    for table in office_tables_for(industry):
        if industry == "legal":
            extras_ok = table in LEGAL_EXTRA_OK_TABLES
            if not _legal_table_match(exp[table], act[table], extras_ok=extras_ok):
                return False
            continue
        if industry == "customer-support" and table == "scam_reports":
            if not _scam_reports_match(exp[table], act[table]):
                return False
            continue
        if not exp[table]:
            live = act[table]
            if industry == "customer-support" and table == "holds":
                # quote_* tools always write an unconsumed hold; a quote the caller never
                # confirmed changes nothing. Expected-empty still fails on a consumed hold.
                live = [row for row in live if isinstance(row, dict) and row.get("consumed") not in (0, "0", False)]
            if live:
                return False
        elif exp[table] != act[table]:
            return False
    return True


def load_tool_schemas(industry: str) -> dict[str, Any]:
    if industry in _TOOL_SCHEMAS:
        return _TOOL_SCHEMAS[industry]
    path = INDUSTRY_ROOT / industry / "tools.json"
    schemas: dict[str, Any] = {}
    if path.is_file():
        data = json.loads(path.read_text())
        for tool in data.get("tools") or []:
            name = tool.get("name")
            if name:
                schemas[str(name)] = tool
    _TOOL_SCHEMAS[industry] = schemas
    return schemas


def _input_schema(tool: dict[str, Any] | None) -> dict[str, Any]:
    raw = (tool or {}).get("inputSchema") or {}
    return raw if isinstance(raw, dict) else {}


def _prop_schema(tool: dict[str, Any] | None, key: str) -> dict[str, Any]:
    props = _input_schema(tool).get("properties") or {}
    spec = props.get(key) if isinstance(props, dict) else None
    return spec if isinstance(spec, dict) else {}


def _is_prose_arg(key: str, prop: dict[str, Any], industry: str | None = None) -> bool:
    fact_keys = fact_arg_keys_for(industry)
    prose_keys = prose_arg_keys_for(industry)
    if prop.get("enum"):
        return False
    types = prop.get("type")
    type_set = {types} if isinstance(types, str) else set(types or [])
    if type_set & KEEP_ARG_TYPES:
        return False
    if prop.get("format") in KEEP_ARG_FORMATS:
        return False
    if prop.get("pattern"):
        return False
    if key.endswith("_id") or key.endswith("_ids") or key.endswith("_e164"):
        return False
    if key in fact_keys:
        return False
    if key in prose_keys:
        return True
    if key == "reason" and not prop.get("enum"):
        return True
    return key in prose_keys


def _params_of(call: dict[str, Any] | None) -> dict[str, Any]:
    raw = (call or {}).get("parameters")
    if not isinstance(raw, dict):
        raw = (call or {}).get("arguments")
    if not isinstance(raw, dict):
        raw = (call or {}).get("args")
    return dict(raw) if isinstance(raw, dict) else {}


def _output_fields(call: dict[str, Any] | None) -> dict[str, Any]:
    call = call or {}
    output = call.get("output")
    if not isinstance(output, dict):
        output = {}
    fields: dict[str, Any] = {}
    if "ok" in call:
        fields["ok"] = call.get("ok")
    elif "ok" in output:
        fields["ok"] = output.get("ok")
    if "error_code" in call:
        fields["error_code"] = call.get("error_code")
    elif "error_code" in output:
        fields["error_code"] = output.get("error_code")
    return fields


def _as_calls(items: list[Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        if isinstance(item, str):
            out.append({"name": item, "parameters": {}})
        elif isinstance(item, dict) and item.get("name"):
            out.append(item)
    return out


# Office ids/names the healthcare tool server already aliases.
_LOCATION_IDS = {
    "loc_park_ave": "park avenue",
    "loc_brooklyn_heights": "brooklyn heights",
    "loc_windermere": "windermere",
}


HARNESS_ONLY_KEYS = frozenset({"to", "from"})


def _canon_location(value: Any) -> str:
    said = str(value or "").strip().lower()
    if not said:
        return ""
    for loc_id, name in _LOCATION_IDS.items():
        if said == loc_id or said == name:
            return loc_id
    return said


def _same_location(expected: Any, actual: Any) -> bool:
    left, right = _canon_location(expected), _canon_location(actual)
    return bool(left) and left == right


_CARRIER_SLUGS = {
    "aetna": "aetna",
    "unitedhealthcare": "unitedhealthcare",
    "cigna": "cigna",
    "bcbs": "bcbs",
    "bluecross": "bcbs",
    "bluecrossblueshield": "bcbs",
    "medicare": "medicare",
    "medicaid": "medicaid",
    "oscarhealth": "oscar_health",
    "oscar": "oscar_health",
    "other": "other",
}


def _canon_carrier(value: Any) -> str:
    compact = "".join(ch for ch in str(value or "").lower() if ch.isalnum())
    return _CARRIER_SLUGS.get(compact, compact)


def _schema_keys(tool: dict[str, Any] | None) -> set[str]:
    props = _input_schema(tool).get("properties") or {}
    return {str(key) for key in props} if isinstance(props, dict) else set()


def _industry_params(params: dict[str, Any], tool: dict[str, Any] | None) -> dict[str, Any]:
    """Keep keys the industry schema actually declares. Drop harness routing."""
    keys = _schema_keys(tool)
    out: dict[str, Any] = {}
    for key, value in params.items():
        if key in HARNESS_ONLY_KEYS:
            continue
        if keys and key not in keys:
            continue
        if _present_nonempty(value):
            out[key] = value
    return out


def _lev(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


_SAINT_RE = re.compile(r"\bst\b\.?")


# ASR spells speech, not orthography: c/k/q and w/u render the same sounds
# ("Okonkwo" vs "Oconquo"), so fold them before comparing spoken names.
_PHONETIC_FOLD = str.maketrans({"c": "k", "q": "k", "w": "u"})


def _party_tokens(value: Any) -> list[str]:
    text = _SAINT_RE.sub("saint", str(value).casefold())
    return [tok.translate(_PHONETIC_FOLD) for tok in re.findall(r"[a-z0-9]+", text)]


def _fuzzy_in(needle: str, hay: str, tol: int) -> bool:
    if tol == 0:
        return needle in hay
    n = len(needle)
    if n - tol > len(hay):
        return False
    for size in range(max(1, n - tol), min(len(hay), n + tol) + 1):
        for start in range(len(hay) - size + 1):
            if _lev(needle, hay[start:start + size]) <= tol:
                return True
    return False


def _party_match(expected: Any, actual: Any, *, require_all_expected: bool = False) -> bool:
    """At least as tolerant as tool_server._party_said: the verifier must never
    score a call as missing when the gate it grades accepted that spelling.
    Tokens are matched as fuzzy substrings of the other side's joined name, so
    ASR token splits ("Tool Works") and small slips ("Hallowell") both hit.
    require_all_expected: every expected token must appear (rejects truncations
    like "New cases" for "new cases intake") while ASR slips still match."""
    want, got = _party_tokens(expected), _party_tokens(actual)
    if not want or not got:
        return False
    tol = lambda s: 0 if len(s) <= 3 else 1 if len(s) <= 6 else 2  # noqa: E731
    joined_want, joined_got = "".join(want), "".join(got)
    if require_all_expected:
        return all(_fuzzy_in(w, joined_got, tol(w)) for w in want)
    if joined_want in joined_got or joined_got in joined_want:
        return True
    if all(_fuzzy_in(w, joined_got, tol(w)) for w in want):
        return True
    return all(_fuzzy_in(g, joined_want, tol(g)) for g in got)


_NO_DEFAULT = object()


_URGENT_BY_DEFAULT = frozenset({"mohs"})


def _omitted_default(tool: str, key: str, act_params: dict[str, Any]) -> Any:
    """What the tool server uses when the model leaves an optional arg out. With strict
    tools off the model may omit it; omitting a server default is the same call."""
    if tool == "classify_visit_request" and key == "urgency":
        visit = str(act_params.get("visit_class") or "").strip().lower()
        return "urgent" if visit in _URGENT_BY_DEFAULT else "routine"
    if tool == "classify_visit_request" and key == "is_new_patient":
        return False
    return _NO_DEFAULT


def _values_equal(key: str, expected: Any, actual: Any) -> bool:
    if expected == actual:
        return True
    if isinstance(expected, dict) and "any_of" in expected:
        return any(_values_equal(key, option, actual) for option in expected["any_of"])
    if expected is None or actual is None:
        return False
    if key == "for_whom":
        return _party_match(expected, actual, require_all_expected=True)
    if key == "opposing_party":
        return _party_match(expected, actual)
    if key == "location_id" or key.endswith("location_id"):
        return _same_location(expected, actual)
    if key == "carrier":
        left, right = _canon_carrier(expected), _canon_carrier(actual)
        return bool(left) and left == right
    if isinstance(expected, list) and isinstance(actual, list):
        if key == "location_ids":
            exp_ids = {_canon_location(item) for item in expected}
            act_ids = {_canon_location(item) for item in actual}
            return bool(exp_ids) and exp_ids == act_ids
        if len(expected) != len(actual):
            return False
        return all(
            _values_equal(key, left, right)
            for left, right in zip(expected, actual)
        )
    if _is_phone_key(key):
        return _digits_phone(str(expected)) == _digits_phone(str(actual))
    if key == "order_number" and isinstance(expected, str) and isinstance(actual, str):
        # the orders tools accept KE-4483316, KE4483316 and "KE 4483316" as one order
        return re.sub(r"[^0-9A-Za-z]", "", expected).upper() == re.sub(r"[^0-9A-Za-z]", "", actual).upper()
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected is actual
    if isinstance(expected, (int, float)) or isinstance(actual, (int, float)):
        try:
            return float(str(expected)) == float(str(actual))
        except (TypeError, ValueError):
            return _plain(expected) == _plain(actual)
    return _plain(expected) == _plain(actual)


_TYPOGRAPHIC = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"})


def _plain(value: Any) -> str:
    """Case- and typography-insensitive text: the model writes Grimwald\u2019s as often as Grimwald's."""
    return str(value).translate(_TYPOGRAPHIC).strip().casefold()


def _present_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _calls_match(
    expected: dict[str, Any],
    actual: dict[str, Any],
    schemas: dict[str, Any] | None,
    industry: str | None = None,
) -> bool:
    if str(expected.get("name") or "") != str(actual.get("name") or ""):
        return False
    tool = (schemas or {}).get(str(expected.get("name") or ""))
    exp_params = {
        key: value for key, value in _params_of(expected).items()
        if _present_nonempty(value)
    }
    act_params = _industry_params(_params_of(actual), tool)
    # no expected args, or live call has no industry args (harness {to,from},
    # empty Bluejay parameters) → name-only hit. do not invent schema demands.
    if not exp_params or not act_params:
        return True
    for key, exp_value in exp_params.items():
        if industry == "legal" and key == "reason":
            continue
        prop = _prop_schema(tool, key)
        if _is_prose_arg(key, prop, industry):
            if key in act_params and not _present_nonempty(act_params.get(key)):
                return False
            continue
        if key not in act_params:
            default = _omitted_default(str(expected.get("name") or ""), key, act_params)
            if default is _NO_DEFAULT or not _values_equal(key, exp_value, default):
                return False
            continue
        if not _values_equal(key, exp_value, act_params.get(key)):
            return False
    exp_out = _output_fields(expected)
    act_out = _output_fields(actual)
    for field in ("ok", "error_code"):
        if field in exp_out and field in act_out and exp_out[field] != act_out[field]:
            return False
    return True


def tool_call_adherence(
    expected: list[Any],
    actual: list[Any],
    schemas: dict[str, Any] | None = None,
    *,
    industry: str | None = None,
) -> dict[str, Any]:
    """Every expected call must match some actual call of the same name.

    Constrained args (enums, ids, facts) must equal when live args exist.
    Prose args are ignored except required fields must be non-empty.
    Empty live parameters are a name-only hit. Extra actuals are fine.
    """
    exp_calls = _as_calls(expected)
    act_calls = _as_calls(actual)
    extra = _forbidden_extra_calls(exp_calls, act_calls, industry)
    if not exp_calls:
        return {
            "passed": not extra,
            "score": 0.0 if extra else 1.0,
            "missing": [],
            "hit": [],
            "extra": extra,
        }
    used: set[int] = set()
    hit: list[str] = []
    missing: list[str] = []
    for exp in exp_calls:
        found = False
        for index, act in enumerate(act_calls):
            if index in used:
                continue
            if _calls_match(exp, act, schemas, industry):
                used.add(index)
                found = True
                break
        name = str(exp.get("name") or "")
        if found:
            hit.append(name)
        else:
            missing.append(name)
    return {
        "passed": not missing and not extra,
        "score": len(hit) / len(exp_calls),
        "missing": missing,
        "hit": hit,
        "extra": extra,
    }


def _forbidden_extra_calls(
    exp_calls: list[dict[str, Any]],
    act_calls: list[dict[str, Any]],
    industry: str | None,
) -> list[str]:
    """Healthcare confirmation SMS is scored as required or forbidden, never optional."""
    if industry != "healthcare":
        return []
    expected_names = {str(call.get("name") or "") for call in exp_calls}
    if "send_sms" in expected_names:
        return []
    if any(str(call.get("name") or "") == "send_sms" for call in act_calls):
        return ["send_sms"]
    return []


def expected_handoff_path(task: dict[str, Any] | None) -> list[str]:
    path = (task or {}).get("exp_handoff_path") or []
    return [str(item) for item in path]


def actual_handoffs(actual_tools: list[str], industry: str | None = None) -> list[str]:
    allowed = handoff_tools_for(industry)
    return [name for name in actual_tools if name in allowed]


def handoff_adherence(expected: list[str], actual: list[str]) -> dict[str, Any]:
    """Expected hops must appear in order. Empty expected always passes."""
    if not expected:
        return {
            "passed": True,
            "verdict": "exact" if not actual else "none_required",
            "score": 1.0,
            "expected": expected,
            "actual": actual,
        }
    i = 0
    for hop in actual:
        if i < len(expected) and hop == expected[i]:
            i += 1
    matched = i / len(expected)
    if actual == expected:
        verdict = "exact"
    elif i == len(expected):
        verdict = "in_order_with_extras"
    else:
        verdict = "incomplete"
    return {
        "passed": verdict in {"exact", "in_order_with_extras"},
        "verdict": verdict,
        "score": matched,
        "expected": expected,
        "actual": actual,
    }

