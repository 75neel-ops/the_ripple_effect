"""
THE RIPPLE EFFECT (Echoes of Choice)
A psychological life simulator powered by the Gemini API  -  Streamlit edition.

Created by NilanjanC
"""

import json
import os
import random
import re
import time
import uuid

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
MODEL_CANDIDATES = [_configured_model(), "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]
DAYS = 3
SCENES_PER_DAY = 5
USE_WEB_GROUNDING = False  # True adds live web lookups for psychology insights but makes each turn much slower

METERS = ["mental_energy", "empathy", "anxiety", "social_connection"]
METER_LABELS = {
    "mental_energy": "Mental Energy",
    "empathy": "Empathy",
    "anxiety": "Anxiety Level",
    "social_connection": "Social Connection",
}

st.set_page_config(page_title=f"{GAME_TITLE} - by {OWNER}", page_icon="🌊", layout="centered")

# --------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------
SYSTEM_PROMPT = f"""You are the story engine of a text-based psychological life simulator called
"{GAME_TITLE}" (created by {OWNER}). The player plays an ordinary person living an ordinary day.
Everything is in English only.

Rules:
- Scenes must be grounded, realistic everyday situations (commute, work, family, friends, money,
  chores, small talk, social media, health, errands). No fantasy, no violence, no gore.
- Every small decision carries a hidden "psychological tax". Show how it ripples into the
  player's mind, mood and the way people around them behave next.
- Look at the player's recent decision pattern. If they repeatedly act selfishly, make
  surrounding characters colder, curt or strange. If they are repeatedly kind, let warmth return,
  but also show that constant self-sacrifice drains Mental Energy. Avoidance should slowly raise
  Anxiety. Make consequences feel earned, never preachy.
- The four meters run 0-100: mental_energy, empathy, anxiety, social_connection.
  (Higher anxiety is WORSE; for the other three, higher is better.)
- Offer exactly 3 distinct, believable choices per scene, with no obviously "correct" one.
- Occasionally (about once per day) add a short, accurate "insight": a real psychology concept
  or theory relevant to what just happened (for example decision fatigue, the bystander effect,
  emotional contagion, cognitive dissonance, the spotlight effect, rumination, reciprocity).
  Explain it in 1-2 plain sentences. Otherwise leave insight as an empty string.
- Keep narration vivid but concise (3-5 sentences). Use second person ("you").
- Always reply with ONLY a single valid JSON object. No markdown fences, no commentary."""

SCENE_SCHEMA = """{
  "time_of_day": "short label, e.g. 'Morning, 7:40 AM'",
  "narrative": "3-5 sentences describing the current situation",
  "choices": ["choice 1", "choice 2", "choice 3"]
}"""

TURN_SCHEMA = """{
  "choice_tag": "one of: selfish, kind, avoidant, assertive, impulsive, balanced",
  "ripple": "2-4 sentences: the immediate psychological ripple of the player's decision",
  "deltas": {"mental_energy": int, "empathy": int, "anxiety": int, "social_connection": int},
  "insight": "1-2 sentence real psychology insight, or empty string",
  "next_scene": %s
}""" % SCENE_SCHEMA


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


def extract_json(text):
    if not text:
        raise ValueError("Empty response")
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start:end + 1])


def ask_gemini(prompt, grounded=False, retries=3):
    client = genai.Client(api_key=st.session_state.api_key)
    tools = [types.Tool(google_search=types.GoogleSearch())] if (grounded and USE_WEB_GROUNDING) else None
    config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=1.2, tools=tools)
    last_err = None
    seen = []
    for model in MODEL_CANDIDATES:
        if model in seen:
            continue
        seen.append(model)
        for attempt in range(1, retries + 1):
            try:
                resp = client.models.generate_content(model=model, contents=prompt, config=config)
                return extract_json(resp.text)
            except Exception as err:
                last_err = err
                if "404" in str(err) or "NOT_FOUND" in str(err):
                    break  # model unavailable: try the next candidate
                if attempt < retries:
                    time.sleep(1.5 * attempt)
    raise RuntimeError(f"Gemini request failed: {last_err}")


