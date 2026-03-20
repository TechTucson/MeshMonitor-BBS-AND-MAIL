#!/usr/bin/env python3
# mm_meta:
#   name: Mesh DM BBS V.5
#   emoji: 📡

import os
import json
import pathlib

DATA = "/data/bbs"
pathlib.Path(DATA).mkdir(parents=True, exist_ok=True)

BOARDS_DB = f"{DATA}/boards.json"
POSTS_DB = f"{DATA}/posts.json"
PENDING_DB = f"{DATA}/pending.json"

MAX_LEN = 180  # Safe LoRa payload length


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


# -----------------------------
# Paging Functions
# -----------------------------

def dm_chunked(sender, text):
    """Send first chunk and store remaining pages per user"""

    # Split text into lines and make chunks <= MAX_LEN
    lines = text.split("\n")
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > MAX_LEN:
            chunks.append(current)
            current = line
        else:
            current += "\n" + line if current else line

    if current:
        chunks.append(current)

    # Store remaining pages
    pending[sender] = chunks[1:]
    save(PENDING_DB, pending)

    # Send first page + prompt if more exist
    first = chunks[0]
    if pending[sender]:
        first += "\n\n(Type: bbs more)"
    print(json.dumps({
        "response": first,
        "private": True
    }))
    exit()


# -----------------------------
# Help Text
# -----------------------------

def help_text():
    return (
        header("Help") +
        "Commands:\n\n"
        "bbs boards\n"
        "List boards\n\n"
        "bbs create <name>\n"
        "Create new board\n\n"
        "bbs post <board> <msg>\n"
        "Add post\n\n"
        "bbs read <board>\n"
        "See posts\n\n"
        " bbs more\n"
        "Continue msg"
    )


# -----------------------------
# Environment
# -----------------------------

sender = os.getenv("FROM_NODE", "unknown")
message = os.getenv("MESSAGE", "").strip()

parts = message.split()
if not parts:
    dm_chunked(sender, header("Error") + "Empty command.\nType: bbs help")

cmd = parts[0].lower()

boards = load(BOARDS_DB)
posts = load(POSTS_DB)
pending = load(PENDING_DB)

# =====================================================
# BBS SYSTEM
# =====================================================

if cmd == "bbs":

    # ---------------- MORE (pagination) ----------------
    if len(parts) > 1 and parts[1].lower() == "more":
        if sender not in pending or not pending[sender]:
            dm_chunked(sender, header("Info") + "No more messages.")
        # pop next page
        next_page = pending[sender].pop(0)
        save(PENDING_DB, pending)
        # append prompt if still more
        if pending[sender]:
            next_page += "\n\n(Type: bbs more)"
        print(json.dumps({
            "response": next_page,
            "private": True
        }))
        exit()

    # ---------------- ROOT HELP ----------------
    if len(parts) == 1:
        dm_chunked(sender,
            header("Welcome") +
            "Type: bbs help\n"
            "to see commands.\n"
	    "Please be patient. This is slow."
        )

    action = parts[1].lower()

    # ---------------- HELP ----------------
    if action == "help":
        dm_chunked(sender, help_text())

    # ---------------- LIST BOARDS ----------------
    elif action == "boards":
        if not boards:
            dm_chunked(sender,
                header("Boards") +
                "No boards yet.\n"
                "Create one with:\n"
                "bbs create general"
            )
        board_list = "\n".join(f"• {b}" for b in boards.keys())
        dm_chunked(sender,
            header("Boards") +
            board_list +
            "\n\nRead with:\n"
            "bbs read <board>"
        )

    # ---------------- CREATE BOARD ----------------
    elif action == "create":
        if len(parts) < 3:
            dm_chunked(sender,
                header("Create Board") +
                "Usage:\n"
                "bbs create <name>"
            )
        name = parts[2].lower()
        if name in boards:
            dm_chunked(sender, header("Create Board") + "Board already exists.")
        boards[name] = {"owner": sender}
        save(BOARDS_DB, boards)
        dm_chunked(sender,
            header("Success") +
            f"Board '{name}' created.\n\n"
            f"Post using:\n"
            f"bbs post {name} hello mesh"
        )

    # ---------------- POST ----------------
    elif action == "post":
        if len(parts) < 4:
            dm_chunked(sender,
                header("Post Message") +
                "Usage:\n"
                "bbs post <board> <message>"
            )
        board = parts[2].lower()
        text = " ".join(parts[3:])
        if board not in boards:
            dm_chunked(sender, header("Error") + "Board not found.\nTry: bbs boards")
        pid = str(len(posts) + 1)
        posts[pid] = {
            "board": board,
            "author": sender,
            "text": text
        }
        save(POSTS_DB, posts)
        dm_chunked(sender,
            header("Post Added") +
            f"Saved as #{pid} in '{board}'.\n\n"
            f"Read posts:\n"
            f"bbs read {board}"
        )

    # ---------------- READ BOARD ----------------
    elif action == "read":
        if len(parts) < 3:
            dm_chunked(sender,
                header("Read Board") +
                "Usage:\n"
                "bbs read <board>"
            )
        board = parts[2].lower()
        if board not in boards:
            dm_chunked(sender, header("Error") + "Board not found.")
        msgs = [
            f'#{pid} {p["author"]}: {p["text"]}'
            for pid, p in posts.items()
            if p["board"] == board
        ]
        if not msgs:
            dm_chunked(sender,
                header(board.upper()) +
                "No posts yet.\n"
                f"Be first:\n"
                f"bbs post {board} hello mesh"
            )
        output = header(f"Board: {board}") + "\n".join(msgs[-10:])
        dm_chunked(sender, output)

# =====================================================

dm_chunked(sender, header("Unknown Command") + "Type: bbs help")
