#!/usr/bin/env python3
"""MCP server for cost_analyzer — JSON-RPC 2.0 over HTTP."""

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
            self._send_json({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            return

        req_id = request.get("id")
        method = request.get("method", "")

        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {"tools": {}},
            }
            self._send_json({"jsonrpc": "2.0", "id": req_id, "result": result})

        elif method == "tools/list":
            tools = cost_analyzer.list_tools()
            self._send_json({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}})

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            known_tools = {t["name"] for t in cost_analyzer.list_tools()}
            if tool_name not in known_tools:
                self._send_json({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                })
                return

            try:
                result = cost_analyzer.dispatch(tool_name, arguments)
                self._send_json({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False,
                    },
                })
            except (ValueError, TypeError) as exc:
                self._send_json({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": str(exc)},
                })

        else:
            self._send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
            })

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