# --------------------------------------------------------------------------
# Randomised life profile (makes every new game different)
# --------------------------------------------------------------------------
FIRST_NAMES = ["Maya", "Arjun", "Elena", "Tom", "Priya", "Daniel", "Sofia", "Kenji", "Amara", "Luca",
               "Hana", "Omar", "Ruth", "Diego", "Mei", "Samir", "Nora", "Felix", "Zara", "Jonas"]
JOBS = ["junior graphic designer", "primary school teacher", "hospital pharmacist", "call-centre agent",
        "freelance writer", "warehouse supervisor", "bank clerk", "software tester", "nurse",
        "cafe barista and part-time student", "delivery driver", "accountant", "librarian",
        "restaurant line cook", "government office clerk", "retail store manager"]
SETTINGS = ["a crowded big city with a long commute", "a quiet mid-sized town", "a coastal town in monsoon season",
            "a busy suburb full of apartment blocks", "a university city", "a small town where everyone knows everyone",
            "a rainy northern city in late autumn", "a hot, humid city in a heatwave"]
LIFE_SITUATIONS = ["living with their parents and saving money", "sharing a flat with two roommates",
                   "newly married and still adjusting", "caring for an elderly relative",
                   "recently moved and knowing few people", "living alone and slightly lonely",
                   "raising a young child with a partner", "paying off a loan and watching every expense"]
QUIRKS = ["overthinks every message they send", "hates confrontation", "says yes too easily",
          "is always running slightly late", "keeps a spotless to-do list but rarely finishes it",
          "worries about what others think", "is fiercely independent and hates asking for help",
          "scrolls their phone when stressed", "is generous but quietly resentful when unappreciated"]
CAST_ROLES = ["a chatty coworker", "a demanding manager", "a close old friend", "a neighbour",
              "a younger sibling", "a parent", "a quiet new colleague", "a roommate", "a childhood friend",
              "a shopkeeper they see daily", "a partner", "a cousin who always needs favours"]
THEMES = ["commute or transport trouble", "a favour requested by someone", "money and small expenses",
          "a conflict or tense conversation", "social media or phone temptation", "a family call or message",
          "a chance to help a stranger", "workplace pressure or a deadline", "a friend's invitation",
          "a health or tiredness choice", "a chore that keeps getting postponed", "an unexpected compliment or criticism",
          "an awkward silence or misunderstanding", "food, sleep or routine decision", "a moment of loneliness or boredom",
          "a promise made earlier coming due", "an overheard conversation", "a surprise change of plans"]


def new_profile():
    rng = random.Random()
    cast = rng.sample(CAST_ROLES, 3)
    names = rng.sample(FIRST_NAMES, 4)
    return {
        "player_name": names[0],
        "job": rng.choice(JOBS),
        "setting": rng.choice(SETTINGS),
        "life": rng.choice(LIFE_SITUATIONS),
        "quirk": rng.choice(QUIRKS),
        "cast": [f"{names[i + 1]} ({cast[i]})" for i in range(3)],
        "themes": rng.sample(THEMES, DAYS * SCENES_PER_DAY),
        "seed": uuid.uuid4().hex[:8],
    }


def profile_text():
    p = st.session_state.profile
    return (
        f"PLAYER CHARACTER (keep consistent all game): {p['player_name']}, a {p['job']}, living in "
        f"{p['setting']}, {p['life']}. Quirk: {p['quirk']}.\n"
        f"RECURRING SUPPORTING CHARACTERS: {', '.join(p['cast'])}. Other people can appear too.\n"
        f"Unique game seed (invent fresh details; never reuse a typical opening): {p['seed']}"
    )


def theme_for(day, idx):
    n = (day - 1) * SCENES_PER_DAY + (idx - 1)
    themes = st.session_state.profile["themes"]
    return themes[n % len(themes)]


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
def pattern_summary(last_n=8):
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


def scene_prompt(day, idx):
    return (f"It is Day {day}, scene {idx} of {SCENES_PER_DAY}. "
            f"{profile_text()}\n"
            f"Current meters: {meters_text()}\nPlayer decision pattern:\n{pattern_summary()}\n"
            f"Write an ordinary everyday situation fitting that moment of the day. "
            f"Suggested theme for this scene: {theme_for(day, idx)}. "
            f"Reply with ONLY JSON in this schema:\n{SCENE_SCHEMA}")


