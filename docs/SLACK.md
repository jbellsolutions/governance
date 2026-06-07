# Slack ↔ Paperclip — talk to your CEO from Slack

The relay (`python main.py --slack-relay`) lets you converse with your CEO agent (and team) from
Slack. Inbound uses a slash command; outbound posts the agents' replies into a channel.

## What you get

- `/ceo <message>` in Slack → posted to the CEO's "Owner channel" issue, which wakes the CEO.
- The CEO's reply (and other agent messages on that thread) → posted back into your Slack channel.
- One channel per business; multiple businesses each relay to their own CEO.

## 1. Create a Slack app

1. Go to https://api.slack.com/apps → **Create New App** → *From scratch*.
2. **OAuth & Permissions** → Bot Token Scopes: add `chat:write`, `commands`, `channels:read`.
3. **Install to Workspace** → copy the **Bot User OAuth Token** (`xoxb-…`) → set `SLACK_BOT_TOKEN`.
4. Invite the bot to your channel: in Slack, `/invite @YourBot` in `#governance` (or your channel).

## 2. Add the slash command

1. **Slash Commands** → **Create New Command**:
   - Command: `/ceo`
   - Request URL: `https://<your-domain>/slack/commands` (the relay's port, default `:3001`)
   - Short description: `Message your CEO agent`
2. (Optional) repeat for `/team`.

If running behind nginx, proxy `/slack/commands` to `127.0.0.1:3001`. For local testing, expose the
port with a tunnel (e.g. `cloudflared` or `ngrok`) and use that URL.

## 3. Configure the relay

Set in `.env` (or company secrets):

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_OWNER_CHANNEL=#governance
PAPERCLIP_API_URL=http://localhost:3000
PAPERCLIP_API_KEY=<board key>          # board key with read + comment
SLACK_RELAY_PORT=3001
```

## 4. Run it

```bash
python main.py --slack-relay
```

Then in Slack: `/ceo what's our pipeline look like?` — the CEO wakes, works, and its reply lands in
`#governance`.

## Agents sending Slack messages themselves

Separately, agents can *send* Slack messages via the Integrations sidecar's `slack` specialist
(Composio). Connect Slack in Composio and set `COMPOSIO_API_KEY`; then a skill can call
`POST $INTEGRATIONS_URL/delegate` with `specialist_type: "slack"`. The relay above is specifically
for the **owner ↔ CEO conversation**; the Composio path is for agents posting notifications/updates.
