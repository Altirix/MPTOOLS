#!/usr/bin/env python3
"""Call a REA MCP tool over plain HTTP (no MCP client needed).

  rea_call.py --list [substr]            list tools
  rea_call.py <tool> '<json args>'       call a tool, print its result
  rea_call.py --rizin <sample> '<cmds>'  execute_rizin_command, print stdout (cli endpoint)

The agent proxy adds auth. Endpoint: see README.md (override with REA_MCP_URL).

Each call starts a fresh REA session unless REA_SESSION names a file: the
session id is kept there, so open_binary and Ghidra's analysis survive across
calls (one file per agent). A closed session (404) is replaced transparently,
but its open target is gone: open_binary again.
"""
import json, os, sys, urllib.error, urllib.request

# --rizin goes to the cli endpoint (rizin/objdump/firmware/process tools only), a separate REA
# process that runs beside an open Ghidra session; its session id is kept in <REA_SESSION>.cli
CLI = len(sys.argv) > 1 and sys.argv[1] == "--rizin"
URL = (os.environ.get("REA_CLI_URL", "https://mcp.peacocks.me/rea/mptools/cli/mcp") if CLI
       else os.environ.get("REA_MCP_URL", "https://mcp.peacocks.me/rea/mptools/mcp"))
SAMPLES = "/var/lib/rea/mptools/samples/"
sid = None

def rpc(method, params=None, id_=1):
    global sid
    body = {"jsonrpc": "2.0", "method": method}
    if id_ is not None: body["id"] = id_
    if params is not None: body["params"] = params
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if sid: h["Mcp-Session-Id"] = sid
    r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode(), h), timeout=600)
    sid = r.headers.get("Mcp-Session-Id") or sid
    out = None
    for line in r.read().decode().splitlines():
        if line.startswith("data:"): out = json.loads(line[5:])
    return out

def call(tool, args):
    res = rpc("tools/call", {"name": tool, "arguments": args}, 2)
    return res.get("result", res)

def connect():
    global sid
    sid = None
    rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "rea_call", "version": "1"}})
    rpc("notifications/initialized", id_=None)
    if SESSION_FILE:
        with open(SESSION_FILE, "w") as f: f.write(sid)

SESSION_FILE = os.environ.get("REA_SESSION")
if SESSION_FILE and CLI:
    SESSION_FILE += ".cli"
if SESSION_FILE and os.path.exists(SESSION_FILE):
    sid = open(SESSION_FILE).read().strip()
    try:
        rpc("ping", {}, 0)
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
        sys.stderr.write("rea_call: session closed, opened a new one (open_binary again)\n")
        connect()
else:
    connect()

if sys.argv[1] == "--list":
    for t in rpc("tools/list", {}, 2)["result"]["tools"]:
        if len(sys.argv) < 3 or sys.argv[2] in t["name"]: print(t["name"])
elif sys.argv[1] == "--rizin":
    r = call("execute_rizin_command", {"path": SAMPLES + sys.argv[2], "command": "e scr.color=0; " + sys.argv[3]})
    out = json.loads(r["content"][0]["text"])
    if "raw_result" not in out: sys.exit(json.dumps(out.get("error", out)))
    raw = out["raw_result"]
    sys.stdout.write(raw["stdout"]); sys.stderr.write(raw["stderr"])
else:
    for c in call(sys.argv[1], json.loads(sys.argv[2])).get("content", []): print(c.get("text", c))
