#!/usr/bin/env python3
"""
THE RIPPLE EFFECT (Echoes of Choice)
A text-based psychological life simulator powered by the Gemini API.

Created by NilanjanC

Setup:
    pip install google-genai
    export GEMINI_API_KEY="your_key_here"        (Mac/Linux)
    set GEMINI_API_KEY=your_key_here             (Windows CMD)
    $env:GEMINI_API_KEY="your_key_here"          (Windows PowerShell)

Run:
    python the_ripple_effect.py
"""

import json
import os
import re
import sys
import textwrap
import time

from google import genai
from google.genai import types

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
OWNER = "NilanjanC"
GAME_TITLE = "THE RIPPLE EFFECT"
SUBTITLE = "Echoes of Choice"

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DAYS = 3                 # number of days in a run
SCENES_PER_DAY = 5       # decisions per day
USE_WEB_GROUNDING = True # let Gemini pull real psychology theories via Google Search
WIDTH = 78

METERS = ["mental_energy", "empathy", "anxiety", "social_connection"]
METER_LABELS = {
    "mental_energy": "Mental Energy",
    "empathy": "Empathy",
    "anxiety": "Anxiety Level",
    "social_connection": "Social Connection",
}

# ANSI colours (silently ignored on terminals that do not support them)
C = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "cyan": "\033[96m", "green": "\033[92m", "yellow": "\033[93m",
    "red": "\033[91m", "magenta": "\033[95m", "blue": "\033[94m",
}
if os.name == "nt":
    os.system("")  # enables ANSI on modern Windows terminals


def paint(text, *styles):
    return "".join(C[s] for s in styles) + text + C["reset"]


def wrap(text, indent=""):
    return textwrap.fill(text, width=WIDTH, initial_indent=indent, subsequent_indent=indent)


# --------------------------------------------------------------------------
# Gemini helpers
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


def make_client():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print(paint("\nNo API key found.", "red", "bold"))
        print("Set your key first, for example:")
        print('  export GEMINI_API_KEY="your_key_here"\n')
        key = input("Or paste your Gemini API key here (not saved anywhere): ").strip()
        if not key:
            sys.exit(1)
    return genai.Client(api_key=key)


def extract_json(text):
    """Pull the first JSON object out of a model response, tolerating stray text/fences."""
    if not text:
        raise ValueError("Empty response")
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start:end + 1])


def ask_gemini(client, prompt, grounded=False, retries=3):
    tools = None
    if grounded and USE_WEB_GROUNDING:
        tools = [types.Tool(google_search=types.GoogleSearch())]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=1.0,
        tools=tools,
    )
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.models.generate_content(model=MODEL_NAME, contents=prompt, config=config)
            return extract_json(resp.text)
        except Exception as err:  # network, quota, bad JSON ...
            last_err = err
            if attempt < retries:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"Gemini request failed: {last_err}")


# --------------------------------------------------------------------------
# Game state
# --------------------------------------------------------------------------
class State:
    def __init__(self):
        self.meters = {"mental_energy": 80, "empathy": 60, "anxiety": 30, "social_connection": 60}
        self.history = []        # list of dicts: day, scene, situation, decision, tag
        self.day = 1
        self.scene_in_day = 1

    def apply(self, deltas):
        applied = {}
        for m in METERS:
            try:
                d = int(deltas.get(m, 0))
            except (TypeError, ValueError):
                d = 0
            d = max(-25, min(25, d))
            before = self.meters[m]
            self.meters[m] = max(0, min(100, before + d))
            applied[m] = self.meters[m] - before
        return applied

    def pattern_summary(self, last_n=8):
        recent = self.history[-last_n:]
        if not recent:
            return "No decisions yet."
        tags = {}
        for h in recent:
            tags[h["tag"]] = tags.get(h["tag"], 0) + 1
        tag_text = ", ".join(f"{k} x{v}" for k, v in sorted(tags.items(), key=lambda kv: -kv[1]))
        lines = [f'Day {h["day"]}: "{h["decision"]}" ({h["tag"]})' for h in recent]
        return f"Tag counts: {tag_text}\nRecent decisions:\n" + "\n".join(lines)

    def meters_text(self):
        return ", ".join(f"{m}={self.meters[m]}" for m in METERS)


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
def clear():
    os.system("cls" if os.name == "nt" else "clear")