def turn_prompt(scene, decision):
    s = st.session_state
    last_of_day = s.scene_in_day == SCENES_PER_DAY
    last_of_game = last_of_day and s.day == DAYS
    if last_of_game:
        nxt = ("This was the FINAL decision of the whole game. Set next_scene to "
               '{"time_of_day": "Night", "narrative": "A quiet closing reflection of 2-3 sentences", '
               '"choices": []}.')
    elif last_of_day:
        nxt = (f"This was the last decision of Day {s.day}. next_scene should be the start of "
               f"Day {s.day + 1} (morning), reflecting how the player's choices carried over.")
    else:
        nxt = (f"next_scene is decision {s.scene_in_day + 1} of {SCENES_PER_DAY} on Day "
               f"{s.day}, progressing naturally through the day.")
    if not last_of_game:
        nd, ni = (s.day + 1, 1) if last_of_day else (s.day, s.scene_in_day + 1)
        nxt += f" Suggested theme for next_scene: {theme_for(nd, ni)}."
    return (
        f"{profile_text()}\n"
        f"Current meters: {meters_text()}\n"
        f"Player decision pattern:\n{pattern_summary()}\n\n"
        f"Current situation: {scene['narrative']}\n"
        f"The player decided: \"{decision}\"\n\n"
        f"{nxt}\n"
        f"Reflect the current meters in tone (high anxiety = tense, jumpy prose; low energy = foggy, "
        f"slow prose; low social connection = loneliness, distance).\n"
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
        '"reflection": "4-6 sentences", '
        '"takeaway": "one gentle real-world takeaway sentence"}'
    )


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------
def reset_game():
    rng = random.Random()
    st.session_state.profile = new_profile()
    # starting meters vary a little each game
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
        return "BURNOUT: you ran out of mental energy. Every decision now feels impossible."
    if m["anxiety"] >= 100:
        return "OVERWHELMED: the anxiety became too loud to think through. You need to stop and rest."
    if m["social_connection"] <= 0:
        return "ISOLATED: the people around you have drifted away, and the silence is heavy."
    return None


# --------------------------------------------------------------------------
# UI pieces
# --------------------------------------------------------------------------
def footer():
    st.divider()
    st.caption(f"{GAME_TITLE} - a game created by **{OWNER}**")


def show_meters(applied=None):
    st.markdown("##### Mind Status")
    cols = st.columns(4)
    for col, m in zip(cols, METERS):
        val = st.session_state.meters[m]
        delta = None
        if applied and applied.get(m):
            delta = f"{applied[m]:+d}"
        with col:
            st.metric(METER_LABELS[m], val, delta=delta,
                      delta_color="inverse" if m == "anxiety" else "normal")
            st.progress(val / 100)


