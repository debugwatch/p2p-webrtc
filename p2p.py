# /// script
# requires-python = ">=3.10"
# dependencies = ["aiortc>=1.9"]
# ///
"""Peer-to-peer chat over WebRTC. No server, just copy-paste two tokens.

Both machines run the SAME command:

  uvx --from git+<repo-url> connect   (or: uv run <raw-url> connect)

Your role is inferred from whether you have a token:
  - Machine A: press Enter to start  -> prints an OFFER token
  - Machine B: paste A's OFFER        -> prints an ANSWER token
  - Machine A: paste the ANSWER       -> connected

Tokens are plain text; send them over any chat/email. Once both say
[connected], type a line and press Enter to send it to the other side.
"""
import asyncio
import base64
import json
import os
import sys
import time
import zlib

from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription

CFG = RTCConfiguration([RTCIceServer(urls="stun:stun.l.google.com:19302")])

_T0 = time.monotonic()
_QUIET = os.environ.get("P2P_QUIET")


def log(*parts):
    if not _QUIET:
        print(f"[{time.monotonic() - _T0:6.2f}s] [p2p]", *parts, file=sys.stderr, flush=True)


def watch(pc):
    """Log WebRTC state changes to stderr so the handshake is visible."""
    @pc.on("signalingstatechange")
    def _():
        log("signaling state:", pc.signalingState)

    @pc.on("icegatheringstatechange")
    def _():
        log("ICE gathering:", pc.iceGatheringState)

    @pc.on("iceconnectionstatechange")
    def _():
        log("ICE connection:", pc.iceConnectionState)

    @pc.on("connectionstatechange")
    def _():
        log("peer connection:", pc.connectionState)


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
        log(f"send: {len(msg.encode())} bytes over data channel")


async def be_offerer(pc):
    """No token in hand: create the offer, then wait for the peer's answer."""
    log("no token -> you are the offerer (starting a new connection)")
    channel = pc.createDataChannel("chat")
    opened = asyncio.Event()

    @channel.on("open")
    def _():
        log("data channel open")
        opened.set()

    @channel.on("message")
    def _(m):
        log(f"recv: {len(m.encode()) if isinstance(m, str) else len(m)} bytes over data channel")
        print(f"< {m}", flush=True)

    log("creating offer and gathering ICE candidates...")
    await pc.setLocalDescription(await pc.createOffer())
    emit("OFFER", enc(pc.localDescription))
    desc = await prompt_token("Paste the ANSWER token, then Enter:", "ANSWER")
    if desc is None:
        sys.exit("No answer given.")
    log("got ANSWER; applying it and starting ICE/DTLS handshake...")
    await pc.setRemoteDescription(desc)
    await opened.wait()
    await chat(channel)


async def be_answerer(pc, offer_token):
    """Token in hand (the peer's offer): produce an answer and connect."""
    log("token provided -> you are the answerer (joining an existing connection)")
    ready = asyncio.get_running_loop().create_future()

    @pc.on("datachannel")
    def _(channel):
        log("data channel received from peer")

        @channel.on("message")
        def _(m):
            log(f"recv: {len(m.encode()) if isinstance(m, str) else len(m)} bytes over data channel")
            print(f"< {m}", flush=True)

        def done():
            log("data channel open")
            if not ready.done():
                ready.set_result(channel)
        if channel.readyState == "open":
            done()
        else:
            channel.on("open", done)

    try:
        desc = dec(offer_token)
    except Exception:
        desc = await prompt_token("That wasn't a valid OFFER token. Paste it again, then Enter:", "OFFER")
        if desc is None:
            sys.exit("No offer given.")
    await pc.setRemoteDescription(desc)
    log("got OFFER; creating answer and gathering ICE candidates...")
    await pc.setLocalDescription(await pc.createAnswer())
    emit("ANSWER", enc(pc.localDescription))
    print("Send the ANSWER back, then wait for the other machine to connect...", flush=True)
    await chat(await ready)


async def connect():
    """One command for both peers: your role is decided by whether you have a token.
    Press Enter to start a connection (offerer), or paste the peer's OFFER (answerer)."""
    pc = RTCPeerConnection(CFG)
    watch(pc)
    token = await line(
        "Paste the peer's OFFER token to join, or press Enter to start a new connection:")
    if not token:
        await be_offerer(pc)
    else:
        await be_answerer(pc, token)


def run(coro):
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        sys.exit(130)


def connect_cmd():
    run(connect())


def main():
    args = sys.argv[1:]
    if args and args[0] != "connect":
        sys.exit("usage: p2p [connect]")
    run(connect())


if __name__ == "__main__":
    main()
