# p2p

Peer-to-peer chat over WebRTC with copy-paste signaling. No server, no accounts —
two machines exchange two short text tokens and talk directly.

## Use it (no clone, no install)

You only need [uv](https://docs.astral.sh/uv/).

**Machine A:**
```
uvx --from git+https://github.com/debugwatch/p2p-webrtc create
```
Prints an **OFFER** token. Send it to machine B.

**Machine B:**
```
uvx --from git+https://github.com/debugwatch/p2p-webrtc answer
```
Paste the OFFER when asked; it prints an **ANSWER** token. Send that back to A.

**Machine A:** paste the ANSWER into the waiting prompt.

Both sides print `[connected]` — type a line, press Enter, and it appears on the
other machine prefixed with `<`.

## Run straight from the URL (no clone, no build)

`uv run` executes the single file directly from its raw URL (it installs the
inline `aiortc` dependency automatically):
```
uv run https://raw.githubusercontent.com/debugwatch/p2p-webrtc/main/p2p.py create
uv run https://raw.githubusercontent.com/debugwatch/p2p-webrtc/main/p2p.py answer
```
`main` serves the latest commit; put a commit SHA in place of `main` to pin a version.

## Notes

- Tokens are plain ASCII (gzip + url-safe base64); move them over any chat or email.
- `create` must stay running until connected — its keys and sockets live in memory.
- Uses a public STUN server. If **both** peers are behind strict/symmetric NATs the
  connection may never complete; that case needs a TURN relay.
- Progress logs (ICE/DTLS/data-channel state) print to **stderr**; set `P2P_QUIET=1`
  to silence them. They don't interfere with the tokens or chat on stdout.
