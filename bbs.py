#!/usr/bin/env python3
# mm_meta:
#   name: Mesh DM BBS
#   emoji: 📡

import os
import json
import pathlib

DATA = "/data/bbs"
pathlib.Path(DATA).mkdir(parents=True, exist_ok=True)

MAIL_DB = f"{DATA}/mail.json"
BOARDS_DB = f"{DATA}/boards.json"
POSTS_DB = f"{DATA}/posts.json"


# -----------------------------
# Utilities
# -----------------------------

def load(path):
    if not os.path.exists(path):
        return {}
    return json.load(open(path))


def save(path, data):
    json.dump(data, open(path, "w"))


def dm(text):
    """Send DM ONLY to command sender"""
    print(json.dumps({
        "response": text[:200],
        "private": True
    }))
    exit()


def dm_multi(messages):
    """Send multiple DM messages"""
    print(json.dumps({
        "responses": messages
    }))
    exit()


sender = os.getenv("FROM_NODE", "unknown")
message = os.getenv("MESSAGE", "").strip()

parts = message.split()
if not parts:
    dm("Empty command.")

cmd = parts[0].lower()

mail = load(MAIL_DB)
boards = load(BOARDS_DB)
posts = load(POSTS_DB)

# =====================================================
# MAIL SYSTEM (DM ONLY)
# =====================================================

if cmd == "mail":

    if len(parts) < 2:
        dm("mail send|inbox|read|delete")

    action = parts[1].lower()

    # ---------------- SEND ----------------
    if action == "send":

        if len(parts) < 4:
            dm("Usage: mail send <node> <message>")

        target = parts[2]
        text = " ".join(parts[3:])

        mid = str(len(mail) + 1)

        mail[mid] = {
            "to": target,
            "from": sender,
            "text": text
        }

        save(MAIL_DB, mail)

        dm_multi([
            {
                "response": "✓ Mail sent.",
                "private": True
            },
            {
                "to": target,
                "response": f"📬 New mail from {sender}",
                "private": True
            }
        ])

    # ---------------- INBOX ----------------
    elif action == "inbox":

        msgs = [
            f'{mid}:{m["text"][:40]}'
            for mid, m in mail.items()
            if m["to"] == sender
        ]

        if not msgs:
            dm("Inbox empty.")

        dm("Inbox: " + " | ".join(msgs[:5]))

    # ---------------- READ ----------------
    elif action == "read":

        if len(parts) < 3:
            dm("Usage: mail read <id>")

        mid = parts[2]

        if mid not in mail or mail[mid]["to"] != sender:
            dm("Message not found.")

        m = mail[mid]

        dm(f'From {m["from"]}: {m["text"]}')

    # ---------------- DELETE ----------------
    elif action == "delete":

        if len(parts) < 3:
            dm("Usage: mail delete <id>")

        mid = parts[2]

        if mid in mail and mail[mid]["to"] == sender:
            del mail[mid]
            save(MAIL_DB, mail)
            dm("Mail deleted.")

        dm("Cannot delete.")

# =====================================================
# BBS SYSTEM (DM RESPONSES ONLY)
# =====================================================

elif cmd == "bbs":

    if len(parts) < 2:
        dm("bbs boards|create|post|read")

    action = parts[1].lower()

    # ---------------- LIST BOARDS ----------------
    if action == "boards":

        if not boards:
            dm("No boards exist.")

        dm("Boards: " + ", ".join(boards.keys()))

    # ---------------- CREATE BOARD ----------------
    elif action == "create":

        if len(parts) < 3:
            dm("Usage: bbs create <name>")

        name = parts[2]

        boards[name] = {"owner": sender}
        save(BOARDS_DB, boards)

        dm(f"Board '{name}' created.")

    # ---------------- POST ----------------
    elif action == "post":

        if len(parts) < 4:
            dm("Usage: bbs post <board> <text>")

        board = parts[2]
        text = " ".join(parts[3:])

        if board not in boards:
            dm("Board not found.")

        pid = str(len(posts) + 1)

        posts[pid] = {
            "board": board,
            "author": sender,
            "text": text
        }

        save(POSTS_DB, posts)

        dm(f"Post #{pid} added.")

    # ---------------- READ BOARD ----------------
    elif action == "read":

        if len(parts) < 3:
            dm("Usage: bbs read <board>")

        board = parts[2]

        msgs = [
            f'{pid}:{p["text"][:40]}'
            for pid, p in posts.items()
            if p["board"] == board
        ]

        if not msgs:
            dm("No posts.")

        dm("Posts: " + " | ".join(msgs[:5]))

# =====================================================

dm("Unknown command.")
