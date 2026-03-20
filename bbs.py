#!/usr/bin/env python3
# mm_meta:
#   name: Mesh Mail Bot
#   emoji: ✉️

import json
import os
import pathlib

DATA = "/data/bbs"
pathlib.Path(DATA).mkdir(parents=True, exist_ok=True)

MAIL_DB = f"{DATA}/mail.json"
PENDING_DB = f"{DATA}/pending.json"

MAX_LEN = 180  # Keep payload under LoRa-friendly size target
MORE_PROMPT = "\n\n(Type: mail more)"
OVERRIDE_PASSWORD = "meshadmin"  # Static admin override password


def load(path):
    if not os.path.exists(path):
        return {}
    return json.load(open(path))


def save(path, data):
    json.dump(data, open(path, "w"))


def header(title):
    return f"✉️ MESH MAIL — {title}\n"


def send_private(text):
    print(json.dumps({"response": text, "private": True}))
    exit()


def is_override_password(pw):
    return bool(OVERRIDE_PASSWORD) and pw == OVERRIDE_PASSWORD


def chunk_text(text, limit):
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
    first_limit = MAX_LEN - len(MORE_PROMPT)
    chunks = chunk_text(text, first_limit)

    pending[sender] = chunks[1:]
    save(PENDING_DB, pending)

    first = chunks[0]
    if pending[sender]:
        first += MORE_PROMPT

    send_private(first)


def help_text():
    return (
        header("Help")
        + "mail send <to_device_id> <message>\n"
        + "mail check\n"
        + "mail delete <mail_id>\n"
        + "mail purge <admin_pw>\n"
        + "mail more"
    )


sender = os.getenv("FROM_NODE", "unknown")
message = os.getenv("MESSAGE", "").strip()
parts = message.split()

mail = load(MAIL_DB)
pending = load(PENDING_DB)

if not parts:
    dm_chunked(sender, help_text())

cmd = parts[0].lower()

# Clear stale pagination state unless user asked for more.
if not (cmd == "mail" and len(parts) > 1 and parts[1].lower() == "more"):
    if sender in pending and pending[sender]:
        pending[sender] = []
        save(PENDING_DB, pending)

if cmd != "mail":
    dm_chunked(sender, header("Unknown Command") + "Use: mail help")

if len(parts) == 1:
    dm_chunked(sender, help_text())

action = parts[1].lower()

if action == "help":
    dm_chunked(sender, help_text())

elif action == "more":
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

elif action == "send":
    if len(parts) < 4:
        dm_chunked(sender, header("Send") + "Usage:\nmail send <to_device_id> <message>")

    recipient = parts[2]
    text = " ".join(parts[3:])

    if not recipient.strip():
        dm_chunked(sender, header("Send") + "Recipient device id is required.")

    if recipient == sender:
        dm_chunked(sender, header("Send") + "Cannot send mail to your own device id.")

    if not text.strip():
        dm_chunked(sender, header("Send") + "Message cannot be empty.")

    mail_id = str(max([int(k) for k in mail.keys()], default=0) + 1)
    mail[mail_id] = {
        "from": sender,
        "to": recipient,
        "text": text,
    }
    save(MAIL_DB, mail)

    dm_chunked(sender, header("Sent") + f"Queued mail #{mail_id} for {recipient}.")

elif action == "check":
    inbox = [(mid, item) for mid, item in mail.items() if item.get("to") == sender]

    if not inbox:
        dm_chunked(sender, header("Inbox") + "No mail for your device id.")

    lines = [
        f"#{mid} from {item.get('from', '?')}: {item.get('text', '')}"
        for mid, item in sorted(inbox, key=lambda x: int(x[0]))
    ]

    dm_chunked(
        sender,
        header("Inbox") + "\n".join(lines) + "\n\nDelete one:\nmail delete <mail_id>",
    )

elif action in ("delete", "del"):
    if len(parts) < 3:
        dm_chunked(sender, header("Delete") + "Usage:\nmail delete <mail_id>")

    mail_id = parts[2]
    if mail_id not in mail:
        dm_chunked(sender, header("Delete") + "Mail not found.")

    if mail[mail_id].get("to") != sender:
        dm_chunked(sender, header("Delete") + "Only the intended receiver can delete this mail.")

    del mail[mail_id]
    save(MAIL_DB, mail)
    dm_chunked(sender, header("Delete") + f"Deleted mail #{mail_id}.")

elif action == "purge":
    if len(parts) < 3:
        dm_chunked(sender, header("Purge") + "Usage:\nmail purge <admin_pw>")

    supplied_pw = parts[2]
    if not is_override_password(supplied_pw):
        dm_chunked(sender, header("Purge") + "Invalid admin password.")

    count = len(mail)
    mail = {}
    save(MAIL_DB, mail)
    dm_chunked(sender, header("Purge") + f"Purged {count} mail item(s).")

else:
    dm_chunked(sender, header("Unknown Command") + "Use: mail help")
