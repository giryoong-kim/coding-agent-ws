#!/usr/bin/env python3
"""MCP JSON-RPC 2.0 server wrapping the cost_analyzer module."""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.environ.get("COST_ANALYZER_DIR", os.path.dirname(os.path.abspath(__file__))))
import cost_analyzer

SERVER_NAME = "cost_analyzer"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"


def make_response(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def make_error(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle_initialize(id_, _params):
    return make_response(id_, {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        "capabilities": {"tools": {}},
    })


def handle_tools_list(id_, _params):
    return make_response(id_, {"tools": cost_analyzer.list_tools()})


def handle_tools_call(id_, params):
    name = params.get("name")
    arguments = params.get("arguments") or {}

    try:
        result = cost_analyzer.dispatch(name, arguments)
    except cost_analyzer.UnknownResourceError:
        return make_error(id_, -32601, f"Unknown tool: {name!r}")
    except (ValueError, TypeError) as exc:
        return make_error(id_, -32602, str(exc))

    return make_response(id_, {
        "content": [{"type": "text", "text": json.dumps(result)}],
        "isError": False,
    })


METHODS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


class MCPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            request = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            resp = make_error(None, -32700, "Parse error")
            self._send_json(resp)
            return

        id_ = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        handler = METHODS.get(method)
        if handler is None:
            resp = make_error(id_, -32601, f"Unknown method: {method!r}")
        else:
            resp = handler(id_, params)

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
    parser = argparse.ArgumentParser(description="MCP server for cost_analyzer")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", "9000")))
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MCPHandler)
    print(f"{SERVER_NAME} v{SERVER_VERSION} listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()