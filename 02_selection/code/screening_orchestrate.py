"""Runs the gated screening steps unattended: next step -> verifier -> step_done message -> wait for the second
system's step_verified for that step -> approve -> next. Stops (exit 3) on any other message, a verifier failure, a
runner error or a malformed status, so that the problem is handled before continuing. Safe to restart: a step already
announced is not announced again, and a step_verified already posted is used.
Usage: screening_orchestrate.py RUN_DIR [RUNNER VERIFIER]  (default: the title/abstract runner and verifier)"""
import datetime, json, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOX = os.path.join(ROOT, "prompts/implementation_records/selection_run/broadcast.jsonl")
D = sys.argv[1]; PY = sys.executable
RUNNER, VERIFIER = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("screening_run.py", "screening_verify.py")
OK_CHATTER = ("ack", "review_started", "note", "progress")


def run(*a):
    return subprocess.run([PY, os.path.join(ROOT, "tools/oct_search", a[0]), *a[1:]], capture_output=True, text=True, cwd=ROOT)


def box():
    return [json.loads(l) for l in open(BOX)]


def post(**m):
    seq = max([x.get("seq", 0) for x in box() if x.get("from") == "claude"] + [0]) + 1
    m = dict(ts=datetime.datetime.now().astimezone().isoformat(timespec="seconds"), **{"from": "claude"}, seq=seq, **m)
    with open(BOX, "a") as f:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return seq


def stop(msg, **kw):
    post(event="orchestrator_stopped", text=msg, **kw); print(msg, flush=True); sys.exit(3)


def status():
    r = run(RUNNER, "status", "--out", D)
    rows = [l.split() for l in r.stdout.splitlines() if l.strip()]
    if r.returncode != 0 or not rows or any(len(x) < 3 or x[2] not in ("done", "pending") for x in rows):
        stop("status failed", detail=(r.stdout + r.stderr)[-800:])
    return rows


while True:
    st = status()
    todo = [x for x in st if not (x[2] == "done" and len(x) >= 4 and x[3] == "approved")]
    if not todo:
        if st[-1][0] != "final":
            stop("no pending step but final not reached", detail=str(st))
        post(event="run_complete", run_dir=D, text="All steps finished and approved."); print("complete", flush=True); break
    name = todo[0][0]
    if todo[0][2] == "pending":
        r = run(RUNNER, "next", "--out", D)
        print(r.stdout, r.stderr, flush=True)
        if r.returncode != 0:
            stop(f"runner error in {name}", step=name, detail=(r.stdout + r.stderr)[-1500:])
        st2 = {x[0]: x for x in status()}
        if name not in st2 or st2[name][2] != "done":
            stop(f"{name} not complete after runner", step=name)
    v = run(VERIFIER, D)
    if v.returncode != 0:
        stop(f"verifier failed after {name}", step=name, detail=v.stdout[-2000:])
    msgs = box()
    announced = [m for m in msgs if m.get("from") == "claude" and m.get("event") == "step_done" and m.get("step") == name and m.get("run_dir") == D]
    if announced:
        start = max(i for i, m in enumerate(msgs) if m is announced[-1])
    else:
        post(event="step_done", step=name, run_dir=D, verifier=v.stdout.strip()[-1500:],
             text=f"Step {name} of run {D} finished. Please verify independently and reply event 'step_verified' with step='{name}' and run_dir='{D}', or findings.")
        start = len(msgs)
    while True:
        new = box()[start:]
        cx = [m for m in new if m.get("from") == "codex"]
        ok = [m for m in cx if m.get("event") == "step_verified" and m.get("step") == name and m.get("run_dir") == D]
        if ok:
            a = run(RUNNER, "approve", name, "--out", D, "--by", "codex", "--ref", f"broadcast seq {ok[0]['seq']} (run_dir {D})")
            print(a.stdout, a.stderr, flush=True)
            if a.returncode != 0:
                stop(f"approve failed for {name}", detail=(a.stdout + a.stderr)[-800:])
            break
        other = [m for m in cx if m.get("event") not in OK_CHATTER and m not in ok and not (m.get("event") == "step_verified" and m.get("run_dir") != D)]
        if other:
            print("stopping on codex message", other[-1], flush=True); sys.exit(3)
        time.sleep(20)
