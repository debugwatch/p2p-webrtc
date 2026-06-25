# /// script
# requires-python = ">=3.10"
# dependencies = ["aiortc>=1.9"]
# ///
"""Peer-to-peer chat over WebRTC. No server, just copy-paste two tokens.

  Machine A:  uvx --from git+<repo-url> create   # prints an OFFER token
  Machine B:  uvx --from git+<repo-url> answer   # paste OFFER -> prints an ANSWER token
  Machine A:  paste the ANSWER when asked        # -> connected

Tokens are plain text; send them over any chat/email. Once both say
[connected], type a line and press Enter to send it to the other side.
"""
import asyncio
import base64
import json
import sys
import zlib

from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription

CFG = RTCConfiguration([RTCIceServer(urls="stun:stun.l.google.com:19302")])


def enc(d):
    # SDP is verbose plain text -> gzip it before base64 to keep the token short.
    raw = json.dumps({"sdp": d.sdp, "type": d.type}).encode()
    return base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode()


def dec(blob):
    raw = zlib.decompress(base64.urlsafe_b64decode(blob.strip()))
    d = json.loads(raw)
    return RTCSessionDescription(sdp=d["sdp"], type=d["type"])


async def prompt_token(prompt, kind):
    """Ask for a token, re-prompting on bad input. Returns None on EOF."""
    while True:
        blob = await line(prompt)
        if blob is None:
            return None
        if not blob:
            continue  # empty line — just ask again
        try:
            return dec(blob)
        except Exception:
            print(
                f"That doesn't look like a valid {kind} token. "
                "Copy the whole line (it's long) and paste it again.\n",
                flush=True,
            )


async def line(prompt=None):
    if prompt:
        print(prompt, flush=True)
    text = await asyncio.get_running_loop().run_in_executor(None, sys.stdin.readline)
    return None if text == "" else text.strip()  # "" means EOF (stdin closed)


def emit(label, token):
    print(f"\n----- {label} (send this to the other machine) -----", flush=True)
    print(token, flush=True)
    print(f"----- end {label} -----\n", flush=True)


async def chat(channel):
    print("[connected] type a message and press Enter to send\n", flush=True)
    while True:
        msg = await line()
        if msg is None:  # stdin closed
            break
        channel.send(msg)


async def create():
    pc = RTCPeerConnection(CFG)
    channel = pc.createDataChannel("chat")
    opened = asyncio.Event()
    channel.on("open", opened.set)
    channel.on("message", lambda m: print(f"< {m}", flush=True))

    await pc.setLocalDescription(await pc.createOffer())
    emit("OFFER", enc(pc.localDescription))
    desc = await prompt_token("Paste the ANSWER token, then Enter:", "ANSWER")
    if desc is None:
        sys.exit("No answer given.")
    await pc.setRemoteDescription(desc)
    await opened.wait()
    await chat(channel)


async def answer():
    pc = RTCPeerConnection(CFG)
    ready = asyncio.get_running_loop().create_future()

    @pc.on("datachannel")
    def _(channel):
        channel.on("message", lambda m: print(f"< {m}", flush=True))
        done = lambda: None if ready.done() else ready.set_result(channel)
        if channel.readyState == "open":
            done()
        else:
            channel.on("open", done)

    desc = await prompt_token("Paste the OFFER token, then Enter:", "OFFER")
    if desc is None:
        sys.exit("No offer given.")
    await pc.setRemoteDescription(desc)
    await pc.setLocalDescription(await pc.createAnswer())
    emit("ANSWER", enc(pc.localDescription))
    print("Send the ANSWER back, then wait for the other machine to connect...", flush=True)
    await chat(await ready)


def run(coro):
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        sys.exit(130)


def create_cmd():
    run(create())


def answer_cmd():
    run(answer())


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "create":
        create_cmd()
    elif cmd == "answer":
        answer_cmd()
    else:
        sys.exit("usage: p2p create | p2p answer")


if __name__ == "__main__":
    main()
