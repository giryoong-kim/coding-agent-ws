#!/usr/bin/env python3
"""MCP server wrapping cost_analyzer as a JSON-RPC 2.0 HTTP endpoint.

Built for the AgentCore Runtime harness. Python stdlib only.
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.environ.get("COST_ANALYZER_DIR", os.path.dirname(os.path.abspath(__file__))))
import cost_analyzer

SERVER_NAME = "cost-analyzer-mcp"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"


def _jsonrpc_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(req_id, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def handle_initialize(req_id, _params):
    return _jsonrpc_response(req_id, {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        "capabilities": {"tools": {}},
    })


def handle_tools_list(req_id, _params):
    tools = cost_analyzer.list_tools()
    return _jsonrpc_response(req_id, {"tools": tools})


def handle_tools_call(req_id, params):
    name = params.get("name") if params else None
    arguments = params.get("arguments") if params else None

    if not name or name not in [t["name"] for t in cost_analyzer.TOOL_SPECS]:
        return _jsonrpc_error(req_id, -32601, f"Unknown tool: {name!r}")

    try:
        result = cost_analyzer.dispatch(name, arguments)
    except (ValueError, TypeError) as exc:
        return _jsonrpc_error(req_id, -32602, str(exc))

    return _jsonrpc_response(req_id, {
        "content": [{"type": "text", "text": json.dumps(result)}],
        "isError": False,
    })


METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


class MCPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)

        try:
            request = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            resp = _jsonrpc_error(None, -32700, "Parse error")
            self._send_json(resp)
            return

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params")

        handler = METHOD_HANDLERS.get(method)
        if handler is None:
            resp = _jsonrpc_error(req_id, -32601, f"Method not found: {method!r}")
        else:
            resp = handler(req_id, params)

        self._send_json(resp)

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="cost-analyzer-mcp JSON-RPC server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", "9000")))
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MCPRequestHandler)
    print(f"{SERVER_NAME} v{SERVER_VERSION} listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()