def title_screen():
    clear()
    line = "=" * WIDTH
    print(paint(line, "cyan"))
    print()
    print(paint(GAME_TITLE.center(WIDTH), "cyan", "bold"))
    print(paint(f"( {SUBTITLE} )".center(WIDTH), "cyan"))
    print()
    print(paint(f"A game created by {OWNER}".center(WIDTH), "yellow", "bold"))
    print(paint(f"(c) {OWNER}. All rights reserved.".center(WIDTH), "dim"))
    print()
    print(paint(line, "cyan"))
    print()
    print(wrap("You are an ordinary person living an ordinary few days. Every small choice "
               "you make, from a missed bus to a coworker's request, sends a ripple through your "
               "mind and the people around you. There are no right answers, only consequences."))
    print()
    print(wrap("Watch your four meters: Mental Energy, Empathy, Anxiety Level and Social "
               "Connection. The story is written live by AI, so no two playthroughs are alike."))
    print()
    input(paint("Press ENTER to begin...", "green"))


def bar(value, good_when_high=True, width=20):
    filled = round(value / 100 * width)
    if good_when_high:
        colour = "green" if value >= 60 else "yellow" if value >= 30 else "red"
    else:
        colour = "red" if value >= 70 else "yellow" if value >= 40 else "green"
    return paint("#" * filled, colour) + paint("-" * (width - filled), "dim")


def show_meters(state, applied=None):
    print(paint("\n  --- Mind Status ---", "magenta", "bold"))
    for m in METERS:
        label = METER_LABELS[m].ljust(18)
        delta = ""
        if applied and applied.get(m):
            d = applied[m]
            good = (d > 0) != (m == "anxiety")
            delta = paint(f" ({d:+d})", "green" if good else "red")
        print(f"  {label} [{bar(state.meters[m], m != 'anxiety')}] {state.meters[m]:>3}{delta}")
    print()


def show_scene(state, scene):
    print(paint("-" * WIDTH, "dim"))
    header = f"Day {state.day} of {DAYS}  |  Decision {state.scene_in_day} of {SCENES_PER_DAY}  |  {scene.get('time_of_day', '')}"
    print(paint(header, "cyan", "bold"))
    print(paint("-" * WIDTH, "dim"))
    print()
    print(wrap(scene["narrative"]))
    print()


def get_choice(scene):
    choices = scene["choices"][:3]
    for i, ch in enumerate(choices, 1):
        print(wrap(f"{i}. {ch}", indent="   ").replace("   ", "  ", 1))
    print("  4. Do something else (type your own action)")
    print()
    while True:
        raw = input(paint("Your choice > ", "green", "bold")).strip().lower()
        if raw in ("q", "quit", "exit"):
            print(paint(f"\nThanks for playing. A game by {OWNER}.\n", "yellow"))
            sys.exit(0)
        if raw in ("1", "2", "3"):
            return choices[int(raw) - 1]
        if raw == "4":
            custom = input("Describe what you do > ").strip()
            if custom:
                return custom[:300]
        print(paint("Please type 1, 2, 3 or 4 (or 'q' to quit).", "yellow"))


def thinking():
    print(paint("\n  ...the world reacts...", "dim"))


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
def opening_prompt():
    return (f"Start the game. It is Day 1, scene 1 of {SCENES_PER_DAY}. Begin with an ordinary "
            f"morning situation (waking up, getting ready, or the commute). "
            f"Reply with ONLY JSON in this schema:\n{SCENE_SCHEMA}")


def turn_prompt(state, scene, decision):
    last_of_day = state.scene_in_day == SCENES_PER_DAY
    last_of_game = last_of_day and state.day == DAYS
    if last_of_game:
        nxt = ("This was the FINAL decision of the whole game. Set next_scene to "
               '{"time_of_day": "Night", "narrative": "A quiet closing reflection of 2-3 sentences", '
               '"choices": []}.')
    elif last_of_day:
        nxt = (f"This was the last decision of Day {state.day}. next_scene should be the start of "
               f"Day {state.day + 1} (morning), reflecting how the player's choices carried over.")
    else:
        nxt = (f"next_scene is decision {state.scene_in_day + 1} of {SCENES_PER_DAY} on Day "
               f"{state.day}, progressing naturally through the day.")
    return (
        f"Current meters: {state.meters_text()}\n"
        f"Player decision pattern:\n{state.pattern_summary()}\n\n"
        f"Current situation: {scene['narrative']}\n"
        f"The player decided: \"{decision}\"\n\n"
        f"{nxt}\n"
        f"Reflect the current meters in tone (high anxiety = tense, jumpy prose; low energy = foggy, "
        f"slow prose; low social connection = loneliness, distance).\n"
        f"Reply with ONLY JSON in this schema:\n{TURN_SCHEMA}"
    )


def ending_prompt(state):
    return (
        f"The game is over. Final meters: {state.meters_text()}\n"
        f"All decisions:\n{state.pattern_summary(last_n=len(state.history))}\n\n"
        "Write a warm, honest, non-judgmental reflection on who this player was over these days. "
        "Reply with ONLY JSON: "
        '{"title": "a short personality-style title for this run", '
        '"reflection": "4-6 sentences", '
        '"takeaway": "one gentle real-world takeaway sentence"}'
    )


