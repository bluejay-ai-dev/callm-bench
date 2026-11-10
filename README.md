# MICOL Gym

**MICOL (Multi-Industry Conversational LLMs)** is a Bluejay Labs benchmark for the LLMs that
power phone agents. This repo is its environment, packaged for
[NeMo Gym](https://github.com/NVIDIA-NeMo/Gym): the same code scores the MICOL Bench
leaderboard and serves as an RL environment.

The model under test runs a multi-agent front desk (healthcare, legal, customer support) over
text. A pinned simulator model plays the caller and, like a real phone line, the model only
receives what a speech recognizer would have heard: dropped words, misheard names and digits,
clipped and split turns. A deterministic verifier grades every call: required tool calls AND
handoff path AND final database state.

The industry packs and tasks come from [MIVAS](https://github.com/bluejay-ai-dev/mivas-bench),
Bluejay's voice-agent benchmark. This repo ships **9 sample tasks** (3 per industry). The full
180-task suite is held out for the leaderboard.

## Folder structure

```
micol-gym/
├── industries/                 one folder per industry
│   └── <industry>/
│       ├── agent_blueprint.json  the multi-agent graph: agents, entry agent, tool ownership, handoff tools
│       ├── system-prompts/       one system prompt per agent
│       ├── tools.json            tool schemas
│       ├── tool_server.py        FastAPI server that executes tools against a per-call SQLite DB
│       ├── db/                   schema.sql + seed.sql (every call starts from this seed)
│       └── tasks/<case>/task.json  caller brief + expected tool calls, handoff path, final DB
├── src/micol/                  the environment's logic, framework-free
│   ├── bench.py                loads industry packs and tasks
│   ├── env.py                  ToolServer, Episode (DAG + tool scoping), Session (one call), oracle_replay
│   ├── usersim.py              caller simulator: persona from the task, SAID/HEARD, recognizer draws
│   ├── asr_profiles/           the simulated recognizer profile and its measured target rates
│   ├── loop.py                 the turn loop, shared by local runs and the Gym agent server
│   ├── grader.py, verify.py    the three checks, conjunctive verdict, shaped RL reward
│   ├── report.py               task, channel, and LLM metrics for a run
│   ├── latency.py              streamed replay of a run's requests: TTFT, TPOT, tokens/s
│   └── console/                backend for `micol ui`
├── ui/                         the console's web UI (Vite + React)
├── resources_servers/micol/    Gym resources server = the environment (tools, DAG, caller, verifier)
├── responses_api_agents/micol/ Gym agent server = drives the model under test
├── responses_api_models/       chat_passthrough (any OpenAI-compatible chat endpoint), retell_playground
├── configs/                    one config per model on the leaderboard; configs/users/ = callers
└── tests/                      offline: scripted models through the real tool server + verifier
```

A dataset row is just `{industry, case_key}`; the environment loads everything else from
`industries/` at run time.

## The simulated phone line

A real phone agent never sees what the caller said, only what speech-to-text produced. MICOL
puts that gap into a text benchmark without any audio:

- Each caller turn, the simulator writes two lines: `SAID:` (what the caller actually said) and
  `HEARD:` (what a phone recognizer would transcribe). Only `HEARD` reaches the model under test.
- The recognizer's behavior lives in a profile, `src/micol/asr_profiles/stt-simulated-gpt-6.1-sol.md`,
  calibrated against 5,289 real caller turns from phone calls. Its measured target rates sit next
  to it in `.stats.json`.
- Before each turn the environment rolls a **recognizer draw** from those real rates (seeded by
  task, attempt, and turn, so reruns are reproducible): correct, minor error, substantial error,
  clipped, or not transcribed, plus whether the turn splits across two agent turns, keeps its
  final punctuation, or comes out lowercase. The simulator writes `HEARD` to match the draw and
  code enforces the mechanical parts.
- A turn the recognizer drops is never handed to the model as an empty message: the caller hears
  silence and speaks again, as on a real line.

`configs/users/sol.yaml` is the same caller with a clean channel (`HEARD` = `SAID`), for
comparison.

## How one rollout runs

| Gym concept | MICOL |
|---|---|
| model server (`policy_model`) | the model under test |
| model server (`user_model`) | the caller simulator, pinned, never trained |
| resources server | the industry: tool server + per-call SQLite, multi-agent DAG, caller, verifier |
| agent server | the turn loop driving the policy through one call |
| dataset row | one task (`industry`, `case_key`) |
| rollout | one phone call |
| `/verify` reward | the MICOL verdict |

```
agent server                                resources server (session = this rollout)
------------                                -----------------------------------------
POST /seed_session {industry, case_key} ->  fresh seeded DB, active agent = entry agent, caller
POST /session_state                     ->  {system_prompt, tools, done}   (the active agent's)
model server: messages[0] = system_prompt, tools = that agent's tools
  model calls a tool                    ->  POST /{tool}: refused unless the active agent owns it;
                                            handoff tools switch the active agent
  model speaks                          ->  POST /end_turn {agent_text}: caller replies (HEARD only)
... until the caller hangs up, the desk ends the call, or 30 exchanges
POST /verify                            ->  grader: tools, handoffs, final DB; session released
```

A handoff replaces `messages[0]` and the toolset in place; the conversation after it is
unchanged. Every swap is recorded (`system_prompt_swaps`), so a training model server captures
each call's tokens under the prompt that was actually active.

## Reward and metrics

`/verify` returns:

- `conjunctive`: the MICOL metric. 1.0 only if tool adherence AND handoff adherence AND
  final-DB adherence all pass.
- `shaped`: partial credit for RL, the mean of `tool_reward`, `state_reward`, and `handoff_reward`.
- `reward`: what Gym reads. `conjunctive` by default; set `reward: shaped` on the resources
  server to train on partial credit.

Each rollout also carries `components` (per-check detail), `trace` (every tool call with the
agent that made it), `transcript` (with `said`, `heard`, and the draw for every caller turn),
`final_state`, and a record per model call (latency, tokens, served model, finish reason).

`micol report --run <id>` turns a run into the leaderboard metrics: pass@1 and pass^k, results
by category and difficulty, how the realized channel compares to the profile's targets, how
often a misheard value was written to the database, clarification and read-back rates, and LLM
metrics (tokens, cache hits, errors, tool-call validity, cost). `micol latency --run <id>`
replays the run's requests streamed, one at a time, for TTFT, time to first sentence, TPOT,
and tokens/s.

## Run it

```bash
uv sync                                    # installs micol + nemo-gym (gives the `gym` CLI)
export OPENAI_API_KEY=...                  # model under test and caller in these configs
export RAY_ENABLE_UV_RUN_RUNTIME_ENV=0     # Ray's uv hook breaks on per-server venvs
source .venv/bin/activate

gym env start "+config_paths=[configs/gpt41.yaml,configs/users/stt-simulated-gpt-6.1-sol.yaml]" \
    "++skip_venv_if_present=true"

# in another shell, same env:
gym eval run --no-serve +agent_name=micol_agent \
    +input_jsonl_fpath=resources_servers/micol/data/example.jsonl \
    +output_jsonl_fpath=results/example_rollouts.jsonl +limit=null
```

Datasets: `resources_servers/micol/data/{healthcare,legal,customer-support}.jsonl`, or write
your own with `micol dataset --industry <industry>`.

**Other models.** Every model on the leaderboard has a config in `configs/`. Hosted APIs read
their usual key (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `RETELL_API_KEY`).
The PhoneLLM configs point at any OpenAI-compatible server for the open weights
(`PHONELLM_BASE_URL`, `PHONELLM_API_KEY`). For training, make `policy_model` your `vllm_model`
server so tokens and log-probs are captured, and leave `user_model` pinned.

**Without Gym.** `micol run --industry healthcare --task hc-tgcr` plays a call locally through
the same loop (per-role models via `MICOL_AGENT_*` / `MICOL_USER_*`).

## Console

```bash
(cd ui && npm install && npm run build)    # once, and after UI changes
echo "OPENAI_API_KEY=..." >> .env          # the console reads the repo's .env (gitignored)
micol ui                                   # http://127.0.0.1:8765
```

Start runs (any config, any caller, k attempts per task), watch them live, and open any call as
a timeline: each caller turn shows what the model heard and what the caller actually said, every
tool call with its arguments and result, each handoff with the new agent's prompt, beside the
grade (expected vs actual calls, handoff path, and final database).

## Checks

```bash
uv run pytest                               # offline: scripted models, real tool server + verifier
micol oracle --industry healthcare --all    # replay each answer key, no model; expect 1.0
```

The oracle replays a task's expected tool calls with no model and no caller and checks that they
produce the expected database. Every task replays to 1.0.

In `exp_tool_calls`, `parameters` is what the grader checks. An `{"any_of": [...]}` value
accepts any listed option. `oracle_parameters` holds a reference value for an argument the task
leaves to the agent; the oracle sends it, the grader ignores it.

## Training notes

- Pin `user_model` to a fixed model that is not being trained; a caller that drifts with the
  policy makes the environment non-stationary.
- The sample tasks are for evaluation. Train on tasks generated from the same industry packs.
- Verification recomputes from the trace and database (no model calls), so Gym's reverification
  works.

## License

MIT. See [LICENSE](LICENSE).
