# MeshMonitor-BBS

MeshMonitor-BBS is a lightweight **Meshtastic DM bulletin board system** script designed for low-bandwidth LoRa networks.

It runs as a command handler (`bbs.py`) and stores state in JSON files under `/data/bbs`.

## Trigger Setup

<img width="1664" height="259" alt="image" src="https://github.com/user-attachments/assets/febeb663-f811-4810-9d9a-fbba11298e63" />


## What it does

- Creates named message boards.
- Lets users post and read board messages.
- Supports paginated replies with `bbs more` for clients that can only receive one response at a time.
- Enforces short responses suitable for LoRa payload limits (target: 180 chars per response chunk).
- Allows board-level passwords (optional).
- Lets users delete their own posts.
- Allows board owners to delete empty boards.
- Supports static override password for admin deletes.

## Data files

The script uses these files under `/data/bbs`:

- `boards.json` — board definitions (owner + optional password)
- `posts.json` — all posts
- `pending.json` — per-user pagination state for `bbs more`

Static admin override password:

- `meshadmin` (configured in `bbs.py` as `OVERRIDE_PASSWORD`)

## Command reference

All commands are sent as a DM message starting with `bbs`.

### Core

- `bbs help`  
  Show command help.

- `bbs boards`  
  List boards (`🔒` means password-protected).

### Boards

- `bbs create <name>`  
  Create a public board.

- `bbs create <name> <password>`  
  Create a password-protected board.

### Posting

- `bbs post <board> <message>`  
  Post on a public board. Use `subject | message` format.

- `bbs post <board> <password> <message>`  
  Post on a protected board. Use `subject | message` format.

### Reading

- `bbs read <board>`  
  If one post exists, it is shown. If multiple posts exist, you'll get IDs to choose from.

- `bbs read <board> <password>`  
  Same behavior for protected boards (list/select when multiple posts).

- `bbs read <board> <post_id>`  
  Read one post on a public board.

- `bbs read <board> <password> <post_id>`  
  Read one post on a protected board.

### Deleting

- `bbs del <post_id>`
- `bbs delete <post_id>`  
  Delete your own post only.

- `bbs del <post_id> <override_password>`  
  Delete any post when override password is configured and valid.

- `bbs delboard <board>`  
  Delete a board only if you are the owner and it is empty.

- `bbs delboard <board> <override_password>`  
  Force delete a board (and its posts) with override password.

### Pagination

- `bbs more`  
  Get the next page when a reply is split.

## Example flow

```text
bbs create general
bbs post general hello | mesh test message
bbs read general

bbs create ops s3cret
bbs post ops s3cret maint | scheduled maintenance at 0300z
bbs read ops s3cret

bbs del 12
```

## Notes

- Message and board names are case-normalized to lowercase.
- Replies are private DM responses.
- If there are no remaining pages, `bbs more` returns “No more messages.”
