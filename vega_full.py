#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

vega_abhinash.py - Full version

ABHINASH — voice assistant + mobile control + trading helper + ethical pentest (whitelist+token+typed-confirm).

IMPORTANT:

- Edit the generated files under /sdcard/vega_logs/ (whitelist & approved_commands) BEFORE running any authorized actions.

- Dangerous actions require: whitelist entry + invite token typed into terminal + typed CONFIRM: YES.

- This script intentionally avoids building/executing exploit payloads.

"""

import os, time, json, threading, subprocess, requests, re, sys, shutil

from collections import Counter

# ---------------- User settings ----------------

ASSISTANT_NAME = "ABHINASH"

OPERATOR_NAME = "ARVIND"

# HuggingFace token (embedded as requested) — optional; set to empty to disable HF queries

HF_API_KEY = ""

HF_MODEL = "gpt2"

HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

# Directories & files (auto-created)

LOG_DIR = "/sdcard/vega_logs"

os.makedirs(LOG_DIR, exist_ok=True)

FEEDBACK_FILE = os.path.join(LOG_DIR, "feedback.json")

USAGE_FILE = os.path.join(LOG_DIR, "usage.json")

SUGGESTED_FIXES = os.path.join(LOG_DIR, "suggested_fixes.json")

APP_MAP_FILE = os.path.join(LOG_DIR, "app_mapping.json")

MEMORY_FILE = os.path.join(LOG_DIR, "vega_memory.json")

AUDIT_LOG = os.path.join(LOG_DIR, "audit.log")

APPROVED_CMDS_FILE = os.path.join(LOG_DIR, "approved_commands.json")

WHITELIST_FILE = os.path.join(LOG_DIR, "whitelist.json")

SCREENSHOT_DIR = "/sdcard/vega_screenshots"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Behavior

LISTEN_SECONDS = 7

RETRY_ON_FAIL = 2

# Quick dangerous keywords block (first-pass)

DANGEROUS_KEYWORDS = [

"exploit","ddos","reverse shell","rootkit","attack","payload","crack","hydra",

"sqlmap","metasploit","nmap","subfinder","ffuf","port scan","scan subnet"

]

DEFAULT_APP_MAP = {

"whatsapp": "com.whatsapp",

"youtube": "com.google.android.youtube",

"camera": "com.android.camera"

}

# ---------------- Utilities ----------------

def load_json(path, default):

    try:

        if os.path.exists(path):

            with open(path, "r") as f:

                return json.load(f)

    except Exception:

        pass

    return default

def save_json(path, data):

    with open(path, "w") as f:

        json.dump(data, f, indent=2)

# create small files if missing

if not os.path.exists(FEEDBACK_FILE): save_json(FEEDBACK_FILE, [])

if not os.path.exists(USAGE_FILE): save_json(USAGE_FILE, [])

if not os.path.exists(SUGGESTED_FIXES): save_json(SUGGESTED_FIXES, [])

if not os.path.exists(APP_MAP_FILE): save_json(APP_MAP_FILE, DEFAULT_APP_MAP.copy())

if not os.path.exists(MEMORY_FILE): save_json(MEMORY_FILE, {"conversations":[]})

# default approved commands + whitelist (safe defaults; edit before use)

if not os.path.exists(APPROVED_CMDS_FILE):

    save_json(APPROVED_CMDS_FILE, {

        "ping": ["ping","-c","4","{target}"],

        "http_head": ["curl","-I","{target}"],

        "port_scan": ["nmap","-sT","-p","1-1024","{target}"]

    })

if not os.path.exists(WHITELIST_FILE):

    save_json(WHITELIST_FILE, {

        "198.51.100.23": {"owner":"security@acme.example","token":"invite-ACME-2025-08","notes":"ACME invited pentest 2025-08-09 scope: 198.51.100.23 only"},

        "lab.local": {"owner":"me","token":"local-lab","notes":"local lab only"}

    })

# ---------------- logging & audit ----------------

def audit_log(entry: dict):

    rec = {"ts": time.time(), "human_time": time.ctime(), **entry}

    with open(AUDIT_LOG, "a") as f:

        f.write(json.dumps(rec) + "\n")

def log_feedback(cmd,status,details=""):

    arr = load_json(FEEDBACK_FILE, [])

    arr.append({"time":time.time(),"human_time":time.ctime(),"command":cmd,"status":status,"details":details})

    save_json(FEEDBACK_FILE,arr)

def log_usage(cmd):

    arr = load_json(USAGE_FILE, [])

    arr.append({"time":time.time(),"command":cmd,"time_ts":time.time()})

    save_json(USAGE_FILE,arr)

def save_memory(user, assistant):

    mem = load_json(MEMORY_FILE, {"conversations":[]})

    mem["conversations"].append({"time":time.time(),"human_time":time.ctime(),"user":user,"assistant":assistant})

    mem["conversations"] = mem["conversations"][-500:]

    save_json(MEMORY_FILE, mem)

# ---------------- TTS helper ----------------

def speak_hindi(text):

    try:

        subprocess.run(["termux-tts-speak","-l","hi", text], check=False)

    except Exception:

        pass

    print(f"{ASSISTANT_NAME}: {text}")

# ---------------- safe subprocess wrapper ----------------

def safe_run(cmd_list, label=None, retries=RETRY_ON_FAIL, timeout=300):

    attempt=0

    while attempt<=retries:

        try:

            proc = subprocess.run(cmd_list, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)

            log_feedback(label or " ".join(cmd_list),"success",f"attempt {attempt+1}")

            return True, proc.stdout

        except subprocess.CalledProcessError as e:

            attempt+=1

            if attempt>retries:

                log_feedback(label or " ".join(cmd_list),"fail",str(e))

                return False, (e.stderr if hasattr(e,"stderr") else str(e))

            time.sleep(0.6)

        except Exception as e:

            return False, str(e)

    return False, "failed"

# ---------------- Termux / Device actions ----------------

def take_screenshot():

    filepath = os.path.join(SCREENSHOT_DIR, f"screenshot_{int(time.time())}.png")

    ok, out = safe_run(["termux-screenshot", filepath], "termux_screenshot")

    if ok:

        speak_hindi("स्क्रीनशॉट ले लिया गया")

    else:

        speak_hindi("स्क्रीनशॉट लेने में समस्या आई — मैन्युअल ले लो")

def camera_photo():

    photo_path = f"/sdcard/camera_{int(time.time())}.jpg"

    ok, out = safe_run(["termux-camera-photo", photo_path], "camera_photo")

    if ok:

        speak_hindi("फोटो ले ली गई")

    else:

        speak_hindi("कैमरा खोलने में समस्या आई")

def set_volume(level):

    ok, out = safe_run(["termux-volume", "music", str(level)], f"volume_{level}")

    if ok:

        if level == 0:

            speak_hindi("वॉल्यूम म्यूट कर दिया गया")

        elif level >= 12:

            speak_hindi("वॉल्यूम पूरा बढ़ा दिया गया")

        else:

            speak_hindi("वॉल्यूम सेट कर दिया गया")

    else:

        speak_hindi("वॉल्यूम बदलने में समस्या आई")

def lock_device():

    ok, out = safe_run(["termux-lock"], "lock_device")

    if ok:

        speak_hindi("फोन लॉक हो गया")

    else:

        speak_hindi("लॉक करने में समस्या आई")

def unlock_device():

    ok, out = safe_run(["termux-wake-unlock"], "unlock_device")

    if ok:

        speak_hindi("फोन अनलॉक हो गया")

    else:

        speak_hindi("अनलॉक करने में समस्या आई")

def open_app(app_name_raw):

    app_map = load_json(APP_MAP_FILE, DEFAULT_APP_MAP.copy())

    app_key = app_name_raw.strip().lower()

    if app_key in app_map:

        pkg = app_map[app_key]

        if safe_run(["am", "start", "-n", f"{pkg}/.MainActivity"], f"open_app_{app_key}")[0]:

            speak_hindi(f"{app_name_raw} खोल दिया")

            return True

    log_feedback(f"open_app:{app_key}", "fail", "mapping_missing_or_open_failed")

    suggested = load_json(SUGGESTED_FIXES, [])

    suggested.append({"time": time.time(), "command": f"open_app:{app_key}", "suggestion": "check package name or pronunciation"})

    save_json(SUGGESTED_FIXES, suggested)

    speak_hindi(f"{app_name_raw} नहीं खुल पाया — मैंने suggestion रखा है, टर्मिनल में CONFIRM करके placeholder जोड़ो")

    return False

# ---------------- HuggingFace helper ----------------

def hf_query(prompt, max_tokens=200):

    if not HF_API_KEY:

        return None, "no_token"

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": 0.1}}

    try:

        resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)

    except Exception as e:

        return None, f"request_failed:{e}"

    if resp.status_code == 200:

        try:

            out = resp.json()

            if isinstance(out, list) and len(out) and "generated_text" in out[0]:

                return out[0]["generated_text"].strip(), None

            if isinstance(out, dict) and "generated_text" in out:

                return out["generated_text"].strip(), None

            if isinstance(out, str):

                return out.strip(), None

            return str(out)[:1000], None

        except Exception as e:

            return None, f"parse_error:{e}"

    else:

        return None, f"HF error {resp.status_code}: {resp.text}"

# ---------------- Normalizer & safety ----------------

def contains_dangerous_intent(text):

    t = text.lower()

    for kw in DANGEROUS_KEYWORDS:

        if kw in t:

            return True, kw

    return False, None

def normalize_and_intent(text):

    dangerous, kw = contains_dangerous_intent(text)

    if dangerous:

        return "DANGEROUS", kw

    t = text.lower()

    # local rules

    if any(x in t for x in ["screenshot","स्क्रीनशॉट","screen shot"]):

        return "SCREENSHOT", None

    if any(x in t for x in ["lock","लॉक"]):

        return "LOCK", None

    if any(x in t for x in ["unlock","अनलॉक"]):

        return "UNLOCK", None

    if any(x in t for x in ["camera","कैमरा","photo","फोटो"]):

        return "CAMERA", None

    if any(x in t for x in ["volume","वॉल्यूम","आवाज़","आवाज"]):

        if any(x in t for x in ["increase","बढ़ा","फुल","ऊपर","up"]):

            return "VOLUME_UP", None

        if any(x in t for x in ["decrease","घटा","कम","down"]):

            return "VOLUME_DOWN", None

        if "mute" in t or "म्यूट" in t:

            return "VOLUME_MUTE", None

    if any(x in t for x in ["time","समय","टाइम"]):

        return "TIME", None

    if "battery" in t or "बैटरी" in t:

        return "BATTERY", None

    if "खोलो" in t or "open" in t:

        app_name = text.replace("खोलो","").replace("open","").strip()

        return "OPEN_APP", app_name

    # trading intents

    if "bitcoin" in t or "btc" in t or "buy bitcoin" in t:

        return "TRADE_ADVICE", "bitcoin"

    # authorized scan phrasing

    if any(x in t for x in ["scan","port scan","run scan","run port"]):

        m = re.search(r"((?:\d{1,3}\.){3}\d{1,3})|([a-z0-9\.-]+\.[a-z]{2,})", t)

        target = m.group(0) if m else None

        return "AUTHORIZED_SCAN", target

    # fallback: ask HF for normalization (safe prompt)

    hf_prompt = (

        "You are a safe normalizer. Convert this user's voice phrase into a short intent phrase "

        "for an Android assistant. Do NOT include any instructions to install hacking tools, perform network scans, or illegal actions.\n"

        f"User: {text}\nNormalizer:"

    )

    hf_out, err = hf_query(hf_prompt, max_tokens=60)

    if hf_out and not err:

        low = hf_out.lower()

        if any(x in low for x in ["screenshot","screen"]):

            return "SCREENSHOT", None

        if "lock" in low:

            return "LOCK", None

        if "unlock" in low:

            return "UNLOCK", None

        if "camera" in low or "photo" in low:

            return "CAMERA", None

        if low.startswith("open "):

            return "OPEN_APP", hf_out[5:].strip()

        if "time" in low or "समय" in low:

            return "TIME", None

        if "battery" in low or "बैटरी" in low:

            return "BATTERY", None

        if any(x in low for x in ["volume","वॉल्यूम","आवाज","आवाज़"]):

            if any(x in low for x in ["increase","up","बढ़ा","फुल"]):

                return "VOLUME_UP", None

            if any(x in low for x in ["decrease","down","कम","घटा"]):

                return "VOLUME_DOWN", None

    return "UNKNOWN", text

# ---------------- Voice listening ----------------

try:

    import speech_recognition as sr

except Exception:

    print("[vega] Missing dependency: SpeechRecognition. Install with: pip install SpeechRecognition")

    raise

def listen_google_stt(timeout=LISTEN_SECONDS, phrase_limit=LISTEN_SECONDS):

    r = sr.Recognizer()

    with sr.Microphone() as source:

        r.adjust_for_ambient_noise(source, duration=0.8)

        print("सुन रहा हूँ... (Google STT)")

        audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

        try:

            text = r.recognize_google(audio, language='hi-IN')

            return text

        except sr.UnknownValueError:

            try:

                text = r.recognize_google(audio, language='en-US')

                return text

            except Exception:

                return ""

        except Exception:

            return ""

# Optional: Vosk offline STT fallback (if user installed vosk & model)

def listen_vosk_offline():

    try:

        from vosk import Model, KaldiRecognizer

        import pyaudio

    except Exception:

        return ""

    model_path = "vosk-model-small-hi-0.22"  # Updated path as per download

    if not os.path.exists(model_path):

        return ""

    wf_rate = 16000

    model = Model(model_path)

    rec = KaldiRecognizer(model, wf_rate)

    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16, channels=1, rate=wf_rate, input=True, frames_per_buffer=8000)

    stream.start_stream()

    print("सुन रहा हूँ... (Vosk offline)")

    while True:

        data = stream.read(4000, exception_on_overflow=False)

        if rec.AcceptWaveform(data):

            res = json.loads(rec.Result())

            return res.get("text", "")

    return ""

# ---------------- Main voice loop ----------------

def voice_loop():

    while True:

        try:

            text = listen_google_stt()

            if not text:

                # try offline fallback

                text = listen_vosk_offline()

            if not text:

                continue

            print(f"तुम बोले: {text}")

            log_usage(text)

            intent, meta = normalize_and_intent(text)

            if intent == "DANGEROUS":

                speak_hindi("माफ़ कीजिए — मैं यह काम करने में मदद नहीं कर सकता।")

                log_feedback(text, "blocked", f"dangerous:{meta}")

                save_memory(text, "blocked_dangerous")

                continue

            # handle local intents

            if intent == "SCREENSHOT":

                take_screenshot(); save_memory(text, "screenshot")

                continue

            if intent == "LOCK":

                lock_device(); save_memory(text, "lock")

                continue

            if intent == "UNLOCK":

                unlock_device(); save_memory(text, "unlock")

                continue

            if intent == "CAMERA":

                camera_photo(); save_memory(text, "camera")

                continue

            if intent == "VOLUME_UP":

                set_volume(15); save_memory(text, "volume_up")

                continue

            if intent == "VOLUME_DOWN":

                set_volume(3); save_memory(text, "volume_down")

                continue

            if intent == "VOLUME_MUTE":

                set_volume(0); save_memory(text, "volume_mute")

                continue

            if intent == "TIME":

                tstr = time.strftime("अभी समय है %H:%M:%S")

                speak_hindi(tstr); save_memory(text, "time")

                continue

            if intent == "BATTERY":

                try:

                    out = subprocess.check_output(["dumpsys", "battery"], text=True)

                    m = re.search(r"level: (\d+)", out)

                    level = m.group(1) if m else "unknown"

                    speak_hindi(f"बैटरी {level}% है")

                except Exception:

                    speak_hindi("बैटरी लेवल नहीं मिला")

                save_memory(text, "battery")

                continue

            if intent == "OPEN_APP":

                opened = open_app(meta)

                save_memory(text, f"open_app:{meta}:{opened}")

                continue

            if intent == "TRADE_ADVICE":

                if meta == "bitcoin":

                    sugg = trading_suggestion_for_btc()

                    speak_hindi(sugg)

                    save_memory(text, sugg)

                    continue

            # Authorized scan flow

            if intent == "AUTHORIZED_SCAN":

                tgt = meta

                if not tgt:

                    speak_hindi("कृपया लक्ष्य बताइए — IP या domain.")

                    continue

                if not is_valid_hostname_or_ip(tgt):

                    speak_hindi("लक्ष्य invalid है।")

                    continue

                wl = load_json(WHITELIST_FILE, {})

                if tgt not in wl:

                    speak_hindi("यह लक्ष्य whitelist में नहीं है — मालिक से invitation token लें।")

                    audit_log({"action":"scan_blocked","target":tgt,"reason":"not_whitelisted"})

                    continue

                speak_hindi("Owner invite token terminal में डालिए।")

                token = input("Invite token: ").strip()

                if not verify_invite_token(tgt, token):

                    speak_hindi("Token invalid. Aborting.")

                    audit_log({"action":"token_invalid","target":tgt,"token_try": token})

                    continue

                ok = require_typed_confirmation()

                if not ok:

                    speak_hindi("Confirmation not received. Aborting.")

                    continue

                ok, out = run_approved_action("port_scan", target=tgt)

                if ok:

                    speak_hindi("Scan complete. Result saved to logs. Summary:")

                    speak_hindi(out[:300] if out else "No output")

                else:

                    speak_hindi("Scan failed: " + str(out)[:200])

                continue

            # If unknown -> ask HF for help (understanding / friendly reply)

            speak_hindi("सोच रहा हूँ...") # quick feedback

            hf_resp, err = hf_query(text, max_tokens=180)

            if hf_resp:

                print("HF:", hf_resp)

                speak_hindi(hf_resp if len(hf_resp) < 300 else hf_resp[:300] + "...")

                save_memory(text, hf_resp)

                log_feedback(text, "success", "hf_reply")

            else:

                print("[vega] HF error:", err)

                speak_hindi("समझ नहीं आया — क्या सरल शब्दों में बोलोगे?")

                log_feedback(text, "fail", err if err else "hf_fail")

                save_memory(text, "hf_fail")

        except KeyboardInterrupt:

            speak_hindi("सर्विस बंद कर रहा हूँ — बाय")

            save_json(os.path.join(LOG_DIR, "shutdown.json"), {"time": time.time()})

            os._exit(0)

        except Exception as e:

            print("[vega] voice loop exception:", e)

            log_feedback("internal_exception", "fail", str(e))

            time.sleep(1)

# ---------------- Terminal monitor ----------------

def terminal_monitor():

    while True:

        try:

            cmd = input().strip()

            if not cmd:

                continue

            C = cmd.upper()

            if C == "CONFIRM":

                suggested = load_json(SUGGESTED_FIXES, [])

                if not suggested:

                    print("कोई suggested fixes नहीं है।")

                    continue

                first = suggested.pop(0)

                save_json(SUGGESTED_FIXES, suggested)

                command = first.get("command", "")

                if command.startswith("open_app:"):

                    app_name = command.split(":", 1)[1]

                    app_map = load_json(APP_MAP_FILE, DEFAULT_APP_MAP.copy())

                    app_map[app_name] = "com.example.placeholder"

                    save_json(APP_MAP_FILE, app_map)

                    print(f"Placeholder mapping added for '{app_name}'. Edit {APP_MAP_FILE} to set real package.")

                    speak_hindi(f"{app_name} के लिए placeholder mapping जोड़ दिया — फ़ाइल एडिट करके सही package डाल देना")

                else:

                    print("Applied safe non-destructive suggestion (logged).")

            elif C == "ANALYZE":

                analyze()

                print("Analyze complete.")

            elif C == "SHOWLOGS":

                fb = load_json(FEEDBACK_FILE, [])

                print("Recent feedback (last 10):")

                for e in fb[-10:]:

                    print(e)

            elif C in ("EXIT","QUIT"):

                speak_hindi("सर्विस बंद कर रहा हूँ — बाय")

                save_json(os.path.join(LOG_DIR, "shutdown.json"), {"time": time.time()})

                os._exit(0)

            else:

                print("Commands: CONFIRM, ANALYZE, SHOWLOGS, EXIT")

        except Exception as e:

            print("[vega] terminal monitor error:", e)

        time.sleep(0.5)

# ---------------- Analyzer (auto-suggest repairs) ----------------

def analyze():

    data = load_json(FEEDBACK_FILE, [])

    if not data:

        print("No feedback yet.")

        return

    fails = [d for d in data if d["status"] == "fail"]

    if not fails:

        print("No failures logged.")

        return

    counts = Counter([f["command"] for f in fails])

    most_common, cnt = counts.most_common(1)[0]

    if cnt >= 3:

        speak_hindi(f"ध्यान दें: '{most_common}' बार-बार फेल हो रहा है — टर्मिनल में CONFIRM करके placeholder जोड़ो")

        suggested = load_json(SUGGESTED_FIXES, [])

        suggested.append({"time": time.time(), "command": most_common, "hint": "possible mapping/permission issue"})

        save_json(SUGGESTED_FIXES, suggested)

    else:

        print("No recurring failures found.")

# ---------------- Auxiliary functions ----------------

def is_valid_hostname_or_ip(s):

    return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", s) or re.match(r"^[a-z0-9\.-]{1,253}$", s, re.IGNORECASE))

def verify_invite_token(target, token):

    wl = load_json(WHITELIST_FILE, {})

    if target in wl and "token" in wl[target]:

        return wl[target]["token"] == token

    return False

def require_typed_confirmation(timeout_seconds=60):

    print("Dangerous action requested. To proceed TYPE: CONFIRM: YES (and press Enter)")

    speak_hindi("ध्यान दें: खतरनाक कार्रवाई के लिए टाइप करके पुष्टि करिए। टर्मिनल में CONFIRM: YES टाइप कीजिये।")

    start = time.time()

    try:

        while time.time() - start < timeout_seconds:

            user = input().strip()

            return user == "CONFIRM: YES"

    except Exception:

        pass

    return False

def run_approved_action(action_name, target=None, extra_args=None):

    approved = load_json(APPROVED_CMDS_FILE, {})

    if action_name not in approved:

        return False, f"Action '{action_name}' not found"

    base_cmd = approved[action_name].copy()

    final_cmd = []

    for part in base_cmd:

        if "{target}" in part:

            if not target:

                return False, "No target provided"

            if not is_valid_hostname_or_ip(target):

                return False, "Invalid target format"

            final_cmd.append(part.replace("{target}", target))

        else:

            final_cmd.append(part)

    if extra_args:

        final_cmd += extra_args

    audit_log({"phase":"pre-exec","action":action_name,"cmd":final_cmd,"target":target})

    ok,out = safe_run(final_cmd, label=f"approved:{action_name}")

    audit_log({"phase":"post-exec","action":action_name,"cmd":final_cmd,"target":target,"success":ok,"stdout_snippet": (out or "")[:1000]})

    return ok, out

# ---------------- Trading helper ----------------

def get_coin_price(coin_id="bitcoin", vs_currency="usd"):

    try:

        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={vs_currency}&include_24hr_change=true", timeout=10)

        j = r.json()

        return j.get(coin_id, {})

    except Exception:

        return {}

def trading_suggestion_for_btc():

    data = get_coin_price("bitcoin","usd")

    if not data:

        return "Market data unavailable right now."

    price = data.get("usd")

    change24 = data.get("usd_24h_change",0)

    trend = "up" if change24>0 else "down"

    sl_pct = 0.01 if trend=="up" else 0.02

    entry = price

    sl = round(entry*(1 - sl_pct),2)

    tp = round(entry*(1 + 0.03),2)

    return f"BTC price ${entry:.2f}, 24h change {change24:.2f}%. Suggested entry ${entry:.2f}, stop-loss ${sl:.2f}, take-profit ${tp:.2f} (trend {trend})."

# ---------------- Main ----------------

if __name__ == "__main__":

    if HF_API_KEY and HF_API_KEY.startswith("hf_"):

        print("\033[96m[vega]\033[0m HuggingFace integration enabled.")

    else:

        print("\033[93m[vega]\033[0m HuggingFace integration disabled (no token or invalid).")

    speak_hindi("वेगा सर्विस शुरू हो रही है")

    analyze() # quick analyze at start

    # start threads

    t_voice = threading.Thread(target=voice_loop, daemon=True)

    t_term = threading.Thread(target=terminal_monitor, daemon=True)

    t_voice.start()

    t_term.start()

    # main keepalive

    try:

        while True:

            time.sleep(10)

            # keep awake (best-effort)

            try:

                subprocess.run(["termux-wake-lock"], check=False)

            except:

                pass

    except KeyboardInterrupt:

        speak_hindi("सर्विस बंद कर रहा हूँ — बाय")

        save_json(os.path.join(LOG_DIR, "shutdown.json"), {"time": time.time()})

        os._exit(0)
