"""
THE RIPPLE EFFECT (Echoes of Choice)
A psychological life simulator powered by the Gemini API  -  Streamlit edition.
Languages: English / Bengali (বাংলা)

Created by NilanjanC
"""

import json
import os
import random
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
from google import genai
from google.genai import types

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
OWNER = "NilanjanC"
GAME_TITLE = "THE RIPPLE EFFECT"
SUBTITLE = "Echoes of Choice"


def _configured_model():
    try:
        m = st.secrets.get("GEMINI_MODEL")
    except Exception:
        m = None
    return m or os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash-lite"


# Tried in order; a model that returns 404 is skipped automatically.
MODEL_CANDIDATES = list(dict.fromkeys(
    [_configured_model(), "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]))
# Game length. A full game needs roughly 2 x (days x decisions) + 2 Gemini requests.
# 2 days x 4 decisions = about 18 requests (fits small free-tier limits).
# With billing enabled you can raise these, e.g. DAYS = 3 and SCENES_PER_DAY = 5.
DAYS = 2
SCENES_PER_DAY = 4
SHOW_DIAGNOSTICS = True    # shows model name and response time in the sidebar; set False to hide

METERS = ["mental_energy", "empathy", "anxiety", "social_connection"]

st.set_page_config(page_title=f"{GAME_TITLE} - by {OWNER}", page_icon="🌊", layout="centered")

# --------------------------------------------------------------------------
# Interface text (English / Bengali)
# --------------------------------------------------------------------------
S = {
    "en": {
        "created_by": f"A game created by {OWNER}",
        "intro1": "You are an ordinary person living an ordinary few days. Every small choice you make, "
                  "from a missed bus to a coworker's request, sends a ripple through your mind and the "
                  "people around you. There are no right answers, only consequences.",
        "intro2": "Watch your four meters: **Mental Energy**, **Empathy**, **Anxiety Level** and "
                  "**Social Connection**. The story is written live by AI, and every new game gives you a "
                  "different character, setting and cast, so no two playthroughs are alike.",
        "speed_tip": "Tip: English replies are generated faster than Bengali.",
        "need_key": "Add your Gemini API key in the app Secrets (GEMINI_API_KEY) or in the sidebar to begin.",
        "begin": "Begin",
        "setting_scene": "Setting the scene...",
        "check_key": "Check your API key and model name, then try again.",
        "quota_msg": "The free Gemini limit for today has been used up on every available model. "
                     "It resets daily. Try again later, switch to another API key, or turn on billing "
                     "in Google AI Studio for much higher limits.",
        "mind_status": "Mind Status",
        "mental_energy": "Mental Energy",
        "empathy": "Empathy",
        "anxiety": "Anxiety Level",
        "social_connection": "Social Connection",
        "day_info": "Day {d} of {D}  |  Decision {i} of {I}  |  {t}",
        "what_do": "What do you do?",
        "do_else": "Do something else (type your own action)",
        "describe": "Describe what you do",
        "describe_warn": "Please describe your action first.",
        "decide": "Decide",
        "world_reacts": "The world reacts...",
        "ripple": "The Ripple",
        "insight": "Psychology insight",
        "continue": "Continue",
        "see_end": "See your ending",
        "next_scene_gen": "Loading the next scene...",
        "reflecting": "Reflecting on your journey...",
        "made_it": "You made it through all {D} days.",
        "your_ripple": "Your Ripple",
        "takeaway": "Takeaway",
        "thanks": f"Thank you for playing {GAME_TITLE}.",
        "play_again": "Play again",
        "footer": f"{GAME_TITLE} - a game created by **{OWNER}**",
        "burnout": "BURNOUT: you ran out of mental energy. Every decision now feels impossible.",
        "overwhelmed": "OVERWHELMED: the anxiety became too loud to think through. You need to stop and rest.",
        "isolated": "ISOLATED: the people around you have drifted away, and the silence is heavy.",
        "fallback_title": "The Quiet Observer",
        "fallback_reflection": "Your choices rippled outward in ways you may only notice later.",
        "fallback_takeaway": "Small decisions shape who we become.",
    },
    "bn": {
        "created_by": f"{OWNER}-এর তৈরি একটি গেম",
        "intro1": "আপনি একজন সাধারণ মানুষ, যার সামনে সাধারণ কয়েকটি দিন। বাস মিস করা থেকে সহকর্মীর অনুরোধ, "
                  "প্রতিটি ছোট সিদ্ধান্ত আপনার মনে এবং আপনার চারপাশের মানুষদের মধ্যে ঢেউ তোলে। "
                  "এখানে কোনো সঠিক উত্তর নেই, আছে শুধু পরিণতি।",
        "intro2": "চারটি মিটারের দিকে নজর রাখুন: **মানসিক শক্তি**, **সহানুভূতি**, **উদ্বেগ** এবং **সামাজিক বন্ধন**। "
                  "গল্পটি সরাসরি এআই লেখে, আর প্রতিটি নতুন খেলায় থাকে আলাদা চরিত্র, পরিবেশ ও মানুষজন, "
                  "তাই দুটি খেলা কখনো এক হয় না।",
        "speed_tip": "পরামর্শ: ইংরেজিতে উত্তর বাংলার চেয়ে দ্রুত তৈরি হয়।",
        "need_key": "শুরু করতে অ্যাপের Secrets-এ GEMINI_API_KEY যোগ করুন, অথবা সাইডবারে লিখুন।",
        "begin": "শুরু করুন",
        "setting_scene": "পরিবেশ তৈরি হচ্ছে...",
        "check_key": "API key ও মডেলের নাম দেখে আবার চেষ্টা করুন।",
        "quota_msg": "আজকের বিনামূল্যের Gemini সীমা সব মডেলেই শেষ হয়ে গেছে। এটি প্রতিদিন রিসেট হয়। "
                     "পরে আবার চেষ্টা করুন, অন্য API key ব্যবহার করুন, অথবা বেশি সীমার জন্য "
                     "Google AI Studio-তে বিলিং চালু করুন।",
        "mind_status": "মনের অবস্থা",
        "mental_energy": "মানসিক শক্তি",
        "empathy": "সহানুভূতি",
        "anxiety": "উদ্বেগ",
        "social_connection": "সামাজিক বন্ধন",
        "day_info": "দিন {d}/{D}  |  সিদ্ধান্ত {i}/{I}  |  {t}",
        "what_do": "আপনি কী করবেন?",
        "do_else": "অন্য কিছু করব (নিজে লিখুন)",
        "describe": "আপনি কী করবেন লিখুন",
        "describe_warn": "আগে আপনার কাজটি লিখুন।",
        "decide": "সিদ্ধান্ত নিন",
        "world_reacts": "চারপাশ প্রতিক্রিয়া দেখাচ্ছে...",
        "ripple": "ঢেউ",
        "insight": "মনোবিজ্ঞানের অন্তর্দৃষ্টি",
        "continue": "এগিয়ে চলুন",
        "see_end": "আপনার সমাপ্তি দেখুন",
        "next_scene_gen": "পরবর্তী দৃশ্য আনা হচ্ছে...",
        "reflecting": "আপনার যাত্রা নিয়ে ভাবা হচ্ছে...",
        "made_it": "আপনি সব {D} দিন পার করেছেন।",
        "your_ripple": "আপনার ঢেউ",
        "takeaway": "শিক্ষা",
        "thanks": f"{GAME_TITLE} খেলার জন্য ধন্যবাদ।",
        "play_again": "আবার খেলুন",
        "footer": f"{GAME_TITLE} - **{OWNER}**-এর তৈরি একটি গেম",
        "burnout": "বার্নআউট: আপনার মানসিক শক্তি শেষ। এখন প্রতিটি সিদ্ধান্তই অসম্ভব মনে হচ্ছে।",
        "overwhelmed": "অভিভূত: উদ্বেগ এত বেড়ে গেছে যে আর ভাবা যাচ্ছে না। একটু থামা আর বিশ্রাম দরকার।",
        "isolated": "একাকী: আপনার চারপাশের মানুষ ধীরে ধীরে দূরে সরে গেছে, আর নীরবতা ভারী হয়ে উঠেছে।",
        "fallback_title": "নীরব দর্শক",
        "fallback_reflection": "আপনার সিদ্ধান্তগুলো এমনভাবে ছড়িয়ে পড়েছে, যা হয়তো আপনি পরে বুঝবেন।",
        "fallback_takeaway": "ছোট ছোট সিদ্ধান্তই আমাদের গড়ে তোলে।",
    },
}


def lang():
    gl = st.session_state.get("game_lang")
    if gl:
        return gl
    return "bn" if st.session_state.get("lang_choice") == "বাংলা" else "en"


def t(key, **kw):
    text = S[lang()][key]
    return text.format(**kw) if kw else text


# --------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------
def system_prompt():
    if lang() == "bn":
        language_rule = (
            "LANGUAGE: Write ALL player-facing text (time_of_day, narrative, choices, ripple, insight, "
            "title, reflection, takeaway) in natural, simple, conversational Bengali (বাংলা) using Bengali "
            "script. Write character names in Bengali script too. Keep JSON keys and the choice_tag value "
            "in English exactly as specified."
        )
    else:
        language_rule = "LANGUAGE: Write everything in English only."
    return f"""You are the story engine of a text-based psychological life simulator called
"{GAME_TITLE}" (created by {OWNER}). The player plays an ordinary Indian person living an ordinary day.
{language_rule}

Rules:
- Scenes must be grounded, realistic everyday situations in an Indian context (local train, bus, metro,
  auto-rickshaw, Uber/Ola, tea stall, office, power cut, WhatsApp family groups, festivals, neighbours,
  rent, EMIs, rupees). No fantasy, no violence, no gore.
- Every small decision carries a hidden "psychological tax". Show how it ripples into the
  player's mind, mood and the way people around them behave next.
- Look at the player's recent decision pattern. If they repeatedly act selfishly, make
  surrounding characters colder, curt or strange. If they are repeatedly kind, let warmth return,
  but also show that constant self-sacrifice drains Mental Energy. Avoidance should slowly raise
  Anxiety. Make consequences feel earned, never preachy.
- The four meters run 0-100: mental_energy, empathy, anxiety, social_connection.
  (Higher anxiety is WORSE; for the other three, higher is better.)
- Offer exactly 3 distinct, believable, SHORT choices per scene, with no obviously "correct" one.
- Occasionally (about once per day) add a short, accurate "insight": a real psychology concept
  relevant to what just happened (decision fatigue, bystander effect, emotional contagion, cognitive
  dissonance, spotlight effect, rumination, reciprocity...). 1-2 plain sentences. Otherwise use "".
- Keep everything BRIEF: narration 2-3 sentences, ripple 2 sentences. Use second person.
- Reply with ONLY a single valid JSON object. No markdown fences, no commentary."""


SCENE_SCHEMA = """{
  "time_of_day": "short label, e.g. 'Morning, 7:40 AM'",
  "narrative": "2-3 sentences describing the current situation",
  "choices": ["choice 1", "choice 2", "choice 3"]
}"""

TURN_SCHEMA = """{
  "choice_tag": "one of: selfish, kind, avoidant, assertive, impulsive, balanced",
  "ripple": "2 sentences: the immediate psychological ripple of the player's decision",
  "deltas": {"mental_energy": int, "empathy": int, "anxiety": int, "social_connection": int},
  "insight": "1-2 sentence real psychology insight, or empty string"
}"""


def get_api_key():
    key = None
    try:
        key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        key = None
    key = key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        key = st.sidebar.text_input("Gemini API key", type="password",
                                    help="Used only in this session. Not stored.")
    return key


@st.cache_resource(show_spinner=False)
def get_client(api_key):
    return genai.Client(api_key=api_key)


@st.cache_resource(show_spinner=False)
def get_executor():
    return ThreadPoolExecutor(max_workers=4)


def extract_json(text):
    if not text:
        raise ValueError("Empty response")
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start:end + 1])


# Options tried for minimising "thinking" time (a big source of delay).
# The last entry, "bare", sends only the system prompt (no JSON mode, no extra settings) as a final fallback.
THINKING_OPTIONS = [{"thinking_budget": 0}, {"thinking_level": "minimal"}, {"thinking_level": "low"}, None, "bare"]


def make_configs():
    """Build the list of generation configs (most-preferred first). Must run in the main thread."""
    base = dict(system_instruction=system_prompt(), temperature=1.1, max_output_tokens=3000,
                response_mime_type="application/json")
    start = st.session_state.get("thinking_idx", 0)
    configs = []
    for opt in THINKING_OPTIONS[start:]:
        if opt == "bare":
            configs.append(types.GenerateContentConfig(system_instruction=system_prompt()))
            continue
        kw = dict(base)
        if opt:
            try:
                kw["thinking_config"] = types.ThinkingConfig(**opt)
            except Exception:
                pass  # this SDK version doesn't know the option: send without it
        configs.append(types.GenerateContentConfig(**kw))
    return configs


def _is_quota(msg):
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def _is_missing(msg):
    return "404" in msg or "NOT_FOUND" in msg


def short_reason(msg):
    if _is_missing(msg):
        return "404 model not available"
    if _is_quota(msg):
        return "429 daily/minute quota used up"
    return msg[:250]


def call_models(client, prompt, configs, models, retries=2):
    """Pure function (no Streamlit access) so it can also run in a background thread.
    Quota (429) and missing-model (404) errors are NOT retried: they move on to the next model."""
    skipped = []
    last = None
    for model in models:
        ci = 0
        attempt = 0
        failed_reason = None
        while attempt < retries and ci < len(configs):
            attempt += 1
            try:
                t0 = time.time()
                resp = client.models.generate_content(model=model, contents=prompt, config=configs[ci])
                data = extract_json(resp.text)
                return data, {"model": model, "seconds": round(time.time() - t0, 1),
                              "cfg_idx": ci, "attempt": attempt, "skipped": skipped}
            except Exception as err:
                last = err
                msg = str(err)
                failed_reason = short_reason(msg)
                if _is_missing(msg) or _is_quota(msg):
                    break
                bad_arg = "400" in msg or "INVALID_ARGUMENT" in msg
                if (bad_arg or "thinking" in msg.lower()) and ci < len(configs) - 1:
                    ci += 1
                    attempt -= 1
                    continue
                if attempt < retries:
                    time.sleep(0.8 * attempt)
        skipped.append(f"{model}: {failed_reason}")
    if skipped and all("429" in x for x in skipped):
        raise RuntimeError("QUOTA")
    raise RuntimeError(f"Gemini request failed. Tried: {'; '.join(skipped)}. Last error: {str(last)[:200]}")


def record_info(info):
    st.session_state.thinking_idx = st.session_state.get("thinking_idx", 0) + info["cfg_idx"]
    st.session_state.last_call = {
        "model": info["model"], "seconds": info["seconds"], "attempt": info["attempt"],
        "skipped": info.get("skipped", []),
        "thinking": THINKING_OPTIONS[min(st.session_state.thinking_idx, len(THINKING_OPTIONS) - 1)],
    }


def ask_gemini(prompt):
    client = get_client(st.session_state.api_key)
    try:
        data, info = call_models(client, prompt, make_configs(), MODEL_CANDIDATES)
    except RuntimeError as err:
        if str(err) == "QUOTA":
            raise RuntimeError(t("quota_msg")) from err
        raise
    record_info(info)
    return data


def start_prefetch(prompt):
    client = get_client(st.session_state.api_key)
    return get_executor().submit(call_models, client, prompt, make_configs(), MODEL_CANDIDATES)


# --------------------------------------------------------------------------
# Randomised life profile (makes every new game different)
# --------------------------------------------------------------------------
FIRST_NAMES = ["Arnab", "Riya", "Subhojit", "Ananya", "Debashis", "Moumita", "Rahul", "Priya", "Sourav",
               "Tanushree", "Imran", "Kavita", "Rohan", "Sneha", "Abhijit", "Swati", "Aditya", "Pooja",
               "Soumya", "Ishita", "Partha", "Rituparna", "Vikram", "Meera", "Sayan", "Debjani", "Karthik",
               "Nandini", "Anirban", "Farhana", "Rajesh", "Shreya", "Tuhin", "Lakshmi", "Biplab", "Aarav"]
JOBS = ["school teacher", "bank clerk", "IT support engineer", "call-centre executive", "hospital pharmacist",
        "junior accountant", "shop owner", "delivery rider", "government office clerk", "college lecturer",
        "freelance graphic designer", "nurse", "sales executive", "software tester", "tuition teacher",
        "medical representative", "railway staff member", "content writer"]
SETTINGS = ["Kolkata, with a crowded local train and bus commute", "Siliguri, a busy town at the foot of the hills",
            "Howrah, a packed industrial neighbourhood", "Pune, working near an IT park",
            "Delhi, with a long metro commute and heavy pollution", "Bengaluru, stuck in heavy traffic",
            "a small town in West Bengal where everyone knows everyone", "Chennai in monsoon season",
            "Mumbai, with an overcrowded local train", "Durgapur, a steel-town with shift workers",
            "Kolkata during the Durga Puja season", "a hot, humid city during a heatwave and power cuts"]
LIFE_SITUATIONS = ["living with parents in a joint family", "sharing a rented flat with two roommates",
                   "newly married and still adjusting to a new household", "caring for an elderly grandparent",
                   "recently moved to the city and knowing few people", "living alone and feeling slightly lonely",
                   "raising a young child with a partner", "paying an EMI and watching every rupee"]
QUIRKS = ["overthinks every WhatsApp message", "hates confrontation", "says yes too easily",
          "is always running slightly late", "keeps a perfect to-do list but rarely finishes it",
          "worries about what relatives and neighbours think", "is fiercely independent and hates asking for help",
          "scrolls the phone when stressed", "is generous but quietly resentful when unappreciated",
          "cannot say no to family"]
CAST_ROLES = ["a chatty neighbour (aunty)", "a demanding boss", "a close college friend", "a younger sibling",
              "mother", "father", "a quiet new colleague", "a roommate", "a cousin who always needs favours",
              "the tea-stall owner they see daily", "a spouse or partner", "a retired uncle from downstairs",
              "an auto-rickshaw driver they often ride with", "a gossipy colleague"]
THEMES = ["commute trouble (train, bus, auto, cab or traffic)", "a favour requested by someone",
          "money and small expenses", "a tense conversation or conflict", "social media or phone temptation",
          "a family call or the family WhatsApp group", "a chance to help a stranger",
          "workplace pressure or a deadline", "a friend's invitation", "a tiredness, health or sleep choice",
          "a chore that keeps getting postponed", "an unexpected compliment or criticism",
          "an awkward silence or misunderstanding", "food or routine decision", "a moment of loneliness or boredom",
          "a promise made earlier coming due", "an overheard conversation", "a surprise change of plans",
          "a power cut, rain or festival crowd", "relatives asking about marriage, salary or career"]


def new_profile():
    rng = random.Random()
    names = rng.sample(FIRST_NAMES, 4)
    roles = rng.sample(CAST_ROLES, 3)
    return {
        "player_name": names[0],
        "job": rng.choice(JOBS),
        "setting": rng.choice(SETTINGS),
        "life": rng.choice(LIFE_SITUATIONS),
        "quirk": rng.choice(QUIRKS),
        "cast": [f"{names[i + 1]} ({roles[i]})" for i in range(3)],
        "themes": rng.sample(THEMES, DAYS * SCENES_PER_DAY),
        "seed": uuid.uuid4().hex[:8],
    }


def profile_text():
    p = st.session_state.profile
    return (
        f"PLAYER CHARACTER (keep consistent all game): {p['player_name']}, a {p['job']}, living in "
        f"{p['setting']}, {p['life']}. Quirk: {p['quirk']}.\n"
        f"RECURRING SUPPORTING CHARACTERS (Indian names; keep these): {', '.join(p['cast'])}. "
        f"Other people can appear too, always with Indian names.\n"
        f"Unique game seed (invent fresh details; avoid a typical opening): {p['seed']}"
    )


def theme_for(day, idx):
    n = (day - 1) * SCENES_PER_DAY + (idx - 1)
    themes = st.session_state.profile["themes"]
    return themes[n % len(themes)]


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
def pattern_summary(last_n=6):
    hist = st.session_state.history[-last_n:]
    if not hist:
        return "No decisions yet."
    tags = {}
    for h in hist:
        tags[h["tag"]] = tags.get(h["tag"], 0) + 1
    tag_text = ", ".join(f"{k} x{v}" for k, v in sorted(tags.items(), key=lambda kv: -kv[1]))
    lines = [f'Day {h["day"]}: "{h["decision"]}" ({h["tag"]})' for h in hist]
    return f"Tag counts: {tag_text}\nRecent decisions:\n" + "\n".join(lines)


def meters_text():
    m = st.session_state.meters
    return ", ".join(f"{k}={m[k]}" for k in METERS)


def scene_prompt(day, idx, recent=""):
    morning = ("This is the morning of a new day; reflect how the previous day's choices carried over. "
               if (idx == 1 and day > 1) else "")
    return (f"It is Day {day}, scene {idx} of {SCENES_PER_DAY}. {morning}"
            f"{profile_text()}\n"
            f"Current meters: {meters_text()}\nPlayer decision pattern:\n{pattern_summary()}\n"
            f"{recent}\n"
            f"Write an ordinary everyday situation fitting that moment of the day. "
            f"Let the tone reflect the meters (high anxiety = tense, low energy = foggy, "
            f"low social connection = lonely). "
            f"Suggested theme for this scene: {theme_for(day, idx)}. "
            f"Reply with ONLY JSON in this schema:\n{SCENE_SCHEMA}")


def turn_prompt(scene, decision):
    return (
        f"{profile_text()}\n"
        f"Current meters: {meters_text()}\n"
        f"Player decision pattern:\n{pattern_summary()}\n\n"
        f"Current situation: {scene['narrative']}\n"
        f"The player decided: \"{decision}\"\n\n"
        f"Describe the psychological ripple of this decision and the meter changes.\n"
        f"Reply with ONLY JSON in this schema:\n{TURN_SCHEMA}"
    )


def ending_prompt():
    return (
        f"The game is over. {profile_text()}\n"
        f"Final meters: {meters_text()}\n"
        f"All decisions:\n{pattern_summary(last_n=len(st.session_state.history))}\n\n"
        "Write a warm, honest, non-judgmental reflection on who this player was over these days. "
        "Reply with ONLY JSON: "
        '{"title": "a short personality-style title for this run", '
        '"reflection": "3-5 sentences", '
        '"takeaway": "one gentle real-world takeaway sentence"}'
    )


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------
def reset_game():
    st.session_state.default_lang_idx = 1 if st.session_state.get("game_lang") == "bn" else 0
    st.session_state.game_lang = None
    rng = random.Random()
    st.session_state.profile = new_profile()
    st.session_state.meters = {
        "mental_energy": rng.randint(65, 90),
        "empathy": rng.randint(45, 75),
        "anxiety": rng.randint(20, 45),
        "social_connection": rng.randint(45, 75),
    }
    st.session_state.history = []
    st.session_state.day = 1
    st.session_state.scene_in_day = 1
    st.session_state.scene = None
    st.session_state.result = None
    st.session_state.applied = {}
    st.session_state.ending_note = None
    st.session_state.end_data = None
    st.session_state.prefetch = None
    st.session_state.phase = "title"


def init():
    if "phase" not in st.session_state:
        reset_game()


def apply_deltas(deltas):
    applied = {}
    for m in METERS:
        try:
            d = int(deltas.get(m, 0))
        except (TypeError, ValueError):
            d = 0
        d = max(-25, min(25, d))
        before = st.session_state.meters[m]
        st.session_state.meters[m] = max(0, min(100, before + d))
        applied[m] = st.session_state.meters[m] - before
    return applied


def crisis_ending():
    m = st.session_state.meters
    if m["mental_energy"] <= 0:
        return t("burnout")
    if m["anxiety"] >= 100:
        return t("overwhelmed")
    if m["social_connection"] <= 0:
        return t("isolated")
    return None


def valid_scene(sc):
    return isinstance(sc, dict) and sc.get("narrative") and len(sc.get("choices", [])) >= 3


# --------------------------------------------------------------------------
# UI pieces
# --------------------------------------------------------------------------
def footer():
    st.divider()
    st.caption(t("footer"))


def show_meters(applied=None):
    st.markdown(f"##### {t('mind_status')}")
    cols = st.columns(4)
    for col, m in zip(cols, METERS):
        val = st.session_state.meters[m]
        delta = None
        if applied and applied.get(m):
            delta = f"{applied[m]:+d}"
        with col:
            st.metric(t(m), val, delta=delta, delta_color="inverse" if m == "anxiety" else "normal")
            st.progress(val / 100)


def screen_title():
    st.radio("Language / ভাষা", ["English", "বাংলা"], horizontal=True, key="lang_choice",
             index=st.session_state.get("default_lang_idx", 0))
    st.markdown(f"<h1 style='text-align:center;margin-bottom:0'>{GAME_TITLE}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;font-size:1.2rem;margin-top:0'><i>{SUBTITLE}</i></p>",
                unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align:center'>{t('created_by')}</h4>", unsafe_allow_html=True)
    st.divider()
    st.write(t("intro1"))
    st.write(t("intro2"))
    st.caption(t("speed_tip"))

    if not st.session_state.api_key:
        st.info(t("need_key"))
        return
    if st.button(t("begin"), type="primary", use_container_width=True):
        st.session_state.game_lang = lang()
        with st.spinner(t("setting_scene")):
            try:
                st.session_state.scene = ask_gemini(scene_prompt(1, 1))
                st.session_state.phase = "scene"
                st.rerun()
            except RuntimeError as err:
                st.session_state.game_lang = None
                st.error(f"{err}\n\n{t('check_key')}")


def screen_scene():
    s = st.session_state
    scene = s.scene
    show_meters()
    st.divider()
    st.caption(t("day_info", d=s.day, D=DAYS, i=s.scene_in_day, I=SCENES_PER_DAY,
                 t=scene.get("time_of_day", "")))
    st.write(scene["narrative"])

    choices = scene["choices"][:3]
    options = choices + [t("do_else")]
    pick = st.radio(t("what_do"), options, index=None, key=f"pick_{s.day}_{s.scene_in_day}")
    custom = ""
    if pick == options[-1]:
        custom = st.text_input(t("describe"), max_chars=300, key=f"custom_{s.day}_{s.scene_in_day}")

    if st.button(t("decide"), type="primary", disabled=pick is None):
        decision = custom.strip() if pick == options[-1] else pick
        if not decision:
            st.warning(t("describe_warn"))
            return
        with st.spinner(t("world_reacts")):
            try:
                result = ask_gemini(turn_prompt(scene, decision))
            except RuntimeError as err:
                st.error(str(err))
                return
        tag = str(result.get("choice_tag", "balanced")).lower()
        s.history.append({"day": s.day, "scene": s.scene_in_day, "decision": decision, "tag": tag})
        s.applied = apply_deltas(result.get("deltas", {}))
        s.result = result
        s.ending_note = crisis_ending()

        # Start writing the next scene in the background while the player reads the ripple.
        s.prefetch = None
        last_of_game = s.day == DAYS and s.scene_in_day == SCENES_PER_DAY
        if not s.ending_note and not last_of_game:
            new_day = s.scene_in_day == SCENES_PER_DAY
            nd = s.day + 1 if new_day else s.day
            ni = 1 if new_day else s.scene_in_day + 1
            recent = (f'The player just decided: "{decision}". Ripple: {result.get("ripple", "")}')
            s.prefetch = {"future": start_prefetch(scene_prompt(nd, ni, recent)), "day": nd, "idx": ni}
        s.phase = "ripple"
        st.rerun()


def screen_ripple():
    s = st.session_state
    result = s.result
    st.markdown(f"#### {t('ripple')}")
    st.write(result.get("ripple", ""))
    insight = (result.get("insight") or "").strip()
    if insight:
        st.info(f"**{t('insight')}:** {insight}")
    st.divider()
    show_meters(s.applied)
    st.divider()

    last_of_game = s.day == DAYS and s.scene_in_day == SCENES_PER_DAY
    if s.ending_note or last_of_game:
        if st.button(t("see_end"), type="primary", use_container_width=True):
            s.phase = "end"
            st.rerun()
        return

    if st.button(t("continue"), type="primary", use_container_width=True):
        pf = s.prefetch
        new_day = s.scene_in_day == SCENES_PER_DAY
        new_day_no = s.day + 1 if new_day else s.day
        new_idx = 1 if new_day else s.scene_in_day + 1

        nxt = None
        with st.spinner(t("next_scene_gen")):
            if pf:
                try:
                    data, info = pf["future"].result(timeout=120)
                    record_info(info)
                    nxt = data
                except Exception:
                    nxt = None
            if not valid_scene(nxt):
                try:
                    nxt = ask_gemini(scene_prompt(new_day_no, new_idx))
                except RuntimeError as err:
                    st.error(str(err))
                    return

        if new_day:  # a night's sleep: partial recovery
            s.meters["mental_energy"] = min(100, s.meters["mental_energy"] + 15)
            s.meters["anxiety"] = max(0, s.meters["anxiety"] - 5)
        s.scene = nxt
        s.day, s.scene_in_day = new_day_no, new_idx
        s.prefetch = None
        s.phase = "scene"
        st.rerun()


def screen_end():
    s = st.session_state
    if s.end_data is None:
        with st.spinner(t("reflecting")):
            try:
                s.end_data = ask_gemini(ending_prompt())
            except RuntimeError:
                s.end_data = {
                    "title": t("fallback_title"),
                    "reflection": t("fallback_reflection"),
                    "takeaway": t("fallback_takeaway"),
                }
    end = s.end_data
    if s.ending_note:
        st.error(s.ending_note)
    else:
        st.success(t("made_it", D=DAYS))
    st.markdown(f"## {t('your_ripple')}: {end.get('title', '')}")
    st.write(end.get("reflection", ""))
    st.markdown(f"**{t('takeaway')}:** {end.get('takeaway', '')}")
    st.divider()
    show_meters()
    st.markdown(f"<p style='text-align:center'>{t('thanks')}<br><b>{t('created_by')}.</b></p>",
                unsafe_allow_html=True)
    if st.button(t("play_again"), type="primary", use_container_width=True):
        reset_game()
        st.rerun()


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
init()
st.session_state.api_key = get_api_key()

phase = st.session_state.phase
if phase == "title":
    screen_title()
elif phase == "scene":
    screen_scene()
elif phase == "ripple":
    screen_ripple()
else:
    screen_end()
footer()

if SHOW_DIAGNOSTICS:
    lc = st.session_state.get("last_call")
    with st.sidebar:
        st.markdown("**Diagnostics**")
        st.caption("Models tried in order: " + ", ".join(MODEL_CANDIDATES))
        if lc:
            st.caption(f"Last call: model `{lc['model']}`, {lc['seconds']} s, "
                       f"thinking setting {lc['thinking']}, attempt {lc['attempt']}")
            if lc.get("skipped"):
                st.caption("Skipped before that: " + "; ".join(lc["skipped"]))
        else:
            st.caption("No call made yet.")