# --------------------------------------------------------------------------
# Early-ending check
# --------------------------------------------------------------------------
def crisis_ending(state):
    m = state.meters
    if m["mental_energy"] <= 0:
        return "BURNOUT: you ran out of mental energy. Every decision now feels impossible."
    if m["anxiety"] >= 100:
        return "OVERWHELMED: the anxiety became too loud to think through. You need to stop and rest."
    if m["social_connection"] <= 0:
        return "ISOLATED: the people around you have drifted away, and the silence is heavy."
    return None


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
def play():
    title_screen()
    client = make_client()
    state = State()

    clear()
    print(paint(f"  {GAME_TITLE}  -  a game by {OWNER}", "cyan", "bold"))
    thinking()
    try:
        scene = ask_gemini(client, opening_prompt())
    except RuntimeError as err:
        print(paint(f"\n{err}", "red"))
        print("Check your API key, model name and internet connection, then try again.")
        return

    ending_note = None
    while True:
        show_meters(state)
        show_scene(state, scene)
        decision = get_choice(scene)
        thinking()

        try:
            result = ask_gemini(client, turn_prompt(state, scene, decision), grounded=True)
        except RuntimeError as err:
            print(paint(f"\n{err}", "red"))
            if input("Try that again? (y/n) > ").strip().lower().startswith("y"):
                continue
            return

        tag = str(result.get("choice_tag", "balanced")).lower()
        state.history.append({
            "day": state.day, "scene": state.scene_in_day,
            "decision": decision, "tag": tag,
        })
        applied = state.apply(result.get("deltas", {}))

        clear()
        print(paint(f"  {GAME_TITLE}  -  a game by {OWNER}", "cyan", "bold"))
        print(paint("\n  The Ripple:", "magenta", "bold"))
        print(wrap(result.get("ripple", ""), indent="  "))
        insight = (result.get("insight") or "").strip()
        if insight:
            print(paint("\n  Psychology Insight:", "blue", "bold"))
            print(wrap(insight, indent="  "))
        show_meters(state, applied)

        # Check game end conditions
        ending_note = crisis_ending(state)
        last_of_game = state.day == DAYS and state.scene_in_day == SCENES_PER_DAY
        if ending_note or last_of_game:
            break

        input(paint("Press ENTER to continue...", "green"))
        clear()

        nxt = result.get("next_scene") or {}
        if not nxt.get("narrative") or len(nxt.get("choices", [])) < 3:
            print(paint("The story hiccuped, so generating a fresh scene...", "yellow"))
            try:
                nxt = ask_gemini(client, opening_prompt().replace(
                    "Day 1, scene 1", f"Day {state.day}, scene {state.scene_in_day + 1}"))
            except RuntimeError as err:
                print(paint(str(err), "red"))
                return
        scene = nxt

        if state.scene_in_day == SCENES_PER_DAY:
            state.day += 1
            state.scene_in_day = 1
            # a night's sleep: partial recovery
            state.meters["mental_energy"] = min(100, state.meters["mental_energy"] + 15)
            state.meters["anxiety"] = max(0, state.meters["anxiety"] - 5)
            print(paint(f"\n  ~ A night passes. You wake up on Day {state.day}. ~\n", "cyan", "bold"))
        else:
            state.scene_in_day += 1

    # ---- Ending ----
    print()
    if ending_note:
        print(paint("  " + ending_note, "red", "bold"))
    else:
        print(paint(f"  You made it through all {DAYS} days.", "green", "bold"))
    thinking()
    try:
        end = ask_gemini(client, ending_prompt(state))
    except RuntimeError:
        end = {"title": "The Quiet Observer",
               "reflection": "Your choices rippled outward in ways you may only notice later.",
               "takeaway": "Small decisions shape who we become."}

    print()
    print(paint("=" * WIDTH, "cyan"))
    print(paint(f"  Your Ripple: {end.get('title', '')}", "yellow", "bold"))
    print(paint("=" * WIDTH, "cyan"))
    print()
    print(wrap(end.get("reflection", ""), indent="  "))
    print()
    print(paint("  Takeaway:", "magenta", "bold"))
    print(wrap(end.get("takeaway", ""), indent="  "))
    print()
    print(paint(f"  Thank you for playing {GAME_TITLE}.", "cyan"))
    print(paint(f"  A game created by {OWNER}.", "yellow", "bold"))
    print()


if __name__ == "__main__":
    try:
        play()
    except KeyboardInterrupt:
        print(paint(f"\n\nGame closed. A game by {OWNER}.\n", "yellow"))
