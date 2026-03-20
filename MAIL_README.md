# Mesh Mail Bot

This branch now contains a **mail-only Meshtastic DM bot**.

All public board/BBS features were removed from `bbs.py`. The bot now supports private mail by device identifier only.

## Security model

- `mail check` only shows mail where `to == FROM_NODE`.
- `mail delete` only allows deletion by the intended receiver.
- `mail purge` requires the configured admin override password.
- Responses are always DM/private replies.

## Commands

All commands are sent in DM and start with `mail`.

- `mail send <to_device_id> <message>`  
  Send private mail to a specific device id.

- `mail check`  
  Show only messages addressed to your device id.

- `mail delete <mail_id>`  
  Delete a message only if your device id is the intended receiver.

- `mail purge <admin_pw>`  
  Admin failsafe to purge all mail.

- `mail help`  
  Show help.

- `mail more`  
  Continue paginated output when a response exceeds message size limits.

## Storage

Files are stored under `/data/bbs`:

- `mail.json` — private mail items
- `pending.json` — pagination state for `mail more`

## Admin override password

Configured in `bbs.py`:

- `OVERRIDE_PASSWORD = "meshadmin"`
