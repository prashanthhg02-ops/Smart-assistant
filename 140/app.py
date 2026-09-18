from __future__ import annotations

import datetime as dt
import json
import re
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parent
AIML_FILE = ROOT / "aiml" / "brain.aiml"
STATIC_FILE = ROOT / "static" / "index.html"


def normalize(text: str) -> str:
    return re.sub(r"\\s+", " ", text.strip().upper())


def safe_math(expression: str) -> str | None:
    expression = expression.strip()
    if not re.fullmatch(r"[0-9+\-*/(). %]+", expression):
        return None
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        if isinstance(result, (int, float)) and abs(result) < 10**12:
            return str(round(result, 8)).rstrip("0").rstrip(".")
    except (ArithmeticError, SyntaxError, TypeError, ValueError):
        return None
    return None


class AimlKernel:
    def __init__(self, path: Path):
        self.categories: list[tuple[re.Pattern[str], str, str | None]] = []
        self._load(path)

    def _load(self, path: Path) -> None:
        tree = ET.parse(path)
        for category in tree.findall(".//category"):
            pattern_node = category.find("pattern")
            template_node = category.find("template")
            if pattern_node is None or template_node is None:
                continue
            pattern = normalize("".join(pattern_node.itertext()))
            template = "".join(template_node.itertext()).strip()
            redirect = template_node.find("redirect")
            redirect_pattern = normalize("".join(redirect.itertext())) if redirect is not None else None
            regex = re.escape(pattern).replace(r"\*", "(.*)")
            self.categories.append((re.compile(r"^" + regex + r"$", re.IGNORECASE), template, redirect_pattern))

    def respond(self, message: str) -> str:
        normalized = normalize(message)
        for regex, template, redirect in self.categories:
            match = regex.match(normalized)
            if not match:
                continue
            if redirect:
                return self._resolve_redirect(redirect)
            response = template
            stars = match.groups()
            for index, value in enumerate(stars, start=1):
                response = response.replace("{" + str(index) + "}", value.strip())
            return self._dynamic(response, stars)
        return "I do not know that one yet. Add a category to aiml/brain.aiml and teach me a new answer."

    def _resolve_redirect(self, pattern: str) -> str:
        for regex, template, redirect in self.categories:
            if regex.match(pattern):
                return self._dynamic(template, regex.match(pattern).groups() if regex.match(pattern) else ())
        return "I am still learning that response."

    def _dynamic(self, response: str, stars: tuple[str, ...]) -> str:
        now = dt.datetime.now()
        response = response.replace("{TIME}", now.strftime("%I:%M %p").lstrip("0"))
        response = response.replace("{DATE}", now.strftime("%A, %B %d, %Y").replace(" 0", " "))
        if response.startswith("{CALC}"):
            answer = safe_math(stars[0] if stars else "")
            return answer if answer is not None else "I could not safely calculate that. Try something like 12 * 4."
        return response


kernel = AimlKernel(AIML_FILE)


class AssistantHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", STATIC_FILE.read_bytes())
        else:
            self._send(404, "application/json", b'{"error":"Not found"}')

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self._send(404, "application/json", b'{"error":"Not found"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            message = str(payload.get("message", ""))[:500]
            if not message.strip():
                raise ValueError("Message is empty")
            answer = kernel.respond(message)
            self._send(200, "application/json; charset=utf-8", json.dumps({"reply": answer}).encode())
        except (ValueError, json.JSONDecodeError):
            self._send(400, "application/json", b'{"error":"Please send a non-empty message."}')

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), AssistantHandler)
    print("Smart AIML Assistant running at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop.")
    try:
        threading.Timer(0.4, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nAssistant stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
