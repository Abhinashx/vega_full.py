# -*- coding: utf-8 -*-
"""
abhi_x4.py  — Final self-update + self-rewrite enabled assistant (clean)
Place in /sdcard/, run with Python 3 inside your environment.

Features:
- Safe "update from GitHub" (clone, backup, replace, restart)
- Safe "rewrite code" (typed confirmation, backup, write, restart)
- Download book support and offline library hooks
- Permission & typed-confirmation required for risky ops
- Works on Termux (if git present) and Ubuntu
"""

import os
import sys
import shutil
import tempfile
import subprocess
import time
import json
from pathlib import Path

# ---------- Configuration ----------
SELF_PATH = Path(__file__).resolve()
LIB_DIR = Path("/sdcard/abhi_lib")
BACKUP_DIR = Path("/sdcard/abhi_backup")
MEMORY_FILE = Path("/sdcard/abhi_memory.json")
MAX_REPLACE_BYTES = 2 * 1024 * 1024  # 2 MB safety limit for replacement

# Ensure directories exist
LIB_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
if not MEMORY_FILE.exists():
    MEMORY_FILE.write_text("[]", encoding="utf-8")

# ---------- Utilities ----------
def log(msg):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")

def save_memory(entry):
    try:
        arr = json.loads(MEMORY_FILE.read_text(encoding="utf-8") or "[]")
    except Exception:
        arr = []
    arr.append({"time": time.time(), "entry": entry})
    MEMORY_FILE.write_text(json.dumps(arr, indent=2), encoding="utf-8")

def typed_confirm(prompt="Type CONFIRM: YES to proceed"):
    print(prompt)
    ans = input("> ").strip()
    return ans == "CONFIRM: YES"

def backup_self():
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{SELF_PATH.stem}_backup_{ts}.py"
    shutil.copy2(SELF_PATH, dest)
    log(f"Backup created: {dest}")
    save_memory({"action":"backup", "backup_path": str(dest), "ts": time.time()})
    return dest

