"""Bounded, retrying HTTP transport for soccer acquisition and verification.

Standard library only. Every physical request is charged against a ``Budget``
and recorded in its history, so a failure on a later page still leaves the
attempted-query trail behind for diagnostics.

Limits (also documented in docs/SOCCER_FRESHNESS.md):

* ``MAX_ATTEMPTS_PER_URL`` = 4 physical requests for one URL.
* Backoff between attempts: 1 s, doubling, capped at 20 s, with +/-25 % jitter.
* ``Retry-After`` is honoured when present (seconds or HTTP-date), capped at 60 s.
* Retryable: incomplete/truncated bodies, timeouts, connection resets and
  refusals, DNS/transient socket errors, empty bodies, HTTP 408/425/429/500/502/503/504.
* Not retried: any other HTTP 4xx (401/403/404/410 ...), TLS verification
  failures, and complete responses that fail to parse (``InvalidResponse``).
* A budget bounds the total number of physical requests and the total elapsed
  wall-clock time for a whole stage, independent of per-URL attempts, so nested
  retries can never multiply into an unbounded request count.

TLS verification stays on: ``urllib.request.urlopen`` is used with its default
verifying SSL context and no override is offered here.
"""
import json
import random
import socket
import ssl
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException, IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

MAX_ATTEMPTS_PER_URL = 4
BACKOFF_BASE_S = 1.0
BACKOFF_FACTOR = 2.0
BACKOFF_CAP_S = 20.0
RETRY_AFTER_CAP_S = 60.0
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
USER_AGENT = "sports-intel-spine/soccer-refresh (+https://github.com/calenb2/sports-intel-spine)"
SECRET_QUERY_KEYS = ("token", "key", "apikey", "api_key", "signature", "sig", "secret",
                     "password", "auth", "access_token", "x-apisports-key")


class TransportError(Exception):
    """A request could not be completed within the configured bounds."""

    def __init__(self, message, *, category, url, attempts, history, last_error=None):
        super().__init__(message)
        self.category = category          # transport | http_permanent | budget | tls
        self.url = url
        self.attempts = attempts
        self.history = history
        self.last_error = last_error


class InvalidResponse(ValueError):
    """A complete response was received but its content is unusable."""


def sanitize_url(url):
    """Drop credentials and secret-looking query values before logging a URL."""
    parts = urlsplit(url)
    netloc = parts.netloc.rsplit("@", 1)[-1]
    query = [(k, "REDACTED" if k.lower() in SECRET_QUERY_KEYS else v)
             for k, v in parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit((parts.scheme, netloc, parts.path, urlencode(query), ""))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Budget:
    """Shared request/time budget for one stage of the refresh."""

    def __init__(self, max_requests, max_elapsed_s, clock=time.monotonic):
        if max_requests < 1 or max_elapsed_s <= 0:
            raise ValueError("Budget must allow at least one request and positive time")
        self.max_requests = max_requests
        self.max_elapsed_s = float(max_elapsed_s)
        self.clock = clock
        self.started = clock()
        self.requests = 0
        self.history = []

    def elapsed(self):
        return self.clock() - self.started

    def remaining_time(self):
        return self.max_elapsed_s - self.elapsed()

    def charge(self, url, attempt):
        """Reserve one physical request; raise before issuing it if out of budget."""
        if self.requests >= self.max_requests:
            raise TransportError(
                f"Request budget of {self.max_requests} physical requests exhausted",
                category="budget", url=sanitize_url(url), attempts=attempt - 1,
                history=self.history)
        if self.remaining_time() <= 0:
            raise TransportError(
                f"Elapsed-time budget of {self.max_elapsed_s:.0f}s exhausted",
                category="budget", url=sanitize_url(url), attempts=attempt - 1,
                history=self.history)
        self.requests += 1

    def record(self, **entry):
        entry.setdefault("at", utc_now())
        self.history.append(entry)
        return entry

    def summary(self):
        return {"physical_requests": self.requests, "max_requests": self.max_requests,
                "elapsed_s": round(self.elapsed(), 3), "max_elapsed_s": self.max_elapsed_s,
                "attempt_history": list(self.history)}


def _retry_after_seconds(headers):
    value = headers.get("Retry-After") if headers is not None else None
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        seconds = (when - datetime.now(timezone.utc)).total_seconds()
    return max(0.0, min(seconds, RETRY_AFTER_CAP_S))


def _backoff(attempt, jitter):
    delay = min(BACKOFF_BASE_S * (BACKOFF_FACTOR ** (attempt - 1)), BACKOFF_CAP_S)
    return delay * jitter()


def _is_tls_failure(exc):
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, (ssl.SSLCertVerificationError, ssl.CertificateError)) or (
        isinstance(reason, ssl.SSLError) and "CERTIFICATE" in str(reason).upper())


