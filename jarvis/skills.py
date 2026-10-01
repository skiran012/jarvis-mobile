"""Skills — the actions JARVIS can take. Each skill is a Python function plus a JSON schema
that is handed to Claude as a "tool". Claude decides when to call which skill.

Add your own skill:  write a function, add a schema to TOOLS, register it in REGISTRY.
"""

from __future__ import annotations

import ast
import json
import math
import operator
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from .config import CONFIG
from .memory import LongTermMemory

LTM = LongTermMemory()
HTTP_TIMEOUT = 10


# ---------------------------------------------------------------- time & date
def get_datetime() -> str:
    now = datetime.now(ZoneInfo(CONFIG.timezone))
    return now.strftime(f"%A, %d %B %Y, %I:%M %p ({CONFIG.timezone})")


# ---------------------------------------------------------------- calculator (safe — no eval())
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_FUNCS = {n: getattr(math, n) for n in ("sqrt", "sin", "cos", "tan", "log", "log10", "exp", "factorial")}
_FUNCS.update({"abs": abs, "round": round, "pi": math.pi, "e": math.e})


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _FUNCS:
        return _FUNCS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise ValueError("Unsupported expression")


def calculate(expression: str) -> str:
    try:
        result = _eval(ast.parse(expression.replace("^", "**"), mode="eval").body)
        return f"{expression} = {round(result, 6) if isinstance(result, float) else result}"
    except Exception as exc:
        return f"Could not calculate '{expression}': {exc}"


# ---------------------------------------------------------------- weather (Open-Meteo, no API key)
_WMO = {0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog",
        51: "light drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 80: "rain showers",
        95: "thunderstorm"}


def get_weather(city: str) -> str:
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1}, timeout=HTTP_TIMEOUT,
        ).json()
        if not geo.get("results"):
            return f"I couldn't find a place called {city}."
        place = geo["results"][0]
        wx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"], "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "forecast_days": 1, "timezone": "auto",
            },
            timeout=HTTP_TIMEOUT,
        ).json()
        c, d = wx["current"], wx["daily"]
        return (
            f"{place['name']}, {place.get('country', '')}: {c['temperature_2m']}°C, "
            f"{_WMO.get(c['weather_code'], 'conditions code ' + str(c['weather_code']))}, "
            f"humidity {c['relative_humidity_2m']}%, wind {c['wind_speed_10m']} km/h. "
            f"Today {d['temperature_2m_min'][0]}–{d['temperature_2m_max'][0]}°C, "
            f"rain chance {d['precipitation_probability_max'][0]}%."
        )
    except Exception as exc:
        return f"Weather service unavailable: {exc}"


# ---------------------------------------------------------------- web lookup
def web_search(query: str) -> str:
    """Tavily search when TAVILY_API_KEY is set; otherwise a Wikipedia summary."""
    try:
        if CONFIG.tavily_api_key:
            r = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": CONFIG.tavily_api_key, "query": query, "max_results": 3},
                timeout=HTTP_TIMEOUT,
            ).json()
            return json.dumps([{"title": x["title"], "content": x["content"][:400], "url": x["url"]}
                               for x in r.get("results", [])])
        s = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 1},
            headers={"User-Agent": "JARVIS-Mobile/1.0"}, timeout=HTTP_TIMEOUT,
        ).json()
        hits = s.get("query", {}).get("search", [])
        if not hits:
            return "No results found."
        title = hits[0]["title"]
        summary = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}",
            headers={"User-Agent": "JARVIS-Mobile/1.0"}, timeout=HTTP_TIMEOUT,
        ).json()
        return f"{title}: {summary.get('extract', '')}"
    except Exception as exc:
        return f"Search unavailable: {exc}"


# ---------------------------------------------------------------- notes & reminders
def save_note(text: str) -> str:
    return LTM.add_note(text)


def list_notes() -> str:
    notes = LTM.list_notes()
    return json.dumps(notes[-20:], ensure_ascii=False) if notes else "No notes saved yet."


def set_reminder(text: str, when: str) -> str:
    return LTM.add_reminder(text, when)


def list_reminders() -> str:
    rem = LTM.list_reminders()
    return json.dumps(rem[-20:], ensure_ascii=False) if rem else "No reminders set."


# ---------------------------------------------------------------- tool schemas for Claude
def _tool(name, description, props=None, required=None):
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": props or {}, "required": required or []},
    }


_STR = {"type": "string"}

TOOLS = [
    _tool("get_datetime", "Current local date and time."),
    _tool("calculate", "Evaluate a maths expression, e.g. '18% of 2450' written as '0.18*2450'.",
          {"expression": _STR}, ["expression"]),
    _tool("get_weather", "Current weather and today's forecast for a city.", {"city": _STR}, ["city"]),
    _tool("web_search", "Look up facts, news or people on the web.", {"query": _STR}, ["query"]),
    _tool("save_note", "Save something the user asks you to remember.", {"text": _STR}, ["text"]),
    _tool("list_notes", "Read back the user's saved notes."),
    _tool("set_reminder", "Store a reminder with a natural-language time.",
          {"text": _STR, "when": _STR}, ["text", "when"]),
    _tool("list_reminders", "Read back the user's reminders."),
]

REGISTRY = {
    "get_datetime": get_datetime, "calculate": calculate, "get_weather": get_weather,
    "web_search": web_search, "save_note": save_note, "list_notes": list_notes,
    "set_reminder": set_reminder, "list_reminders": list_reminders,
}


def run_tool(name: str, args: dict) -> str:
    fn = REGISTRY.get(name)
    if fn is None:
        return f"Unknown tool {name}"
    try:
        return str(fn(**(args or {})))
    except Exception as exc:
        return f"Tool {name} failed: {exc}"
