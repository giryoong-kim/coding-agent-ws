"""MCP server wrapping cost_analyzer as a JSON-RPC 2.0 HTTP service."""

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


class MCPHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

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
            self._send_error(None, -32700, "Parse error")
            return

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params") or {}

        if method == "initialize":
            self._send_result(req_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {"tools": {}},
            })
        elif method == "tools/list":
            tools = cost_analyzer.list_tools()
            self._send_result(req_id, {"tools": tools})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments") or {}
            try:
                result = cost_analyzer.dispatch(tool_name, arguments)
                self._send_result(req_id, {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": False,
                })
            except cost_analyzer.UnknownResourceError:
                self._send_error(req_id, -32601, f"Unknown tool or resource: {tool_name}")
            except (ValueError, TypeError) as exc:
                self._send_error(req_id, -32602, str(exc))
        else:
            self._send_error(req_id, -32601, f"Unknown method: {method}")

    def _send_result(self, req_id, result):
        resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
        self._write_json(resp)

    def _send_error(self, req_id, code, message):
        resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
        self._write_json(resp)

    def _write_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="MCP server for cost_analyzer")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", "9000")))
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MCPHandler)
    print(f"{SERVER_NAME} v{SERVER_VERSION} listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()