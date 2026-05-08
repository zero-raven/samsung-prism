"""
FinSight Setup Wizard
=====================
Always prompts for secret keys (Groq, Telegram bot, Finnhub) for safety.
Validates each one live, writes .env, then launches the pipeline with
live per-skill progress.

Usage:
    python setup.py            # standard run
    python setup.py --no-run   # set up keys, don't launch pipeline
    python setup.py --keep     # opt-in: reuse stored secret keys (skip re-prompt)
"""

import argparse
import getpass
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

# Best-effort UTF-8 stdout so pipeline output (emojis/arrows) doesn't crash on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).parent.resolve()
ENV_PATH = ROOT / ".env"


# ── ANSI color helpers (Windows 10+ terminals support ANSI natively) ───

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"


CYAN = lambda s: _c("36", s)
GREEN = lambda s: _c("32", s)
RED = lambda s: _c("31", s)
YELLOW = lambda s: _c("33", s)
GREY = lambda s: _c("90", s)
BOLD = lambda s: _c("1", s)


# ── .env I/O ───────────────────────────────────────────────────────

def read_env() -> dict:
    if not ENV_PATH.exists():
        return {}
    out = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip()
    return out


def write_env(env: dict):
    body = "\n".join(f"{k}={v}" for k, v in env.items()) + "\n"
    ENV_PATH.write_text(body, encoding="utf-8")


# ── Validators (each returns (ok: bool, detail: str)) ──────────────

def v_groq(key, env):
    try:
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=(5, 8),
        )
        if r.status_code == 200:
            return True, "OK"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"network error: {e}"


def v_tg_bot(token, env):
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=(5, 8))
        if r.status_code == 200 and r.json().get("ok"):
            return True, f"@{r.json()['result'].get('username', '?')}"
        return False, r.json().get("description", "invalid token")
    except Exception as e:
        return False, f"network error: {e}"


def v_tg_chat(chat_id, env):
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return False, "needs TELEGRAM_BOT_TOKEN first"
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getChat",
            params={"chat_id": chat_id},
            timeout=(5, 8),
        )
        if r.status_code == 200 and r.json().get("ok"):
            res = r.json()["result"]
            label = res.get("username") or res.get("first_name") or res.get("title", "chat")
            return True, f"chat -> {label}"
        return False, r.json().get("description", "chat not found / bot blocked")
    except Exception as e:
        return False, f"network error: {e}"


def v_finnhub(key, env):
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": "AAPL", "token": key},
            timeout=(5, 8),
        )
        c = r.json().get("c") if r.status_code == 200 else None
        if isinstance(c, (int, float)) and c > 0:
            return True, f"AAPL ${c}"
        return False, f"HTTP {r.status_code} or empty quote"
    except Exception as e:
        return False, f"network error: {e}"


# ── Key specs ──────────────────────────────────────────────────────

KEYS = [
    {
        "name": "GROQ_API_KEY",
        "label": "Groq API key",
        "hint": "https://console.groq.com/keys",
        "required": True,
        "secret": True,
        "validator": v_groq,
    },
    {
        "name": "TELEGRAM_BOT_TOKEN",
        "label": "Telegram bot token",
        "hint": "DM @BotFather, /newbot, copy the token",
        "required": True,
        "secret": True,
        "validator": v_tg_bot,
    },
    {
        "name": "TELEGRAM_CHAT_ID",
        "label": "Telegram chat ID",
        "hint": "send /start to your bot, then visit https://api.telegram.org/bot<TOKEN>/getUpdates",
        "required": True,
        "secret": False,
        "validator": v_tg_chat,
    },
    {
        "name": "FINNHUB_API_KEY",
        "label": "Finnhub API key (optional)",
        "hint": "https://finnhub.io/register — leave blank to skip Finnhub source",
        "required": False,
        "secret": True,
        "validator": v_finnhub,
    },
]


# ── UI helpers ─────────────────────────────────────────────────────

def mask(value: str, secret: bool) -> str:
    if not value:
        return "(blank)"
    if not secret:
        return value
    if len(value) <= 8:
        return "***"
    return value[:4] + "..." + value[-4:]


def show(spec, value, detail, ok):
    mark = GREEN("[OK]") if ok else YELLOW("[--]")
    print(f"  {mark} {spec['name']:<22} {mask(value, spec['secret']):<28} {detail}")


def prompt(spec, env, step, total):
    print()
    print(CYAN(f"─── Step {step}/{total} ──────────────────────────────────────"))
    print(BOLD(f"  {spec['label']}{'  (required)' if spec['required'] else '  (optional)'}"))
    hint = spec["hint"]
    if spec["name"] == "TELEGRAM_CHAT_ID" and env.get("TELEGRAM_BOT_TOKEN"):
        hint = f"send /start to your bot, then visit https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/getUpdates"
    print(GREY(f"    hint: {hint}"))
    use_getpass = spec["secret"] and sys.stdin.isatty()
    if use_getpass:
        try:
            return getpass.getpass("    value (hidden): ").strip()
        except (EOFError, getpass.GetPassWarning):
            pass
    return input("    value: ").strip()