def _classify(exc):
    """Return (retryable, label, retry_after_seconds) for an exception."""
    if isinstance(exc, HTTPError):
        if exc.code in RETRYABLE_STATUS:
            return True, f"http_{exc.code}", _retry_after_seconds(exc.headers)
        return False, f"http_{exc.code}", None
    if isinstance(exc, IncompleteRead):
        return True, "incomplete_read", None
    if isinstance(exc, HTTPException):
        return True, type(exc).__name__, None
    if _is_tls_failure(exc):
        return False, "tls_verification", None
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return True, "timeout", None
    if isinstance(exc, URLError):
        inner = exc.reason
        if isinstance(inner, (socket.timeout, TimeoutError)):
            return True, "timeout", None
        return True, f"urlerror:{type(inner).__name__ if isinstance(inner, Exception) else inner}", None
    if isinstance(exc, (ConnectionError, socket.gaierror, socket.herror, OSError)):
        return True, type(exc).__name__, None
    return False, type(exc).__name__, None


def fetch_bytes(url, budget, *, timeout=45, max_attempts=MAX_ATTEMPTS_PER_URL,
                opener=None, sleep=None, jitter=None, headers=None):
    """Fetch a complete response body with bounded retries.

    Returns ``(body, info)`` where ``info`` records attempts, status and size.
    Raises ``TransportError`` when the bounds are exhausted or the failure is
    permanent. Never returns a partial body.
    """
    jitter = jitter or (lambda: random.uniform(0.75, 1.25))
    sleep = sleep or time.sleep      # late-bound so tests can patch time.sleep
    opener = opener or urlopen       # late-bound so tests can patch soccer_transport.urlopen
    shown = sanitize_url(url)
    request_headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    request_headers.update(headers or {})
    last_error = None
    for attempt in range(1, max_attempts + 1):
        budget.charge(url, attempt)
        started = time.monotonic()
        try:
            request = Request(url, headers=request_headers)
            effective_timeout = max(1.0, min(float(timeout), budget.remaining_time()))
            with opener(request, timeout=effective_timeout) as response:
                status = getattr(response, "status", None) or response.getcode()
                body = response.read()
                declared = response.headers.get("Content-Length") if response.headers else None
            if declared is not None and declared.isdigit() and int(declared) != len(body):
                raise IncompleteRead(body, int(declared) - len(body))
            if not body:
                raise IncompleteRead(b"", None)
            budget.record(url=shown, attempt=attempt, outcome="ok", status=status,
                          bytes=len(body), elapsed_ms=round((time.monotonic() - started) * 1000))
            return body, {"url": shown, "attempts": attempt, "status": status, "bytes": len(body)}
        except Exception as exc:  # classified below; never swallowed silently
            retryable, label, retry_after = _classify(exc)
            last_error = exc
            budget.record(url=shown, attempt=attempt, outcome="error", error=label,
                          detail=str(exc)[:300], retryable=retryable,
                          elapsed_ms=round((time.monotonic() - started) * 1000))
            if not retryable:
                category = "tls" if label == "tls_verification" else (
                    "http_permanent" if label.startswith("http_") else "transport")
                raise TransportError(f"{label} for {shown} (not retryable)", category=category,
                                     url=shown, attempts=attempt, history=budget.history,
                                     last_error=exc) from exc
            if attempt >= max_attempts:
                break
            delay = retry_after if retry_after is not None else _backoff(attempt, jitter)
            if delay > budget.remaining_time():
                raise TransportError(
                    f"Elapsed-time budget would be exceeded waiting {delay:.1f}s before retry",
                    category="budget", url=shown, attempts=attempt, history=budget.history,
                    last_error=exc) from exc
            if delay > 0:
                sleep(delay)
    raise TransportError(
        f"{max_attempts} attempts failed for {shown}; last error: {last_error}",
        category="transport", url=shown, attempts=max_attempts, history=budget.history,
        last_error=last_error) from last_error


def fetch_json(url, budget, **kwargs):
    """Fetch and decode JSON. Decoding failures are InvalidResponse (not retried)."""
    body, info = fetch_bytes(url, budget, **kwargs)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidResponse(f"Complete response from {info['url']} is not valid JSON: {exc}") from exc
