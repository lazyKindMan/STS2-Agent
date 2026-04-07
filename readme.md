# STS2 Agent (personal draft)

Personal sandbox for experimenting with an automated agent for **Slay the Spire 2**. Not intended for open source yet; this doc just tracks my setup and dev notes. If I open it later, I’ll add license/contrib sections then.

## Table of Contents
- [Goal](#goal)
- [Repo Layout](#repo-layout)
- [Quickstart](#quickstart)
- [Dev Notes](#dev-notes)
- [TODO](#todo)

## Goal
Get a minimal loop running: fetch observations from the game/sim, send actions, and test simple policies. Fancier learning or open-source hygiene can come later.

## Repo Layout
- `agent/`: core logic—env wrappers, policies/models, rollout or replay scripts.
- `mod/`: (optional) bridge/MOD code to talk to the game.
- `requirements.txt`: placeholder for Python deps (currently empty; fill as you go).
- `readme.md`: these notes.

## Quickstart
1) Create a virtual env (Python 3.10+)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```
2) Install deps  
`requirements.txt` exists but is empty—append packages as you add them, then run:
```bash
pip install -r requirements.txt
```
3) Connect to STS2  
- If using a MOD bridge, place it under `mod/` and jot install steps.  
- No live game yet? Write a mock env in `agent/` to exercise the loop first.

## Dev Notes
- Build the smallest env wrapper first; lock down obs/action formats.
- Run smoke tests with rule-based or random policy to prove the loop.
- Layer in PPO/IL/etc. gradually; keep runner scripts in `agent/` for reuse.
- Prefer configs (YAML/TOML) for hyperparams to compare runs easily.

## TODO
- [ ] Define a clear obs/action protocol (agent <-> mod).
- [ ] Ship a baseline policy + smoke test.
- [ ] Keep `requirements.txt` updated as deps stabilize (consider pinning/lockfile later).
- [ ] Document MOD install/launch steps (if used).
- [ ] Add simple eval metrics (win rate, DPS, decision latency).

If I decide to open-source, I’ll append contribution guidelines and a license then.
