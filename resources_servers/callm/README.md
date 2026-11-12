# callm resources server

The CALLM environment. One server hosts every configured industry; per rollout it holds a
`callm.env.Session` keyed by the Gym session cookie: a fresh seeded database on the
industry's tool server, the position in the multi-agent graph, and the caller simulator.

| Route | Body | Returns |
|---|---|---|
| `/seed_session` | dataset row (`industry`, `case_key`) | starts the call |
| `/session_state` | none | active agent's `system_prompt`, `tools`, `done` |
| `/{tool}` | tool arguments | tool result; `UNKNOWN_TOOL` unless the active agent owns the tool |
| `/end_turn` | `{agent_text}` | caller reply `{text, hangup, done}` |
| `/verify` | row + `response` | `reward`, `conjunctive`, `shaped`, components, trace, transcript, swaps, final DB |

Config (`configs/callm.yaml`):

- `user_model_server`: the caller simulator's model server. Never the policy.
- `industries`: which packs to serve (default all three).
- `reward`: `conjunctive` (default, the CALLM metric) or `shaped` (partial credit).

Data: `data/example.jsonl` (5 healthcare cases) and one file per industry, regenerated with
`callm dataset --industry <name>`. Rows hold identifiers only; task content is read from
`industries/` in this repo at run time. License: MIT.
