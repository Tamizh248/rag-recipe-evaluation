"""Capture the RAW JSON-RPC exchange (initialize -> tools/list -> tools/call)
against the NEW ingredient_db_server (Week 9, requirement 4) - talks
newline-delimited JSON-RPC directly over the subprocess's stdin/stdout,
bypassing the mcp SDK's ClientSession, so what's written to
evaluation/week9/wire.json is exactly what crossed the wire, byte for byte.

Usage:
    python scripts/capture_mcp_wire.py
"""
import json
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = BACKEND_DIR.parent / "evaluation" / "week9" / "wire.json"


def send(proc: subprocess.Popen, message: dict) -> None:
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def recv(proc: subprocess.Popen) -> dict:
    line = proc.stdout.readline()
    return json.loads(line)


def main() -> None:
    proc = subprocess.Popen(
        [sys.executable, "mcp_servers/ingredient_db_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(BACKEND_DIR),
        text=True,
        bufsize=1,
    )

    exchange = []

    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "week9-wire-capture", "version": "0.1"},
        },
    }
    send(proc, initialize_request)
    initialize_response = recv(proc)
    exchange.append({"direction": "client->server", "message": initialize_request})
    exchange.append({"direction": "server->client", "message": initialize_response})

    initialized_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    send(proc, initialized_notification)
    exchange.append({"direction": "client->server", "message": initialized_notification})

    tools_list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    send(proc, tools_list_request)
    tools_list_response = recv(proc)
    exchange.append({"direction": "client->server", "message": tools_list_request})
    exchange.append({"direction": "server->client", "message": tools_list_response})

    tools_call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "lookup_ingredient", "arguments": {"name": "walnuts"}},
    }
    send(proc, tools_call_request)
    tools_call_response = recv(proc)
    exchange.append({"direction": "client->server", "message": tools_call_request})
    exchange.append({"direction": "server->client", "message": tools_call_response})

    proc.terminate()
    proc.wait(timeout=5)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(exchange, indent=2), encoding="utf-8")

    print(json.dumps(exchange, indent=2))
    print(f"\nWritten to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
