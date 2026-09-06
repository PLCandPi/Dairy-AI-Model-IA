# Setup Status — resume here

Last updated: 2026-09-05, ~23:15 IST. Session paused here; phone left running the
in-progress install. Read this before doing anything else next session.

## Where things stand

The phone (Termux, SSH on `192.168.1.6:8022`, user `u0_a167`, key
`~/.ssh/termux_agent` on the dev machine) is mid-way through
`pip install -r requirements.txt`, running detached (`nohup ... & disown`) as
PID-tree rooted around the `pip install` process — **it survives Termux/SSH
being killed**, so leaving the phone alone is fine.

- Log: `~/reqs_install6.log` on the phone.
- Last confirmed state: `hf-xet` finished and got cached as a wheel; now
  building `tokenizers` (reusing the already-cached `maturin` binary, so this
  should be faster than earlier builds).
- Remaining after `tokenizers`: `pyyaml`, `regex`, `safetensors` also need
  building — all should reuse cached `maturin` and go quickly based on
  earlier runs this session.

## First thing next session: check if it finished

```bash
ssh -p 8022 -i ~/.ssh/termux_agent u0_a167@192.168.1.6 'tail -40 ~/reqs_install6.log'
```

- If it ends with `Successfully installed ...` — done, skip to **Next steps**.
- If it's still running — check `pgrep -c rustc` / `pgrep -fla cargo` to see
  if it's actively compiling (CPU time climbing) vs actually stuck, and just
  keep waiting; nothing else needs doing.
- If it shows an error — see **Known issues fixed this session** below, the
  pattern for every failure so far has been: check `pkg search <name>` for a
  native Termux package first, or diagnose the actual compiler error rather
  than blindly retrying.

## Next steps once `pip install -r requirements.txt` succeeds

```bash
ssh -p 8022 -i ~/.ssh/termux_agent u0_a167@192.168.1.6 '
export ANDROID_API_LEVEL=24
python -c "import transformers, peft, datasets, accelerate; print(\"OK\")"
'
```

Then launch training (downloads `Qwen/Qwen3-0.6B` from Hugging Face first,
~1.2GB, then starts the actual LoRA fine-tune):

```bash
ssh -p 8022 -i ~/.ssh/termux_agent u0_a167@192.168.1.6 '
cd ~/Termux-LLM-Training
nohup python train.py > ~/train_run.log 2>&1 &
disown
'
```

Watch `~/train_run.log` for real loss values appearing with no
crash/traceback — that's the actual end-to-end proof this whole pipeline
works, which we have not yet reached.

`train.py` is resumable by design (checkpoints every 20 steps to `output/`,
picks up automatically if the process dies) — safe to just re-run if
interrupted.

## Known issues fixed this session (don't re-debug these)

- `pip install torch` always fails on Termux (no PyPI wheel for
  Android/Bionic) — `torch` must come from `pkg install python-torch`, never
  pip. Already installed (2.11.0).
- `ANDROID_API_LEVEL` must be exported (`24`, matching Termux's own NDK
  target) before any `pip install` that compiles a Rust extension
  (tokenizers/safetensors/hf-xet all use `maturin`) — without it, maturin
  fails with "Failed to determine Android API level". Already added to
  `~/.bashrc` on the phone, but re-export it in any fresh shell that doesn't
  source `.bashrc` (e.g. a raw `ssh host 'cmd'` invocation).
- `psutil` (pulled in by `accelerate`) refuses to build from source on
  Android ("platform android is not supported" — hardcoded in its setup.py).
  Fixed: `pkg install python-psutil` (native package, already installed).
- `pyarrow` (pulled in by `datasets`) has no Android wheel and would try
  building the full Arrow C++ codebase from source. Fixed: `pkg install
  python-pyarrow` (native package, already installed).
- `numpy`'s **isolated build environment** (triggered when `pandas` builds
  from source and re-resolves `numpy>=2.0.0` as its own build dependency,
  ignoring the already-installed native `python-numpy`) hits a real Android
  Bionic libc bug: missing `long double` complex-math functions (`cpowl`,
  `cexpl`, etc). Fixed: install `pandas` with `pip install
  --no-build-isolation pandas` so it reuses the working native `numpy`
  instead of rebuilding a fresh (buggy) one. Already done — `pandas` 3.0.5
  installed successfully this way.
- `cmake`/`ninja` PyPI wrapper packages are **not needed** — `pkg install
  cmake ninja` (native binaries) plus pre-installing `meson-python`, `meson`,
  `Cython`, `versioneer`, `setuptools-scm` via plain `pip install` (not as
  part of a bigger combined install) was enough for `meson-python` to find
  the system `cmake`/`ninja` directly. Trying to `pip install cmake ninja`
  directly triggers a very slow GitHub binary download — avoid it.
- Never `pkill -f "<pattern>"` where the pattern appears in the invoking
  shell command itself (e.g. `pkill -f "pip install"` run via `ssh host
  'pkill -f "pip install"; ...'`) — it self-matches the wrapper shell and
  kills the whole SSH session before later commands run. Kill by explicit
  PID instead.
- Background jobs launched with `nohup ... & disown` survive the Termux
  app/SSH session being killed (confirmed empirically once this session,
  ~2hrs into a build, when Termux got killed by Android but the pip install
  kept running underneath). Always launch long builds this way.

## Repo/environment reference

- Repo: `github.com/PLCandPi/Dairy-AI-Model-IA` (public, renamed from
  `Termux-LLM-Training`). Cloned on the phone at `~/Termux-LLM-Training`,
  and locally at `/home/alvinad/Termux-LLM-Training` - the local folder
  names still use the old repo name; only the GitHub repo itself was
  renamed.
- `train.py`, `setup_termux.sh`, `requirements.txt`, and the seed dataset
  (`data/dairy_domain_seed.jsonl`, `data/heatwatch_codebase_seed.jsonl`) are
  already committed — see `README.md` for the full design rationale (model
  choice, LoRA config, why fp32, why `--no-build-isolation` isn't baked into
  `setup_termux.sh` itself — it wasn't needed until `pandas` specifically).
- No Claude/Anthropic attribution in commits for this project (explicit user
  instruction).
- Real hardware constraints established this session: phone is a Snapdragon
  675 / Adreno 612 (`sm6150`), 5.6GB RAM (~2.6-2.8GB actually available),
  7 CPU cores. Adreno 612 **cannot** be used for training (confirmed via
  research — GPU-accelerated LoRA training tools like QVAC Fabric require
  Adreno 800-series; this is a hardware generation gap, not fixable). CPU-only
  training is the only path on this device, hence `Qwen3-0.6B` (not 1.7B —
  too tight for training, fine for inference-only via Ollama separately).
