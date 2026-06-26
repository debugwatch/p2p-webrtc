# p2p

Peer-to-peer chat over WebRTC with copy-paste signaling. No server, no accounts —
two machines exchange two short text tokens and talk directly.

## Use it (no clone, no install)

You only need [uv](https://docs.astral.sh/uv/). **Both machines run the same
command** — your role is inferred from whether you have a token:
```
uvx --from git+https://github.com/debugwatch/p2p-webrtc connect
```

1. **Machine A** presses **Enter** to start → prints an **OFFER** token. Send it to B.
2. **Machine B** pastes the OFFER → prints an **ANSWER** token. Send that back to A.
3. **Machine A** pastes the ANSWER into its waiting prompt.

Both sides print `[connected]` — type a line, press Enter, and it appears on the
other machine prefixed with `<`.

## Run straight from the URL (no clone, no build)

`uv run` executes the single file directly from its raw URL (it installs the
inline `aiortc` dependency automatically):
```
uv run https://raw.githubusercontent.com/debugwatch/p2p-webrtc/main/p2p.py connect
```
`main` serves the latest commit; put a commit SHA in place of `main` to pin a version.

## Notes

- Tokens are plain ASCII (gzip + url-safe base64); move them over any chat or email.
- The peer who started (the offerer) must stay running until connected — its keys
  and sockets live in memory.
- Uses a public STUN server. If **both** peers are behind strict/symmetric NATs the
  connection may never complete; that case needs a TURN relay.
- Progress logs (ICE/DTLS/data-channel state) print to **stderr**; set `P2P_QUIET=1`
  to silence them. They don't interfere with the tokens or chat on stdout.
