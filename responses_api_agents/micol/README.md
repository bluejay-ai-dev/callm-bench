# micol agent server

Drives the model under test through one MICOL call. It owns no MICOL logic: it runs the
shared turn loop (`micol.loop.run_episode`) with the policy behind `model_server` and the
environment behind the `micol` resources server.

Per model call it asks the resources server for the active agent's system prompt and tools,
so a handoff swaps both before the next call. Policy calls go through `url_path_for_run`,
which lets a training model server capture tokens per call. The trajectory it returns starts
with the entry agent's prompt as the environment served it; later swaps are in
`system_prompt_swaps`.

Config: `resources_server`, `model_server`, `max_exchanges` (30), `max_tool_rounds` (8 model
calls per agent turn). A rollout that crashes returns reward 0 with failure class
`micol_agent_error`, so Gym excludes it from scores.
