#!/usr/bin/env python3
"""
Centralized error handling and logging.

Requirements implemented:
- Codes in format MODULO-TIPO-CODIGO (e.g., VAL-001, SYS-500).
- Severities SEV1..SEV4.
- IEEE 1044-style context: type, origin, brief message.
- Structured JSON logging to stderr for every error.
"""

import json
import sys
from datetime import datetime, timezone


class CodedError(Exception):
    """Error with structured code, severity, and context."""

    def __init__(self, code, severity, message, *, details=None, err_type=None, origin=None):
        super().__init__(message)
        self.code = code
        self.severity = severity
        self.message = message
        self.details = details
        self.err_type = err_type
        self.origin = origin

    def to_dict(self):
        return {
            "error_code": self.code,
            "severity": self.severity,
            "message": self.message,
            "details": self.details or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": self.err_type or "",
            "origin": self.origin or "",
        }


def emit_error(err: CodedError):
    """Print structured JSON to stderr."""
    payload = err.to_dict()
    sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stderr.flush()
    return payload


def raise_error(code, severity, message, *, details=None, err_type=None, origin=None):
    """Helper to raise a CodedError."""
    raise CodedError(code, severity, message, details=details, err_type=err_type, origin=origin)
