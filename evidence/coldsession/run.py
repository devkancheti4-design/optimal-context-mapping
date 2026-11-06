"""A repository through every arm and session, each session its own process, in the order that carries lessons forward. Resumes. Stops at the spending cap.

    <modeld python> -I run.py <repo> [--arms alone,notes,map,modeld,guess]"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SESSIONS  # noqa: E402

repo = sys.argv[1]
arms = sys.argv[sys.argv.index("--arms") + 1].split(",") if "--arms" in sys.argv else ["guess", "modeld", "alone", "map", "notes"]
for arm in arms:
    for session in SESSIONS[arm]:
        code = subprocess.run([sys.executable, "-I", os.path.join(HERE, "session.py"), repo, arm, str(session)]).returncode
        if code == 3:
            sys.exit("stopped at the spending cap")
        if code == 4:
            sys.exit("stopped: under 1 GB of disk free")
        if code:
            sys.exit(f"{arm} session {session} failed with exit code {code}")
print("RUN DONE", repo, flush=True)
