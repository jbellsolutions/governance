# Slack ↔ Paperclip — talk to your CEO from Slack

The relay (`python main.py --slack-relay`, `integrations/slack_paperclip.py`) lets you converse
with your CEO agent (and team) from Slack. Inbound uses a slash command; outbound posts the agents'
replies into a channel. This is the **only** Slack integration in this repo — there was previously
a second, overlapping implementation (`integrations/slack_bridge.py`'s own webhook server); that's
been retired. `slack_bridge.py` now only provides low-level Slack-posting helpers this relay uses
internally.

## What you get

- `/ceo <message>` in Slack → posted to the CEO's "Owner channel" issue, which wakes the CEO.
- The CEO's reply (and other agent messages on that thread) → posted back into your Slack channel.
- One channel per business; multiple businesses each relay to their own CEO.
- Every inbound request is signature-verified (Slack's HMAC scheme) — the relay refuses to start
  without `SLACK_SIGNING_SECRET` set, and rejects any request that doesn't verify.

## 1. Create the Slack app from the manifest

1. Go to https://api.slack.com/apps → **Create New App** → **From an app manifest**.
2. Pick your workspace, paste the contents of **`integrations/slack-manifest.yaml`**, review, create.
   This wires the bot scopes and both slash commands (`/ceo`, `/team`) in one step — no manual
   OAuth-scope clicking or slash-command form-filling.
3. If your board isn't at `https://137-184-151-136.sslip.io`, edit the two `url` fields in the
   manifest to your actual public host *before* pasting it in.
4. **Install to Workspace** → copy the **Bot User OAuth Token** (`xoxb-…`) → set `SLACK_BOT_TOKEN`.
5. **Basic Information** → **App Credentials** → copy the **Signing Secret** → set
   `SLACK_SIGNING_SECRET`.
6. Invite the bot to your channel: in Slack, `/invite @Governance CEO` in `#governance`.

## 2. Wire the public endpoint

Slack needs a public HTTPS URL to reach the relay's slash-command receiver (default `:3001`). If
your Paperclip board already terminates TLS behind nginx (as `deploy-vps.sh` sets up), add one more
location block reusing the same cert — no new domain needed:

```nginx
location /slack/ {
    proxy_pass http://127.0.0.1:3001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Then `nginx -t && systemctl reload nginx`. For local testing without nginx, expose the port with a
tunnel (`cloudflared` or `ngrok`) and point the manifest's URLs at that instead.

## 3. Configure the relay

Set in `.env` (or company secrets):

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...                # from Basic Information — required, not optional
SLACK_OWNER_CHANNEL=#governance
PAPERCLIP_API_URL=http://localhost:3000
PAPERCLIP_API_KEY=<board key>          # board key with read + comment
SLACK_RELAY_PORT=3001
```

## 4. Run it

```bash
python main.py --slack-relay
```

On a VPS deployed via `scripts/deploy-vps.sh`, this runs as the `governance-slack.service` systemd
unit — it's enabled automatically once `SLACK_BOT_TOKEN` is set in the deploy env.

Then in Slack: `/ceo what's our pipeline look like?` — the CEO wakes, works, and its reply lands in
`#governance`.

## Agents sending Slack messages themselves

Separately, agents can *send* Slack messages via the Integrations sidecar's `slack` specialist
(Composio). Connect Slack in Composio and set `COMPOSIO_API_KEY`; then a skill can call
`POST $INTEGRATIONS_URL/delegate` with `specialist_type: "slack"`. The relay above is specifically
for the **owner ↔ CEO conversation**; the Composio path is for agents posting notifications/updates.
