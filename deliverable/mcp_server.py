#!/usr/bin/env python3
"""JSON-RPC 2.0 MCP server for critter_lab over HTTP."""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.environ.get("COST_ANALYZER_DIR", os.path.dirname(os.path.abspath(__file__))))
import critter_lab  # noqa: E402

SERVER_NAME = "critter_lab"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"


def _jsonrpc_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _jsonrpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def handle_request(body):
    try:
        req = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return _jsonrpc_error(None, -32700, "Parse error")

    req_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params") or {}

    if method == "initialize":
        return _jsonrpc_result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "capabilities": {"tools": {}},
        })

    if method == "tools/list":
        return _jsonrpc_result(req_id, {"tools": critter_lab.list_tools()})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            result = critter_lab.dispatch(tool_name, arguments)
        except critter_lab.UnknownToolError:
            return _jsonrpc_error(req_id, -32601, f"Unknown tool: {tool_name}")
        except (ValueError, TypeError) as exc:
            return _jsonrpc_error(req_id, -32602, str(exc))
        return _jsonrpc_result(req_id, {
            "content": [{"type": "text", "text": json.dumps(result)}],
            "isError": False,
        })

    return _jsonrpc_error(req_id, -32601, f"Unknown method: {method}")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = json.dumps({"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        response = handle_request(body)
        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="MCP server for critter_lab")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", "9000")))
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"{SERVER_NAME} v{SERVER_VERSION} listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()