# ── Main flow ──────────────────────────────────────────────────────

def run_setup(keep_secrets: bool = False):
    print(BOLD(CYAN("=" * 60)))
    print(BOLD(CYAN("  FinSight Setup")))
    print(GREY(f"  .env: {ENV_PATH}"))
    if not keep_secrets:
        print(GREY("  Secret keys will be re-prompted every run for safety."))
    print(BOLD(CYAN("=" * 60)))

    env = read_env()
    total = len(KEYS)

    for i, spec in enumerate(KEYS, 1):
        name = spec["name"]
        existing = env.get(name, "").strip()
        is_secret = spec["secret"]

        # Non-secret keys: validate existing first; only prompt if missing or invalid.
        # Secret keys: always re-prompt (safety) unless --keep is set AND the stored
        # value validates.
        if existing and (not is_secret or keep_secrets):
            ok, detail = spec["validator"](existing, env)
            if ok:
                show(spec, existing, detail, True)
                continue
            if not spec["required"]:
                show(spec, existing, f"kept, but failed: {detail}", False)
                continue
            print(YELLOW(f"  [!] {name} present but failed: {detail} — re-prompting"))

        # Prompt loop
        while True:
            val = prompt(spec, env, i, total)
            if not val:
                if spec["required"]:
                    print(YELLOW("    required — try again, or Ctrl-C to abort."))
                    continue
                # Optional + blank input: keep existing value if any (blank = "skip re-key").
                if existing:
                    env[name] = existing
                    show(spec, existing, "kept existing (not re-validated)", True)
                else:
                    env[name] = ""
                    show(spec, "", "skipped", False)
                break

            ok, detail = spec["validator"](val, {**env, name: val})
            if ok:
                env[name] = val
                show(spec, val, detail, True)
                break

            print(YELLOW(f"    [!] validation failed: {detail}"))
            ans = input("        Save anyway? [y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                env[name] = val
                show(spec, val, f"unverified ({detail})", False)
                break
            # else: loop back, re-prompt

    write_env(env)
    print()
    print(GREEN(f"[OK] .env saved ({len(env)} keys total)"))


# ── Pipeline live progress ─────────────────────────────────────────

SKILL_DESC = {
    1: ("INGEST",    "Fetch news from Google News + GDELT + Finnhub; dedupe by hash"),
    2: ("EXTRACT",   "Groq LLM extracts entities, scores significance, updates knowledge graph"),
    3: ("ANALYZE",   "ChromaDB retrieves historical analogues; Groq synthesizes causal chains"),
    4: ("PORTFOLIO", "Map affected sectors to your holdings; compute exposure %"),
    5: ("SIGNAL",    "Groq generates directional trading signals (BULLISH/BEARISH/NEUTRAL)"),
    6: ("DELIVER",   "Route by confidence: HIGH→immediate, MEDIUM→briefing, LOW→log; push to Telegram"),
}

RE_SKILL_START = re.compile(r">{15,}\s+SKILL\s+(\d+):\s+([A-Z][A-Z ]*?)\s+<{15,}")
RE_SKILL_OK    = re.compile(r"\[OK\]\s+Skill\s+(\d+)\s+complete:?\s*(.*)")
RE_SKILL_ERR   = re.compile(r"\[ERROR\]\s+Skill\s+(\d+)\s+failed:?\s*(.*)")
RE_PAUSE       = re.compile(r"\[PAUSE\]\s+(.*)")
RE_PIPE_DONE   = re.compile(r"Pipeline complete in\s+([0-9.]+)s\.\s+(.*)")
# Lines we strip from the pass-through (replaced by our own banners)
RE_NOISE = re.compile(r"^(={10,}|>{10,}|-{10,})\s*$")


def run_pipeline_with_progress() -> int:
    venv_py = ROOT / "venv" / "Scripts" / "python.exe"
    py = str(venv_py) if venv_py.exists() else sys.executable
    cmd_env = os.environ.copy()
    cmd_env["PYTHONIOENCODING"] = "utf-8"
    cmd_env["PYTHONUNBUFFERED"] = "1"

    print()
    print(BOLD(CYAN("=" * 60)))
    print(BOLD(CYAN("  FinSight Pipeline — Live Progress")))
    print(GREY("  (each skill banner shows what it's doing)"))
    print(BOLD(CYAN("=" * 60)))

    try:
        proc = subprocess.Popen(
            [py, str(ROOT / "pipeline.py")],
            cwd=str(ROOT), env=cmd_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, text=True, encoding="utf-8", errors="replace",
        )
    except Exception as e:
        print(RED(f"[err] failed to launch pipeline: {e}"))
        return 1

    pipeline_start = time.time()
    skill_starts: dict[int, float] = {}

    try:
        for raw in proc.stdout:
            line = raw.rstrip("\n")

            m = RE_SKILL_START.search(line)
            if m:
                n = int(m.group(1))
                skill_starts[n] = time.time()
                name, desc = SKILL_DESC.get(n, (m.group(2), ""))
                print()
                print(CYAN("─" * 60))
                print(BOLD(CYAN(f"▶ SKILL {n}/6: {name}   (running…)")))
                print(GREY(f"  {desc}"))
                print(CYAN("─" * 60))
                continue

            m = RE_SKILL_OK.search(line)
            if m:
                n = int(m.group(1))
                elapsed = time.time() - skill_starts.get(n, pipeline_start)
                summary = m.group(2).strip() or "complete"
                name = SKILL_DESC.get(n, ("", ""))[0]
                print(GREEN(f"  ✓ SKILL {n} ({name}) done in {elapsed:.1f}s — {summary}"))
                continue

            m = RE_SKILL_ERR.search(line)
            if m:
                n = int(m.group(1))
                print(RED(f"  ✗ SKILL {n} FAILED — {m.group(2).strip()}"))
                continue

            m = RE_PAUSE.search(line)
            if m:
                print(YELLOW(f"  ⏸ Paused — {m.group(1).strip()}"))
                continue

            m = RE_PIPE_DONE.search(line)
            if m:
                print(GREEN(BOLD(f"\n[done] Pipeline complete in {m.group(1)}s")))
                print(GREEN(f"       {m.group(2)}"))
                continue

            # Skip pure-separator noise; pass everything else through verbatim,
            # so the user sees per-article / per-event progress in real time.
            if RE_NOISE.match(line):
                continue
            if line.startswith("[Config] Workspace initialized"):
                print(GREY(f"  {line}"))
                continue
            sys.stdout.write(raw)
            sys.stdout.flush()
    except KeyboardInterrupt:
        proc.terminate()
        print(YELLOW("\n[abort] Interrupted; stopping pipeline..."))
    rc = proc.wait()
    total = time.time() - pipeline_start
    print()
    if rc == 0:
        print(GREEN(BOLD(f"[ok] Pipeline finished cleanly in {total:.1f}s")))
        flush_briefing_to_telegram()
    else:
        print(RED(BOLD(f"[err] Pipeline exited with code {rc} after {total:.1f}s")))
    return rc


def flush_briefing_to_telegram():
    """After a successful pipeline run, flush any queued briefing to Telegram so
    the user actually sees something land in their chat. Skill 6 only sends
    HIGH-confidence alerts immediately; MEDIUM-confidence events sit in the
    briefing queue otherwise."""
    queue_path = ROOT / "data" / "briefing" / "queue.yaml"
    if not queue_path.exists() or queue_path.stat().st_size == 0:
        print(GREY("  (no briefing queue to flush)"))
        return
    venv_py = ROOT / "venv" / "Scripts" / "python.exe"
    py = str(venv_py) if venv_py.exists() else sys.executable
    cmd_env = os.environ.copy()
    cmd_env["PYTHONIOENCODING"] = "utf-8"
    cmd_env["PYTHONUNBUFFERED"] = "1"
    print()
    print(CYAN("─" * 60))
    print(BOLD(CYAN("▶ Flushing briefing queue → Telegram")))
    print(GREY("  (sends MEDIUM-confidence events that didn't trigger immediate alerts)"))
    print(CYAN("─" * 60))
    try:
        out = subprocess.run(
            [py, str(ROOT / "deliver.py"), "--briefing"],
            cwd=str(ROOT), env=cmd_env,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60,
        )
        for line in (out.stdout or "").splitlines():
            print(f"  {line}")
        for line in (out.stderr or "").splitlines():
            print(YELLOW(f"  {line}"))
        if "send: OK" in (out.stdout or ""):
            print(GREEN("  ✓ Briefing delivered. Check your Telegram chat."))
        elif "No events in briefing queue" in (out.stdout or ""):
            print(GREY("  (queue was empty — nothing to send)"))
        else:
            print(YELLOW("  [!] Briefing send may have failed — see lines above."))
    except subprocess.TimeoutExpired:
        print(RED("  [!] deliver.py --briefing timed out after 60s"))
    except Exception as e:
        print(RED(f"  [!] flush failed: {e}"))


def maybe_run_pipeline():
    ans = input("\nRun pipeline now? [y/N]: ").strip().lower()
    if ans not in ("y", "yes"):
        print("Skipped. Run later with:  python pipeline.py")
        return
    run_pipeline_with_progress()


def main():
    parser = argparse.ArgumentParser(description="FinSight setup wizard")
    parser.add_argument("--keep", action="store_true",
                        help="Reuse stored secret keys instead of re-prompting (faster, less safe)")
    parser.add_argument("--no-run", action="store_true",
                        help="Don't offer to run the pipeline at the end")
    args = parser.parse_args()

    try:
        run_setup(keep_secrets=args.keep)
        if not args.no_run:
            maybe_run_pipeline()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
