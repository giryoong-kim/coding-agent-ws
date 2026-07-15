"""Remote MCP server exposing cost_analyzer tools over HTTP JSON-RPC.

Uses only the Python standard library. Start with:
    python3 mcp_server.py --port 9000
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from http.server import HTTPServer

sys.path.insert(0, os.environ.get("COST_ANALYZER_DIR", os.path.dirname(os.path.abspath(__file__))))
import cost_analyzer


SERVER_NAME = "cost-analyzer-mcp"
SERVER_VERSION = "1.0.0"


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MCPHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self._send_json_response(200, {
            "status": "ok",
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
        })

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            self._send_jsonrpc_error(None, -32700, "Parse error")
            return

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "initialize":
            self._send_result(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            })
        elif method == "tools/list":
            tools = cost_analyzer.list_tools()
            self._send_result(req_id, {"tools": tools})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                result = cost_analyzer.dispatch(tool_name, arguments)
                self._send_result(req_id, {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": False,
                })
            except (ValueError, TypeError) as exc:
                self._send_jsonrpc_error(req_id, -32602, str(exc))
        else:
            self._send_jsonrpc_error(req_id, -32601, f"Method not found: {method!r}")

    def _send_result(self, req_id, result):
        self._send_json_response(200, {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        })

    def _send_jsonrpc_error(self, req_id, code, message):
        self._send_json_response(200, {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        })

    def _send_json_response(self, status, obj):
        payload = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def main():
    default_port = int(os.environ.get("MCP_PORT", "9000"))

    parser = argparse.ArgumentParser(description="Cost Analyzer MCP Server")
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MCPHandler)
    print(f"MCP server listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()