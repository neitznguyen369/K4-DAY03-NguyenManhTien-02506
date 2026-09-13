"""Web interface for the ReAct QC assistant."""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import run_react_agent, save_waterfall_trace
from mcp_server import MCPAcademicServer
from providers import get_llm_provider


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "web")
ENV_PATH = os.path.join(BASE_DIR, ".env")
provider = None
provider_config = None
provider_lock = threading.Lock()
mcp_server = MCPAcademicServer()


def get_runtime_provider():
    """Reload provider configuration when .env changes during server runtime."""
    global provider, provider_config
    with provider_lock:
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        current_config = (
            os.getenv("LLM_PROVIDER", "gemini").lower(),
            os.getenv("GEMINI_API_KEY", ""),
            os.getenv("OPENAI_API_KEY", ""),
            os.getenv("LLM_MODEL", ""),
        )
        if provider is None or current_config != provider_config:
            provider = get_llm_provider()
            provider_config = current_config
            print(f"[config] Provider updated: {provider.__class__.__name__}")
        return provider


class QCWebHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename, content_type):
        path = os.path.join(STATIC_DIR, filename)
        try:
            with open(path, "rb") as file:
                body = file.read()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send_file("index.html", "text/html; charset=utf-8")
        elif path == "/styles.css":
            self._send_file("styles.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self._send_file("app.js", "text/javascript; charset=utf-8")
        elif path == "/api/health":
            active_provider = get_runtime_provider()
            tools = mcp_server.list_tools()
            self._send_json({
                "status": "ok",
                "provider": active_provider.__class__.__name__,
                "mcp": {"status": "online", "tools": len(tools)},
            })
        else:
            self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/chat":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) or b"{}"
            try:
                body = raw_body.decode("utf-8")
            except UnicodeDecodeError:
                body = raw_body.decode("cp1258")
            payload = json.loads(body)
            question = str(payload.get("question", "")).strip()
            if not question:
                self._send_json({"error": "Vui lòng nhập câu hỏi."}, 400)
                return
            trace = run_react_agent(question, get_runtime_provider(), mcp_server)
            save_waterfall_trace(trace, append=True)
            self._send_json({"question": question, "trace": trace})
        except Exception as error:
            self._send_json({"error": str(error)}, 500)

    def log_message(self, format, *args):
        print(f"[web] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    active_provider = get_runtime_provider()
    port = int(os.getenv("WEB_PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), QCWebHandler)
    print(f"QC ReAct Studio: http://127.0.0.1:{port}")
    print(f"Provider: {active_provider.__class__.__name__}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng QC ReAct Studio.")
    finally:
        server.server_close()