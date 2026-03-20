#!/usr/bin/env python3
# mm_meta:
#   name: Mesh DM BBS V.5
#   emoji: 📡

import json
import os
import pathlib

DATA = "/data/bbs"
pathlib.Path(DATA).mkdir(parents=True, exist_ok=True)

BOARDS_DB = f"{DATA}/boards.json"
POSTS_DB = f"{DATA}/posts.json"
PENDING_DB = f"{DATA}/pending.json"

MAX_LEN = 180  # Keep payload under the LoRa message size target
MORE_PROMPT = "\n\n(Type: bbs more)"


# -----------------------------
# Utilities
# -----------------------------

def load(path):
    if not os.path.exists(path):
        return {}
    return json.load(open(path))


def save(path, data):
    json.dump(data, open(path, "w"))


def header(title):
    return f"📡 MESH BBS — {title}\n"


def send_private(text):
    print(json.dumps({"response": text, "private": True}))
    exit()


# -----------------------------
# Paging Functions
# -----------------------------

def chunk_text(text, limit):
    """Split text into chunks <= limit, handling long unbroken strings."""
    chunks = []
    current = ""

    for part in text.split("\n"):
        piece = part if not current else f"\n{part}"

        if len(piece) <= limit and len(current) + len(piece) <= limit:
            current += piece
            continue

        if current:
            chunks.append(current)
            current = ""

        while len(part) > limit:
            chunks.append(part[:limit])
            part = part[limit:]

        current = part

    if current:
        chunks.append(current)

    return chunks or [""]


def dm_chunked(sender, text):
    """Send first chunk and store remaining pages per user."""
    first_limit = MAX_LEN - len(MORE_PROMPT)
    chunks = chunk_text(text, first_limit)

    pending[sender] = chunks[1:]
    save(PENDING_DB, pending)

    first = chunks[0]
    if pending[sender]:
        first += MORE_PROMPT

    send_private(first)


# -----------------------------
# Help Text
# -----------------------------

def help_text():
    return (
        header("Help")
        + "Commands:\n\n"
        + "bbs boards\n"
        + "List boards\n\n"
        + "bbs create <name> [pw]\n"
        + "Create board (optional password)\n\n"
        + "bbs post <board> <msg>\n"
        + "Post on public board\n\n"
        + "bbs post <board> <pw> <msg>\n"
        + "Post on protected board\n\n"
        + "bbs read <board> [pw]\n"
        + "Read posts\n\n"
        + "bbs del <post_id>\n"
        + "Delete your post\n\n"
        + "bbs more\n"
        + "Continue msg"
    )


# -----------------------------
# Environment
# -----------------------------

sender = os.getenv("FROM_NODE", "unknown")
message = os.getenv("MESSAGE", "").strip()

parts = message.split()
if not parts:
    pending = load(PENDING_DB)
    dm_chunked(sender, header("Error") + "Empty command.\nType: bbs help")

cmd = parts[0].lower()

boards = load(BOARDS_DB)
posts = load(POSTS_DB)
pending = load(PENDING_DB)

# Clear stale pagination state unless user asked for more.
if not (cmd == "bbs" and len(parts) > 1 and parts[1].lower() == "more"):
    if sender in pending and pending[sender]:
        pending[sender] = []
        save(PENDING_DB, pending)


# =====================================================
# BBS SYSTEM
# =====================================================

