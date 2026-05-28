"""Consistent JSON error responses for the whole API.

This is a JSON-first service, so a stray 404 / 405 / 413 / 500 should never hand
the caller Flask's default HTML error page. Registering these handlers keeps the
contract uniform: every error is ``{"error": ..., "status": <code>}``.
"""

from werkzeug.exceptions import HTTPException

# Human-friendly messages for the codes we care about; anything else falls back
# to the exception's own description.
_MESSAGES = {
    400: "Bad request.",
    401: "Authentication required.",
    404: "Resource not found.",
    405: "Method not allowed for this endpoint.",
    413: "Uploaded file is too large.",
    415: "Unsupported media type.",
    500: "Internal server error.",
}


def _json_error(status, message):
    from flask import jsonify

    return jsonify({"error": message, "status": status}), status


def register_error_handlers(app):
    """Attach JSON error handlers to *app*. Safe to call once at startup."""

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc):  # noqa: ANN001
        status = exc.code or 500
        message = _MESSAGES.get(status, exc.description or "Request failed.")
        return _json_error(status, message)

    @app.errorhandler(Exception)
    def _handle_unexpected(exc):  # noqa: ANN001
        # Let Flask's debugger surface the traceback in debug mode; in
        # production return a clean 500 instead of leaking internals.
        if app.debug:
            raise exc
        app.logger.exception("Unhandled exception: %s", exc)
        return _json_error(500, _MESSAGES[500])

    return app