def screen_title():
    st.markdown(f"<h1 style='text-align:center;margin-bottom:0'>{GAME_TITLE}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;font-size:1.2rem;margin-top:0'><i>{SUBTITLE}</i></p>",
                unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align:center'>A game created by {OWNER}</h4>", unsafe_allow_html=True)
    st.divider()
    st.write("You are an ordinary person living an ordinary few days. Every small choice you make, "
             "from a missed bus to a coworker's request, sends a ripple through your mind and the "
             "people around you. There are no right answers, only consequences.")
    st.write("Watch your four meters: **Mental Energy**, **Empathy**, **Anxiety Level** and "
             "**Social Connection**. The story is written live by AI, and every new game gives you a "
             "different character, setting and cast, so no two playthroughs are alike.")

    if not st.session_state.api_key:
        st.info("Add your Gemini API key in the app Secrets (GEMINI_API_KEY) or in the sidebar to begin.")
        return
    if st.button("Begin", type="primary", use_container_width=True):
        with st.spinner("Setting the scene..."):
            try:
                st.session_state.scene = ask_gemini(scene_prompt(1, 1))
                st.session_state.phase = "scene"
                st.rerun()
            except RuntimeError as err:
                st.error(f"{err}\n\nCheck your API key and model name, then try again.")


def screen_scene():
    s = st.session_state
    scene = s.scene
    show_meters()
    st.divider()
    st.caption(f"Day {s.day} of {DAYS}  |  Decision {s.scene_in_day} of {SCENES_PER_DAY}  |  "
               f"{scene.get('time_of_day', '')}")
    st.write(scene["narrative"])

    choices = scene["choices"][:3]
    options = choices + ["Do something else (type your own action)"]
    pick = st.radio("What do you do?", options, index=None, key=f"pick_{s.day}_{s.scene_in_day}")
    custom = ""
    if pick == options[-1]:
        custom = st.text_input("Describe what you do", max_chars=300,
                               key=f"custom_{s.day}_{s.scene_in_day}")

    if st.button("Decide", type="primary", disabled=pick is None):
        decision = custom.strip() if pick == options[-1] else pick
        if not decision:
            st.warning("Please describe your action first.")
            return
        with st.spinner("The world reacts..."):
            try:
                result = ask_gemini(turn_prompt(scene, decision), grounded=True)
            except RuntimeError as err:
                st.error(str(err))
                return
        tag = str(result.get("choice_tag", "balanced")).lower()
        s.history.append({"day": s.day, "scene": s.scene_in_day, "decision": decision, "tag": tag})
        s.applied = apply_deltas(result.get("deltas", {}))
        s.result = result
        s.ending_note = crisis_ending()
        s.phase = "ripple"
        st.rerun()


def screen_ripple():
    s = st.session_state
    result = s.result
    st.markdown("#### The Ripple")
    st.write(result.get("ripple", ""))
    insight = (result.get("insight") or "").strip()
    if insight:
        st.info(f"**Psychology insight:** {insight}")
    st.divider()
    show_meters(s.applied)
    st.divider()

    last_of_game = s.day == DAYS and s.scene_in_day == SCENES_PER_DAY
    if s.ending_note or last_of_game:
        if st.button("See your ending", type="primary", use_container_width=True):
            s.phase = "end"
            st.rerun()
        return

    if st.button("Continue", type="primary", use_container_width=True):
        nxt = result.get("next_scene") or {}
        new_day = s.scene_in_day == SCENES_PER_DAY
        new_day_no = s.day + 1 if new_day else s.day
        new_idx = 1 if new_day else s.scene_in_day + 1
        if new_day:
            s.meters["mental_energy"] = min(100, s.meters["mental_energy"] + 15)
            s.meters["anxiety"] = max(0, s.meters["anxiety"] - 5)
        if not nxt.get("narrative") or len(nxt.get("choices", [])) < 3:
            with st.spinner("Generating the next scene..."):
                try:
                    nxt = ask_gemini(scene_prompt(new_day_no, new_idx))
                except RuntimeError as err:
                    st.error(str(err))
                    return
        s.scene = nxt
        s.day, s.scene_in_day = new_day_no, new_idx
        s.phase = "scene"
        st.rerun()


def screen_end():
    s = st.session_state
    if s.end_data is None:
        with st.spinner("Reflecting on your journey..."):
            try:
                s.end_data = ask_gemini(ending_prompt())
            except RuntimeError:
                s.end_data = {
                    "title": "The Quiet Observer",
                    "reflection": "Your choices rippled outward in ways you may only notice later.",
                    "takeaway": "Small decisions shape who we become.",
                }
    end = s.end_data
    if s.ending_note:
        st.error(s.ending_note)
    else:
        st.success(f"You made it through all {DAYS} days.")
    st.markdown(f"## Your Ripple: {end.get('title', '')}")
    st.write(end.get("reflection", ""))
    st.markdown(f"**Takeaway:** {end.get('takeaway', '')}")
    st.divider()
    show_meters()
    st.markdown(f"<p style='text-align:center'>Thank you for playing {GAME_TITLE}.<br>"
                f"<b>A game created by {OWNER}.</b></p>", unsafe_allow_html=True)
    if st.button("Play again", type="primary", use_container_width=True):
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
