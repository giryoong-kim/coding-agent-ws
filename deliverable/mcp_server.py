#!/usr/bin/env python3
"""MCP server for cost_analyzer: JSON-RPC 2.0 over HTTP."""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.environ.get("COST_ANALYZER_DIR", os.path.dirname(os.path.abspath(__file__))))
import cost_analyzer

SERVER_NAME = "cost_analyzer"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


class MCPHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        body = json.dumps({"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION}).encode("utf-8")
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
            self._send_error(None, -32700, "Parse error")
            return

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {"tools": {}},
            }
            self._send_result(req_id, result)

        elif method == "tools/list":
            tools = cost_analyzer.list_tools()
            self._send_result(req_id, {"tools": tools})

        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments") or {}
            try:
                result = cost_analyzer.dispatch(name, arguments)
            except cost_analyzer.UnknownResourceError as exc:
                self._send_error(req_id, -32601, str(exc))
                return
            except (ValueError, TypeError) as exc:
                self._send_error(req_id, -32602, str(exc))
                return
            self._send_result(req_id, {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "isError": False,
            })

        else:
            self._send_error(req_id, -32601, f"Unknown method: {method!r}")

    def _send_result(self, req_id, result):
        payload = {"jsonrpc": "2.0", "id": req_id, "result": result}
        self._write_json(payload)

    def _send_error(self, req_id, code, message):
        payload = {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
        self._write_json(payload)

    def _write_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
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