if cmd == "bbs":
    # ---------------- MORE (pagination) ----------------
    if len(parts) > 1 and parts[1].lower() == "more":
        if sender not in pending or not pending[sender]:
            dm_chunked(sender, header("Info") + "No more messages.")

        next_limit = MAX_LEN - len(MORE_PROMPT)
        next_page = pending[sender].pop(0)
        save(PENDING_DB, pending)

        if len(next_page) > next_limit:
            rest = chunk_text(next_page, next_limit)
            next_page = rest[0]
            pending[sender] = rest[1:] + pending[sender]
            save(PENDING_DB, pending)

        if pending[sender]:
            next_page += MORE_PROMPT

        send_private(next_page)

    # ---------------- ROOT HELP ----------------
    if len(parts) == 1:
        dm_chunked(
            sender,
            header("Welcome")
            + "Type: bbs help\n"
            + "to see commands.\n"
            + "Please be patient. This is slow.",
        )

    action = parts[1].lower()

    # ---------------- HELP ----------------
    if action == "help":
        dm_chunked(sender, help_text())

    # ---------------- LIST BOARDS ----------------
    elif action == "boards":
        if not boards:
            dm_chunked(
                sender,
                header("Boards") + "No boards yet.\nCreate one with:\nbbs create general",
            )

        board_list = "\n".join(
            f"• {name}{' 🔒' if meta.get('password') else ''}" for name, meta in boards.items()
        )
        dm_chunked(
            sender,
            header("Boards") + board_list + "\n\nRead with:\nbbs read <board> [pw]",
        )

    # ---------------- CREATE BOARD ----------------
    elif action == "create":
        if len(parts) < 3:
            dm_chunked(sender, header("Create Board") + "Usage:\nbbs create <name> [password]")

        name = parts[2].lower()
        password = parts[3] if len(parts) > 3 else ""

        if name in boards:
            dm_chunked(sender, header("Create Board") + "Board already exists.")

        boards[name] = {"owner": sender, "password": password}
        save(BOARDS_DB, boards)

        protection = "protected" if password else "public"
        dm_chunked(
            sender,
            header("Success")
            + f"Board '{name}' created ({protection}).\n\n"
            + "Post using:\n"
            + (f"bbs post {name} <pw> hello mesh" if password else f"bbs post {name} hello mesh"),
        )

    # ---------------- POST ----------------
    elif action == "post":
        if len(parts) < 4:
            dm_chunked(sender, header("Post Message") + "Usage:\nbbs post <board> <message>")

        board = parts[2].lower()
        if board not in boards:
            dm_chunked(sender, header("Error") + "Board not found.\nTry: bbs boards")

        board_pw = boards[board].get("password", "")
        if board_pw:
            if len(parts) < 5:
                dm_chunked(
                    sender,
                    header("Post Message") + f"Board '{board}' is protected.\nUsage:\nbbs post {board} <pw> <message>",
                )
            supplied_pw = parts[3]
            if supplied_pw != board_pw:
                dm_chunked(sender, header("Error") + "Wrong board password.")
            text = " ".join(parts[4:])
        else:
            text = " ".join(parts[3:])

        pid = str(max([int(k) for k in posts.keys()], default=0) + 1)
        posts[pid] = {"board": board, "author": sender, "text": text}
        save(POSTS_DB, posts)
        dm_chunked(
            sender,
            header("Post Added") + f"Saved as #{pid} in '{board}'.\n\nRead posts:\nbbs read {board}",
        )

    # ---------------- READ BOARD ----------------
    elif action == "read":
        if len(parts) < 3:
            dm_chunked(sender, header("Read Board") + "Usage:\nbbs read <board> [password]")

        board = parts[2].lower()
        if board not in boards:
            dm_chunked(sender, header("Error") + "Board not found.")

        board_pw = boards[board].get("password", "")
        supplied_pw = parts[3] if len(parts) > 3 else ""
        if board_pw and supplied_pw != board_pw:
            dm_chunked(
                sender,
                header("Read Board") + f"Board '{board}' is protected.\nUsage:\nbbs read {board} <pw>",
            )

        msgs = [
            f'#{pid} {p["author"]}: {p["text"]}'
            for pid, p in posts.items()
            if p["board"] == board
        ]
        if not msgs:
            dm_chunked(
                sender,
                header(board.upper()) + f"No posts yet.\nBe first:\nbbs post {board} hello mesh",
            )

        output = header(f"Board: {board}") + "\n".join(msgs[-10:])
        dm_chunked(sender, output)

    # ---------------- DELETE OWN POST ----------------
    elif action in ("del", "delete"):
        if len(parts) < 3:
            dm_chunked(sender, header("Delete") + "Usage:\nbbs del <post_id>")

        pid = parts[2]
        if pid not in posts:
            dm_chunked(sender, header("Delete") + "Post not found.")

        if posts[pid].get("author") != sender:
            dm_chunked(sender, header("Delete") + "You can only delete your own posts.")

        board = posts[pid].get("board", "?")
        del posts[pid]
        save(POSTS_DB, posts)
        dm_chunked(sender, header("Deleted") + f"Removed post #{pid} from '{board}'.")

# =====================================================

dm_chunked(sender, header("Unknown Command") + "Type: bbs help")
