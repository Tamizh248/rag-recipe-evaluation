"""The agent's ONLY way to discover or call a tool (Week 9) - a synchronous
facade over the real MCP protocol (initialize -> tools/list -> tools/call,
over stdio, one subprocess per configured server). Reads backend/
mcp_config.json for the list of servers to connect to; nothing in this
file or in app/agent/agent.py names a specific server - adding a server is
a config-only change (see evaluation/week9/agent_diff.txt).

A background thread owns one persistent asyncio event loop, and every
ClientSession lives for the process lifetime INSIDE one single long-running
task on that loop (_main, below) - not split across separate
run_until_complete()/run_coroutine_threadsafe() calls. anyio (which mcp is
built on) ties a session's internal task group to whichever task opened
it; calling into a session later from a DIFFERENT task raises "Attempted
to exit cancel scope in a different task than it was entered in". Each
call_tool() instead enqueues a request onto an asyncio.Queue that _main's
own loop consumes, so every session method call happens on the same task
that created the session.
"""

import asyncio
import concurrent.futures
import json
import sys
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CONFIG_PATH = Path(__file__).resolve().parents[2] / "mcp_config.json"
BACKEND_DIR = Path(__file__).resolve().parents[2]


@dataclass
class ToolInfo:
    name: str
    description: str
    server: str


class MCPClient:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._queue: asyncio.Queue | None = None
        self._tool_to_server: dict[str, str] = {}
        self._tools: list[ToolInfo] = []
        self._ready = threading.Event()
        self._start_error: BaseException | None = None

    def _ensure_started(self) -> None:
        if self._thread is not None:
            if self._start_error:
                raise self._start_error
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="mcp-client-loop")
        self._thread.start()
        self._ready.wait()
        if self._start_error:
            raise self._start_error

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        except BaseException as exc:  # noqa: BLE001
            self._start_error = exc
            self._ready.set()

    async def _main(self) -> None:
        """Everything - connect, serve every call for the process lifetime,
        disconnect - happens in this ONE task, so every session stays
        owned by the task that created it."""
        self._queue = asyncio.Queue()
        config = json.loads(self.config_path.read_text(encoding="utf-8"))

        async with AsyncExitStack() as stack:
            sessions: dict[str, ClientSession] = {}
            for server in config["servers"]:
                # "python" in config means "the SAME interpreter running this
                # process" (sys.executable), not whatever "python" resolves
                # to on PATH, which may not have this project's venv packages.
                command = sys.executable if server["command"] == "python" else server["command"]
                params = StdioServerParameters(command=command, args=server["args"], cwd=str(BACKEND_DIR))
                read, write = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                listing = await session.list_tools()
                for tool in listing.tools:
                    self._tool_to_server[tool.name] = server["name"]
                    self._tools.append(ToolInfo(name=tool.name, description=tool.description or "", server=server["name"]))
                sessions[server["name"]] = session

            self._ready.set()

            while True:
                name, arguments, future = await self._queue.get()
                asyncio.ensure_future(self._handle_call(sessions, name, arguments, future))

    async def _handle_call(
        self, sessions: dict[str, ClientSession], name: str, arguments: dict, future: concurrent.futures.Future
    ) -> None:
        try:
            server_name = self._tool_to_server.get(name)
            if server_name is None:
                future.set_result({"error": f"Unknown tool {name!r} - not discovered from any configured MCP server."})
                return
            result = await sessions[server_name].call_tool(name, arguments)
            text = result.content[0].text if result.content else ""
            if result.isError:
                future.set_result({"error": text})
                return
            try:
                future.set_result(json.loads(text))
            except (json.JSONDecodeError, TypeError):
                future.set_result({"result": text})
        except Exception as exc:  # noqa: BLE001
            future.set_result({"error": str(exc)})

    def list_tools(self) -> list[ToolInfo]:
        self._ensure_started()
        return list(self._tools)

    def call_tool(self, name: str, arguments: dict) -> dict:
        self._ensure_started()
        future: concurrent.futures.Future = concurrent.futures.Future()
        self._loop.call_soon_threadsafe(self._queue.put_nowait, (name, arguments, future))
        return future.result(timeout=30)


_default_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    global _default_client
    if _default_client is None:
        _default_client = MCPClient()
    return _default_client
