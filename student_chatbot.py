
import os
import re
import json
import random
import ast
import operator
import calendar
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


MEMORY_FILE = Path("chatbot_memory.json")

DEFAULT_BOT_NAME = "StudBot"
DEFAULT_LOCATION = "Guntur, Andhra Pradesh, India"

OPENAI_MODEL = "gpt-5.6"

BOT_NAME = DEFAULT_BOT_NAME
USER_NAME = ""
LOCATION = DEFAULT_LOCATION

MEMORY = {
    "user_name": "",
    "bot_name": DEFAULT_BOT_NAME,
    "facts": {},
    "interests": [],
    "hobbies": [],
    "favorites": {},
    "goals": [],
    "conversation_topics": [],
    "mood": "",
    "last_topic": "",
    "message_count": 0
}

CONVERSATION_HISTORY = []

CLIENT = None


def load_memory():
    global BOT_NAME
    global USER_NAME
    global MEMORY

    try:
        if MEMORY_FILE.exists():
            with open(
                MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

            if isinstance(data, dict):
                MEMORY.update(data)

            BOT_NAME = str(
                MEMORY.get(
                    "bot_name",
                    DEFAULT_BOT_NAME
                )
            )

            USER_NAME = str(
                MEMORY.get(
                    "user_name",
                    ""
                )
            )

    except Exception:
        BOT_NAME = DEFAULT_BOT_NAME
        USER_NAME = ""


def save_memory():
    try:
        MEMORY["bot_name"] = BOT_NAME
        MEMORY["user_name"] = USER_NAME

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                MEMORY,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception:
        pass


load_memory()

def initialize_ai():
    global CLIENT

    if OpenAI is None:
        return

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        return

    try:
        CLIENT = OpenAI(
            api_key=api_key
        )
    except Exception:
        CLIENT = None


initialize_ai()


def clean_text(text):
    text = str(text)
    text = text.lower().strip()
    text = re.sub(
        r"\s+",
        " ",
        text
    )
    return text


def title_name(name):
    name = str(name).strip()

    name = re.sub(
        r"[^a-zA-Z0-9 _-]",
        "",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    if not name:
        return ""

    return name.title()


def extract_name(text):
    value = text.strip()

    value = re.split(
        r"\b(?:now|please|okay|ok|from now on)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]

    value = re.sub(
        r"[^a-zA-Z0-9 _-]",
        "",
        value
    )

    value = value.strip()

    if not value:
        return ""

    words = value.split()

    if len(words) > 3:
        words = words[:3]

    return title_name(
        " ".join(words)
    )


# ============================================================
# BOT NAME
# ============================================================

def change_bot_name(text):
    global BOT_NAME

    patterns = [
        r"\byour\s+name\s+is\s+(.+)",
        r"\byou\s+name\s+is\s+(.+)",
        r"\bcall\s+yourself\s+(.+)",
        r"\bcall\s+you\s+(.+)",
        r"\bi\s+will\s+call\s+you\s+(.+)",
        r"\bchange\s+your\s+name\s+to\s+(.+)",
        r"\brename\s+yourself\s+to\s+(.+)",
        r"\bfrom\s+now\s+on\s+your\s+name\s+is\s+(.+)"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            new_name = extract_name(
                match.group(1)
            )

            if new_name:
                old_name = BOT_NAME
                BOT_NAME = new_name
                MEMORY["bot_name"] = BOT_NAME
                save_memory()

                return (
                    f"Okay! You were calling me "
                    f"{old_name}, but from now on "
                    f"my name is {BOT_NAME}. "
                    f"I'll remember that."
                )

    return None

def change_user_name(text):
    global USER_NAME

    patterns = [
        r"\bmy\s+name\s+is\s+(.+)",
        r"\bcall\s+me\s+(.+)",
        r"\bi'm\s+(.+)",
        r"\bi\s+am\s+(.+)"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            name = extract_name(
                match.group(1)
            )

            if name and len(name) <= 40:
                USER_NAME = name
                MEMORY["user_name"] = USER_NAME
                save_memory()

                return (
                    f"Nice to meet you, "
                    f"{USER_NAME}! I'll remember "
                    f"your name."
                )

    return None

def bot_is_called(text):
    if not BOT_NAME:
        return False

    pattern = (
        r"^\s*"
        r"(?:hey|hi|hello)?"
        r"\s*"
        + re.escape(BOT_NAME)
        + r"\b"
    )

    return bool(
        re.match(
            pattern,
            text,
            re.IGNORECASE
        )
    )


def remove_bot_name(text):
    if not BOT_NAME:
        return text.strip()

    pattern = (
        r"^\s*"
        r"(?:hey|hi|hello)?"
        r"\s*"
        + re.escape(BOT_NAME)
        + r"\s*"
        r"[,;:\-!]?\s*"
    )

    return re.sub(
        pattern,
        "",
        text,
        count=1,
        flags=re.IGNORECASE
    ).strip()


def remember_user_information(text):
    lower = clean_text(text)

    patterns = {
        "study": [
            r"\bi study (.+)",
            r"\bi'm studying (.+)",
            r"\bi am studying (.+)",
            r"\bi am a student of (.+)",
            r"\bmy branch is (.+)",
            r"\bi'm doing (.+)"
        ],

        "work": [
            r"\bi work as (.+)",
            r"\bi'm working as (.+)",
            r"\bi am working as (.+)"
        ],

        "college": [
            r"\bmy college is (.+)",
            r"\bi study at (.+)"
        ],

        "city": [
            r"\bi live in (.+)",
            r"\bi am from (.+)",
            r"\bi'm from (.+)",
            r"\bmy hometown is (.+)"
        ]
    }

    for key, expressions in patterns.items():
        for expression in expressions:
            match = re.search(
                expression,
                text,
                re.IGNORECASE
            )

            if match:
                value = match.group(1).strip()

                value = re.split(
                    r"\b(?:and|but|because|so|now)\b",
                    value,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0].strip()

                if value:
                    MEMORY["facts"][key] = value
                    save_memory()
                    break

    hobby_patterns = [
        r"\bi like (.+)",
        r"\bi love (.+)",
        r"\bi enjoy (.+)",
        r"\bmy hobby is (.+)",
        r"\bhobbies are (.+)"
    ]

    for pattern in hobby_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = match.group(1).strip()

            value = re.split(
                r"\b(?:but|because|and)\b",
                value,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0].strip()

            if value:
                add_memory_item(
                    "hobbies",
                    value
                )

    interest_patterns = [
        r"\bi'm interested in (.+)",
        r"\bi am interested in (.+)",
        r"\bmy interest is (.+)",
        r"\bi like learning (.+)"
    ]

    for pattern in interest_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = match.group(1).strip()

            if value:
                add_memory_item(
                    "interests",
                    value
                )

    goal_patterns = [
        r"\bmy goal is (.+)",
        r"\bi want to become (.+)",
        r"\bi want to be (.+)",
        r"\bi want to learn (.+)",
        r"\bi'm trying to learn (.+)"
    ]

    for pattern in goal_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = match.group(1).strip()

            value = re.split(
                r"\b(?:and|but|because)\b",
                value,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0].strip()

            if value:
                add_memory_item(
                    "goals",
                    value
                )


def add_memory_item(key, value):
    if key not in MEMORY:
        MEMORY[key] = []

    value = value.strip()

    if not value:
        return

    existing = [
        str(item).lower()
        for item in MEMORY[key]
    ]

    if value.lower() not in existing:
        MEMORY[key].append(value)

    if len(MEMORY[key]) > 20:
        MEMORY[key] = MEMORY[key][-20:]

    save_memory()


def detect_favorites(text):
    patterns = [
        (
            r"\bmy favorite movie is (.+)",
            "movie"
        ),
        (
            r"\bmy favourite movie is (.+)",
            "movie"
        ),
        (
            r"\bmy favorite actor is (.+)",
            "actor"
        ),
        (
            r"\bmy favourite actor is (.+)",
            "actor"
        ),
        (
            r"\bmy favorite food is (.+)",
            "food"
        ),
        (
            r"\bmy favourite food is (.+)",
            "food"
        ),
        (
            r"\bmy favorite language is (.+)",
            "language"
        ),
        (
            r"\bmy favorite programming language is (.+)",
            "language"
        )
    ]

    for pattern, key in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = match.group(1).strip()

            value = re.split(
                r"\b(?:and|but|because)\b",
                value,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0].strip()

            if value:
                MEMORY["favorites"][key] = value
                save_memory()


def detect_mood(text):
    lower = clean_text(text)

    positive = [
        "happy",
        "excited",
        "great",
        "awesome",
        "amazing",
        "good",
        "wonderful",
        "fantastic",
        "glad",
        "proud"
    ]

    negative = [
        "sad",
        "angry",
        "upset",
        "bad",
        "tired",
        "lonely",
        "bored",
        "frustrated",
        "worried",
        "stressed",
        "confused",
        "depressed"
    ]

    if any(
        word in lower
        for word in positive
    ):
        MEMORY["mood"] = "positive"

    elif any(
        word in lower
        for word in negative
    ):
        MEMORY["mood"] = "negative"

    save_memory()


def current_time():
    return datetime.now().strftime(
        "%I:%M:%S %p"
    )


def current_date():
    return datetime.now().strftime(
        "%A, %d %B %Y"
    )


def calendar_info():
    now = datetime.now()

    days = calendar.monthrange(
        now.year,
        now.month
    )[1]

    return (
        f"Today is {now.strftime('%A, %d %B %Y')}.\n"
        f"The current month is {now.strftime('%B %Y')}.\n"
        f"This month has {days} days."
    )


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos
}


def calculate_expression(expression):

    try:
        tree = ast.parse(
            expression,
            mode="eval"
        )
    except Exception:
        return None

    def evaluate(node):

        if isinstance(
            node,
            ast.Expression
        ):
            return evaluate(node.body)

        if isinstance(
            node,
            ast.Constant
        ):
            if isinstance(
                node.value,
                (int, float)
            ):
                return node.value

            raise ValueError

        if isinstance(
            node,
            ast.BinOp
        ):
            left = evaluate(
                node.left
            )

            right = evaluate(
                node.right
            )

            operation = OPERATORS.get(
                type(node.op)
            )

            if operation is None:
                raise ValueError

            return operation(
                left,
                right
            )

        if isinstance(
            node,
            ast.UnaryOp
        ):
            value = evaluate(
                node.operand
            )

            operation = OPERATORS.get(
                type(node.op)
            )

            if operation is None:
                raise ValueError

            return operation(
                value
            )

        raise ValueError

    try:
        result = evaluate(tree)

        if isinstance(
            result,
            float
        ):
            result = round(
                result,
                8
            )

        return result

    except Exception:
        return None


def extract_math(text):

    lower = clean_text(text)

    replacements = [
        ("multiplied by", "*"),
        ("divided by", "/"),
        ("times", "*"),
        ("into", "*"),
        ("plus", "+"),
        ("minus", "-")
    ]

    expression = lower

    for word, symbol in replacements:
        expression = expression.replace(
            word,
            symbol
        )

    expression = re.sub(
        r"^(what is|what's|calculate|solve|find)\s+",
        "",
        expression
    )

    expression = re.sub(
        r"[^0-9+\-*/().% ]",
        "",
        expression
    )

    if not expression.strip():
        return None

    if not re.search(
        r"\d",
        expression
    ):
        return None

    if not re.search(
        r"[+\-*/%]",
        expression
    ):
        return None

    return calculate_expression(
        expression
    )
def friendly_response(text):
    global MEMORY

    lower = clean_text(text)

    if re.search(
        r"\b(hi|hii|hey|hello|heyy)\b",
        lower
    ):
        greetings = [
            f"Hey! 😊 Nice to hear from you. How are you doing?",
            f"Hi! I'm glad you came to talk with me. How's your day going?",
            f"Hey there! 😄 What's going on with you today?",
            f"Hello! Nice to see you. What have you been up to?"
        ]

        return random.choice(
            greetings
        )

    if (
        "how are you" in lower
        or "how r u" in lower
    ):
        return random.choice([
            f"I'm doing great! Thanks for asking. 😊 "
            f"What about you?",
            f"I'm good and ready to chat. "
            f"How has your day been?",
            f"I'm doing well! It's always nice to have "
            f"a conversation. How are you feeling?"
        ])

    if (
        "what are you doing" in lower
        or "what r u doing" in lower
    ):
        return (
            f"Right now I'm here talking with you. 😄 "
            f"So, what are you doing?"
        )

    if (
        "thank you" in lower
        or "thanks" in lower
    ):
        return random.choice([
            "You're very welcome! 😊",
            "Anytime! I'm happy to help.",
            "No problem at all!",
            "Of course! That's what I'm here for."
        ])

    if (
        "good morning" in lower
    ):
        return (
            "Good morning! ☀️ "
            "I hope you have a really good day. "
            "What are you planning to do today?"
        )

    if (
        "good night" in lower
    ):
        return (
            "Good night! 🌙 "
            "Take some rest and have a peaceful sleep."
        )

    if (
        "i am fine" in lower
        or "i'm fine" in lower
        or "i am good" in lower
        or "i'm good" in lower
    ):
        return (
            "That's great to hear! 😊 "
            "What have you been doing today?"
        )

    if (
        "i am tired" in lower
        or "i'm tired" in lower
    ):
        MEMORY["mood"] = "tired"
        save_memory()

        return random.choice([
            "Sounds like you've had a long day. Take a little break. "
            "What made you tired today?",
            "You should give yourself a little rest. 😊 "
            "Was it studying, work, or something else?",
            "I understand. Sometimes a short break helps a lot. "
            "What were you working on?"
        ])

    if (
        "i am bored" in lower
        or "i'm bored" in lower
    ):
        MEMORY["mood"] = "bored"
        save_memory()

        return random.choice([
            "Let's fix that! 😄 We can talk about movies, "
            "technology, programming, or just have a random conversation.",
            "Boredom detected! 😄 Want to talk about something interesting?",
            "Let's do something fun. Do you want a joke, a quiz, "
            "a programming challenge, or just a normal conversation?"
        ])

    if (
        "i am sad" in lower
        or "i'm sad" in lower
        or "feeling sad" in lower
    ):
        MEMORY["mood"] = "sad"
        save_memory()

        return random.choice([
            "I'm sorry you're feeling that way. You don't have to pretend "
            "everything is fine. If you want, tell me what's bothering you.",
            "That sounds difficult. I'm here to listen. "
            "What happened?",
            "I'm here with you. You can talk about it if you feel comfortable."
        ])

    if (
        "i am happy" in lower
        or "i'm happy" in lower
        or "feeling happy" in lower
    ):
        MEMORY["mood"] = "happy"
        save_memory()

        return random.choice([
            "That's wonderful! 😄 What's making you happy?",
            "I love hearing that! What happened?",
            "Nice! You sound happy today. Tell me about it!"
        ])

    if (
        "tell me a joke" in lower
        or "make me laugh" in lower
        or lower == "joke"
    ):
        return random.choice([
            "Why do programmers prefer dark mode? "
            "Because light attracts bugs! 😄",

            "Why did the computer go to the doctor? "
            "Because it had a virus! 😂",

            "Why was the Python programmer confused? "
            "Because there were too many snakes in the code! 🐍"
        ])

    if (
        "who are you" in lower
        or "what are you" in lower
    ):
        return (
            f"I'm {BOT_NAME}, your AI conversation partner and "
            f"student tutor. We can talk casually, or I can help "
            f"you with programming, DSA, AI, ML and many other topics."
        )

    if (
        "what is your name" in lower
        or "your name" in lower
    ):
        return (
            f"My name is {BOT_NAME}. "
            f"You can call me {BOT_NAME}. 😊"
        )

    if (
        "do you like me" in lower
    ):
        return (
            "I enjoy talking with you, and I'm always happy to "
            "continue our conversations. 😊"
        )

    if (
        "are you my friend" in lower
    ):
        return (
            "I'd be happy to be your friendly AI conversation partner. "
            "We can talk, learn things together, and keep our conversations going."
        )

    return None

def memory_response(text):

    lower = clean_text(text)

    if (
        "what is my name" in lower
        or "do you know my name" in lower
    ):
        if USER_NAME:
            return (
                f"Your name is {USER_NAME}. "
                f"You told me that earlier."
            )

        return (
            "You haven't told me your name yet. "
            "What should I call you?"
        )

    if (
        "what do you remember about me" in lower
        or "what do you know about me" in lower
        or "tell me about me" in lower
    ):
        details = []

        if USER_NAME:
            details.append(
                f"Your name is {USER_NAME}."
            )

        for key, value in MEMORY["facts"].items():
            details.append(
                f"{key.replace('_', ' ').title()}: {value}"
            )

        if MEMORY["hobbies"]:
            details.append(
                "Hobbies: "
                + ", ".join(
                    MEMORY["hobbies"]
                )
            )

        if MEMORY["interests"]:
            details.append(
                "Interests: "
                + ", ".join(
                    MEMORY["interests"]
                )
            )

        if MEMORY["goals"]:
            details.append(
                "Goals: "
                + ", ".join(
                    MEMORY["goals"]
                )
            )

        if MEMORY["favorites"]:
            for key, value in MEMORY["favorites"].items():
                details.append(
                    f"Favorite {key}: {value}"
                )

        if not details:
            return (
                "I don't know much about you yet. "
                "Let's get to know each other."
            )

        return (
            "Here's what I remember about you:\n"
            + "\n".join(
                "- " + item
                for item in details
            )
        )

    return None


# ============================================================
# NATURAL FOLLOW-UP ENGINE
# ============================================================

def conversation_follow_up(text):

    lower = clean_text(text)

    if (
        "student" in lower
        or "btech" in lower
        or "college" in lower
        or "studying" in lower
        or "study" in lower
    ):
        MEMORY["last_topic"] = "studies"
        save_memory()

        return random.choice([
            "Nice! What are you studying?",
            "That's interesting. Which subject do you enjoy the most?",
            "How are your studies going?",
            "What's the most interesting thing you're learning right now?"
        ])

    if (
        "python" in lower
        or "programming" in lower
        or "coding" in lower
    ):
        MEMORY["last_topic"] = "programming"
        save_memory()

        return random.choice([
            "Nice! What are you currently building with it?",
            "That's great. Which part of programming do you enjoy most?",
            "What programming problem are you working on these days?",
            "Are you learning programming for college, projects, "
            "placements, or just because you enjoy it?"
        ])

    if (
        "movie" in lower
        or "movies" in lower
        or "film" in lower
    ):
        MEMORY["last_topic"] = "movies"
        save_memory()

        return random.choice([
            "Nice! What kind of movies do you usually enjoy?",
            "What's the last movie you watched?",
            "Do you have a favorite actor or actress?",
            "Do you prefer action, comedy, romance, thriller, or something else?"
        ])

    if (
        "music" in lower
        or "song" in lower
        or "songs" in lower
    ):
        MEMORY["last_topic"] = "music"
        save_memory()

        return random.choice([
            "Nice! What kind of music do you usually listen to?",
            "Who's your favorite singer?",
            "What song have you been listening to recently?",
            "Do you prefer relaxing music or energetic songs?"
        ])

    if (
        "game" in lower
        or "gaming" in lower
    ):
        MEMORY["last_topic"] = "gaming"
        save_memory()

        return random.choice([
            "Nice! What games do you usually play?",
            "Are you more into mobile games or PC games?",
            "What's your favorite game?",
            "Do you play competitively or just for fun?"
        ])

    if (
        "travel" in lower
        or "trip" in lower
        or "place" in lower
    ):
        MEMORY["last_topic"] = "travel"
        save_memory()

        return random.choice([
            "Travel sounds fun! Where would you love to visit?",
            "What's the best place you've visited so far?",
            "Do you prefer mountains, beaches, cities, or peaceful places?",
            "If you could travel anywhere tomorrow, where would you go?"
        ])

    if (
        "future" in lower
        or "career" in lower
        or "job" in lower
        or "goal" in lower
        or "dream" in lower
    ):
        MEMORY["last_topic"] = "future"
        save_memory()

        return random.choice([
            "That's interesting. What kind of future do you imagine for yourself?",
            "What would you really like to achieve in the next few years?",
            "What's one big goal you're working toward right now?",
            "What kind of career would make you feel successful?"
        ])

    return None

def local_general_response(text):

    lower = clean_text(text)

    if (
        "time" in lower
        and (
            "what" in lower
            or "current" in lower
            or "now" in lower
        )
    ):
        return (
            f"The current local time is "
            f"{current_time()}."
        )

    if (
        "date" in lower
        or "today" in lower
        or "which day" in lower
    ):
        if (
            "today" in lower
            or "date" in lower
            or "day" in lower
        ):
            return (
                f"Today is {current_date()}."
            )

    if "calendar" in lower:
        return calendar_info()

    if (
        "where are you" in lower
        or "your location" in lower
    ):
        return (
            f"My configured location is "
            f"{LOCATION}."
        )

    result = extract_math(text)

    if result is not None:
        return (
            f"The answer is {result}."
        )

    return None

def should_search_web(text):

    lower = clean_text(text)

    words = [
        "current",
        "present",
        "latest",
        "today",
        "recent",
        "news",
        "now",
        "2026",
        "politics",
        "election",
        "minister",
        "chief minister",
        "president",
        "government",
        "festival",
        "weather",
        "live"
    ]

    return any(
        word in lower
        for word in words
    )


def web_search(query):

    if requests is None:
        return ""

    if BeautifulSoup is None:
        return ""

    try:
        url = (
            "https://html.duckduckgo.com/html/?q="
            + requests.utils.quote(query)
        )

        headers = {
            "User-Agent":
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/140.0 Safari/537.36"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=8
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        results = []

        for item in soup.select(
            ".result"
        )[:5]:

            title = item.select_one(
                ".result__title"
            )

            snippet = item.select_one(
                ".result__snippet"
            )

            if title and snippet:

                results.append(
                    title.get_text(
                        " ",
                        strip=True
                    )
                    + ": "
                    + snippet.get_text(
                        " ",
                        strip=True
                    )
                )

        return "\n".join(
            results
        )

    except Exception:
        return ""

def ai_response(question, web_context=""):

    if CLIENT is None:
        return None

    memory_summary = {
        "user_name": USER_NAME,
        "bot_name": BOT_NAME,
        "facts": MEMORY["facts"],
        "interests": MEMORY["interests"],
        "hobbies": MEMORY["hobbies"],
        "favorites": MEMORY["favorites"],
        "goals": MEMORY["goals"],
        "mood": MEMORY["mood"],
        "last_topic": MEMORY["last_topic"]
    }

    system_prompt = f"""
You are {BOT_NAME}, a friendly AI conversation partner
and student tutor.

The user's name is:
{USER_NAME if USER_NAME else "unknown"}

User memory:
{json.dumps(memory_summary, ensure_ascii=False)}

Your personality:
- Friendly
- Warm
- Natural
- Curious
- Respectful
- Patient
- Encouraging
- Intelligent
- Not robotic

Your main goal is to have a natural conversation.

If the user is casually talking:
- Respond naturally.
- Don't turn every message into a lesson.
- Ask a relevant follow-up question when appropriate.
- Don't ask a question after absolutely every sentence.
- Remember things the user told you.
- Connect new messages with previous information.
- Gradually become more comfortable and friendly.

If the user talks about:
- studies
- programming
- Python
- AI
- machine learning
- DSA
- projects
- career

then become a helpful tutor.

For technical questions:
- Explain clearly.
- Give examples.
- Give code when requested.
- Explain code.
- Include time and space complexity for DSA.
- Avoid unnecessary complexity for beginners.

If current web information is supplied, use it carefully.
Do not invent current facts.

Never claim to have real-world feelings or a physical life.
You can still communicate warmly and naturally.

Current web information:
{web_context if web_context else "None"}
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(
        CONVERSATION_HISTORY[-20:]
    )

    messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    try:
        response = CLIENT.responses.create(
            model=OPENAI_MODEL,
            input=messages
        )

        answer = (
            getattr(
                response,
                "output_text",
                ""
            )
            or ""
        ).strip()

        if not answer:
            return None

        CONVERSATION_HISTORY.append(
            {
                "role": "user",
                "content": question
            }
        )

        CONVERSATION_HISTORY.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        if len(CONVERSATION_HISTORY) > 40:
            del CONVERSATION_HISTORY[:-40]

        return answer

    except Exception:
        return None

def advanced_fallback(text):

    lower = clean_text(text)

    if MEMORY["last_topic"] == "studies":
        return random.choice([
            "That sounds interesting. What part of your studies do you enjoy most?",
            "How are you finding your studies so far?",
            "Is there any subject you're currently struggling with?",
            "Do you prefer learning by theory or by building projects?"
        ])

    if MEMORY["last_topic"] == "programming":
        return random.choice([
            "What are you building at the moment?",
            "What's the hardest programming problem you've faced recently?",
            "Do you enjoy solving coding problems or building projects more?",
            "What technology would you like to learn next?"
        ])

    if MEMORY["last_topic"] == "movies":
        return random.choice([
            "What movie would you recommend to me?",
            "Do you usually watch movies alone or with friends?",
            "What's a movie you can watch more than once?",
            "Do you prefer movies with a strong story or lots of action?"
        ])

    if MEMORY["last_topic"] == "music":
        return random.choice([
            "What song never gets boring for you?",
            "Do you listen to music while studying?",
            "Who's an artist you would recommend?"
        ])

    if MEMORY["last_topic"] == "gaming":
        return random.choice([
            "What's your favorite game?",
            "What makes that game fun for you?",
            "Do you play mostly for competition or relaxation?"
        ])

    if MEMORY["last_topic"] == "future":
        return random.choice([
            "That's something worth thinking about. "
            "What's one small step you could take toward that goal?",
            "I like that you're thinking about your future. "
            "What would you like to achieve first?",
            "What motivates you to pursue that goal?"
        ])

    if MEMORY["mood"] in {
        "sad",
        "negative",
        "stressed",
        "tired"
    }:
        return random.choice([
            "I understand. If you want, you can tell me more about what's going on.",
            "That sounds like a lot. What's been on your mind?",
            "Sometimes talking about it helps. What happened?"
        ])

    if MEMORY["hobbies"]:
        hobby = MEMORY["hobbies"][-1]

        return (
            f"You mentioned that you enjoy {hobby}. "
            f"How did you first get interested in it?"
        )

    if MEMORY["interests"]:
        interest = MEMORY["interests"][-1]

        return (
            f"You mentioned that you're interested in {interest}. "
            f"What do you like most about it?"
        )

    return random.choice([
        "That's interesting. Tell me more about that.",
        "I see. What happened next?",
        "Really? I'd like to know more about that.",
        "That sounds interesting. How did you get into it?",
        "I understand. What do you think about it?",
        "Nice! What made you feel that way?",
        "Tell me more. I'm listening.",
        "That's something worth talking about. What happened?"
    ])
def process_message(original_text):

    global BOT_NAME

    text = original_text.strip()

    if not text:
        return "I'm listening. Tell me something."

    MEMORY["message_count"] += 1

    # Bot name change
    response = change_bot_name(text)

    if response:
        return response

    # User name
    response = change_user_name(text)

    if response:
        return response

    # Remember information
    remember_user_information(text)
    detect_favorites(text)
    detect_mood(text)

    # Remove bot name when explicitly called
    if bot_is_called(text):
        text = remove_bot_name(text)

        if not text:
            return (
                f"Yes, I'm {BOT_NAME}. 😊 "
                f"What would you like to talk about?"
            )
    response = memory_response(text)

    if response:
        return response
    response = local_general_response(text)

    if response:
        return response

    # Friendly conversation
    response = friendly_response(text)

    if response:
        return response
    response = conversation_follow_up(text)

    if response:
        return response
    web_context = ""

    if should_search_web(text):
        web_context = web_search(text)

    response = ai_response(
        text,
        web_context
    )

    if response:
        return response

    return advanced_fallback(text)


def show_help():

    print()
    print("=" * 72)
    print("ADVANCED STUDENT AI CHATBOT")
    print("=" * 72)
    print()
    print("FRIENDLY CONVERSATION")
    print("  Hi")
    print("  How are you?")
    print("  I am feeling tired")
    print("  I am bored")
    print("  Tell me a joke")
    print("  I like movies")
    print("  I enjoy playing games")
    print()
    print("PERSONAL INFORMATION")
    print("  My name is Karthik")
    print("  I study B.Tech")
    print("  I am interested in AI")
    print("  My hobby is watching movies")
    print("  My favorite movie is Maharshi")
    print("  My goal is to become an AI engineer")
    print()
    print("BOT NAME")
    print("  Your name is Abhi")
    print("  Your name is Bhavishya")
    print("  Call yourself Jarvis")
    print("  Change your name to Friday")
    print()
    print("MEMORY")
    print("  What is my name?")
    print("  What do you remember about me?")
    print()
    print("STUDENT / TECHNICAL")
    print("  Explain Python")
    print("  Explain NumPy")
    print("  Explain Pandas")
    print("  Explain train_test_split")
    print("  Explain machine learning")
    print("  Explain linked list")
    print("  Explain Dijkstra")
    print()
    print("UTILITIES")
    print("  What is the time?")
    print("  What is today's date?")
    print("  Show calendar")
    print("  What is 30 into 2?")
    print()
    print("CURRENT INFORMATION")
    print("  Who is the present CM of Andhra Pradesh?")
    print("  What is the latest AI news?")
    print()
    print("COMMANDS")
    print("  help")
    print("  exit")
    print()
    print("=" * 72)
    print()

def show_status():

    print()
    print("=" * 60)
    print("CHATBOT STATUS")
    print("=" * 60)
    print(f"Bot name       : {BOT_NAME}")
    print(
        f"User name      : "
        f"{USER_NAME if USER_NAME else 'Not known'}"
    )
    print(f"Location       : {LOCATION}")
    print(
        f"AI API         : "
        f"{'Available' if CLIENT else 'Not available'}"
    )
    print(
        f"Messages       : "
        f"{MEMORY['message_count']}"
    )
    print(
        f"Last topic     : "
        f"{MEMORY['last_topic'] or 'None'}"
    )
    print(
        f"Mood           : "
        f"{MEMORY['mood'] or 'Unknown'}"
    )
    print("=" * 60)
    print()

def start_chat():

    print()
    print("=" * 72)
    print("              ADVANCED STUDENT AI CHATBOT")
    print("=" * 72)
    print()
    print(f"Bot name : {BOT_NAME}")
    print(f"Location : {LOCATION}")
    print(f"Date     : {current_date()}")
    print(f"Time     : {current_time()}")
    print()
    print(
        f"{BOT_NAME}: Hey! 😊 I'm {BOT_NAME}. "
        f"We can have a normal conversation, "
        f"get to know each other, or I can help "
        f"you with your studies."
    )
    print()
    print(
        "Type 'help' for examples."
    )
    print(
        "Type 'status' to see what I remember."
    )
    print(
        "Type 'exit' to close."
    )
    print()

    while True:

        try:
            user_input = input(
                "You: "
            ).strip()

        except KeyboardInterrupt:
            print()
            print(
                f"{BOT_NAME}: Goodbye! Take care. 😊"
            )
            break

        except EOFError:
            print()
            print(
                f"{BOT_NAME}: Goodbye!"
            )
            break

        if not user_input:
            print(
                f"{BOT_NAME}: I'm listening. 😊"
            )
            continue

        command = clean_text(
            user_input
        )

        if command in {
            "exit",
            "quit",
            "bye",
            "goodbye",
            "close",
            "stop"
        }:
            print()
            print(
                f"{BOT_NAME}: It was nice talking with you. "
                f"Take care! 😊"
            )
            break

        if command == "help":
            show_help()
            continue

        if command == "status":
            show_status()
            continue

        print()
        print(
            f"{BOT_NAME}: Thinking..."
        )

        response = process_message(
            user_input
        )

        print()
        print(
            f"{BOT_NAME}: {response}"
        )
        print()

        save_memory()


if __name__ == "__main__":
    start_chat()