# ---------- Git helper (tries git CLI, otherwise raises) ----------
def git_clone(repo_url, branch="main"):
    tmp = Path(tempfile.mkdtemp(prefix="abhi_update_"))
    log(f"Cloning repo {repo_url} into {tmp} ...")
    # prefer system git
    git_cmd = shutil.which("git")
    if git_cmd:
        try:
            subprocess.run([git_cmd, "clone", "--depth", "1", "--branch", branch, repo_url, str(tmp)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log("Clone (git CLI) succeeded.")
            return tmp
        except subprocess.CalledProcessError as e:
            shutil.rmtree(tmp, ignore_errors=True)
            log(f"git clone failed: {e.stderr.decode(errors='ignore') if hasattr(e,'stderr') else e}")
            raise RuntimeError("git clone failed")
    else:
        # try gitpython if installed
        try:
            from git import Repo
            Repo.clone_from(repo_url, tmp, branch=branch)
            log("Clone (GitPython) succeeded.")
            return tmp
        except Exception as e:
            shutil.rmtree(tmp, ignore_errors=True)
            log(f"Clone failed (no git CLI and gitpython unavailable): {e}")
            raise RuntimeError("git clone failed - install git or gitpython")

# ---------- Update from GitHub ----------
def update_from_github(repo_url: str, branch: str = "main", repo_file_path: str | None = None):
    """
    repo_url: HTTPS git url, e.g. https://github.com/user/repo.git
    branch: branch name to clone
    repo_file_path: optional path within repo to the file to copy (e.g. 'abhi_x4.py' or 'src/assistant.py').
                    if None, will try to find a file with same name as SELF_PATH.name
    """
    log("REQUEST: update_from_github")
    if not typed_confirm("Dangerous: This will replace the running script. Type CONFIRM: YES to continue"):
        log("User declined update.")
        return False

    # clone
    try:
        repo_tmp = git_clone(repo_url, branch=branch)
    except Exception as e:
        log(f"Clone error: {e}")
        return False

    # determine candidate file
    candidate = None
    if repo_file_path:
        p = (repo_tmp / repo_file_path)
        if p.exists():
            candidate = p
    else:
        # try to find file with same base name
        desired = SELF_PATH.name
        found = list(repo_tmp.rglob(desired))
        if found:
            candidate = found[0]

    if not candidate:
        # fallback: find top-level python file if any
        py_files = list(repo_tmp.rglob("*.py"))
        candidate = py_files[0] if py_files else None

    if not candidate or not candidate.exists():
        log("Update failed: could not find replacement file in repo.")
        shutil.rmtree(repo_tmp, ignore_errors=True)
        return False

    size = candidate.stat().st_size
    if size > MAX_REPLACE_BYTES:
        log(f"Refusing to replace: candidate file too large ({size} bytes). Limit {MAX_REPLACE_BYTES}.")
        shutil.rmtree(repo_tmp, ignore_errors=True)
        return False

    # backup current
    backup_self()

    # copy candidate over SELF_PATH
    try:
        shutil.copy2(candidate, SELF_PATH)
        log(f"Replaced {SELF_PATH} with {candidate}")
        save_memory({"action":"update_from_github","repo":repo_url,"file":str(candidate), "ts": time.time()})
    except Exception as e:
        log(f"Failed to copy new file into place: {e}")
        shutil.rmtree(repo_tmp, ignore_errors=True)
        return False
    finally:
        shutil.rmtree(repo_tmp, ignore_errors=True)

    # restart process
    log("Restarting process to apply update...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

# ---------- Rewrite self from input ----------
def rewrite_self_from_input():
    log("REQUEST: rewrite_self_from_input")
    if not typed_confirm("You are about to overwrite this script. Type CONFIRM: YES to proceed"):
        log("User declined rewrite.")
        return False

    log("Enter new code. End with a single line containing EOF")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "EOF":
            break
        lines.append(line)

    new_code = "\n".join(lines)
    if not new_code.strip():
        log("No code provided; aborting.")
        return False

    # safety: limit size
    if len(new_code.encode("utf-8")) > MAX_REPLACE_BYTES:
        log("Provided code too large; aborting.")
        return False

    backup_self()
    try:
        with open(SELF_PATH, "w", encoding="utf-8") as f:
            f.write(new_code)
        log("Self file rewritten successfully.")
        save_memory({"action":"rewrite_self","ts": time.time()})
    except Exception as e:
        log(f"Failed to write new code: {e}")
        return False

    log("Restarting to run new version...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

# ---------- Simple book download helper (with typed confirmation) ----------
def download_book_to_lib(url: str, filename: str | None = None):
    if not typed_confirm("Download book from internet? Type CONFIRM: YES to allow"):
        log("User declined download.")
        return False
    import requests
    filename = filename or url.split("/")[-1]
    safe_name = filename if filename.endswith(".txt") else f"{filename}.txt"
    dest = LIB_DIR / safe_name
    try:
        log(f"Downloading {url} -> {dest}")
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            dest.write_text(r.text, encoding="utf-8")
            log("Download saved.")
            save_memory({"action":"download_book","url":url,"file":str(dest),"ts":time.time()})
            return True
        else:
            log(f"Download failed: HTTP {r.status_code}")
            return False
    except Exception as e:
        log(f"Download exception: {e}")
        return False

# ---------- Small helpers for library ----------
def list_books():
    return sorted([p.name for p in LIB_DIR.glob("*.txt")])

def read_book(name):
    p = LIB_DIR / name
    if not p.exists():
        log("Book not found.")
        return
    print(f"---- START {name} ----")
    print(p.read_text(encoding="utf-8", errors="ignore")[:20000])  # print first chunk (avoid huge dumps)
    print(f"---- END {name} ----")
    save_memory({"action":"read_book","file":str(p),"ts":time.time()})

# ---------- CLI / Main loop ----------
def print_help():
    print("""
Available admin commands:
  help
  list books
  read <bookname.txt>
  download <url> [filename.txt]   (requires CONFIRM: YES)
  update github <repo_url> [branch] [file_path_in_repo]
       e.g. update github https://github.com/user/repo.git main abhi_x4.py
  rewrite self
  backup
  exit
Notes:
 - For update/rewrite/download operations you MUST type the exact confirmation string:
     CONFIRM: YES
""".rstrip())

def main_loop():
    log("ABHI ready (self-update enabled).")
    print_help()
    while True:
        try:
            cmd = input("\nabhi> ").strip()
        except (EOFError, KeyboardInterrupt):
            log("Shutting down (input closed).")
            break

        if not cmd:
            continue
        parts = cmd.split()
        if parts[0].lower() in ("help","h","?"):
            print_help()
            continue

        if cmd.lower() == "list books":
            print("\n".join(list_books() or ["<no books>"]))
            continue

        if parts[0].lower() == "read" and len(parts) >= 2:
            name = " ".join(parts[1:])
            read_book(name)
            continue

        if parts[0].lower() == "download" and len(parts) >= 2:
            url = parts[1]
            filename = parts[2] if len(parts) >= 3 else None
            download_book_to_lib(url, filename)
            continue

        if parts[0].lower() == "update" and len(parts) >= 3 and parts[1].lower() == "github":
            repo_url = parts[2]
            branch = parts[3] if len(parts) >= 4 else "main"
            repo_file = parts[4] if len(parts) >= 5 else None
            update_from_github(repo_url, branch=branch, repo_file_path=repo_file)
            continue

        if cmd.lower() == "rewrite self":
            rewrite_self_from_input()
            continue

        if cmd.lower() == "backup":
            backup_self()
            continue

        if cmd.lower() == "exit":
            log("Exit requested by user.")
            break

        print("Unknown command. Type 'help' for list.")

if __name__ == "__main__":
    main_loop()
