"""Turn a raw build log into something a user and an operator can both act on.

A failed build used to surface as `Docker build failed with exit code 1.` plus
four kilobytes of PlatformIO output, shown to the user as the download link
text. That says nothing to a user and buries the one decisive line from an
operator. So failures now carry a stable code (which the page translates), one
quoted line of evidence, and the phase the build died in.

The detail line is quoted from the build log, and that log contains the full
`-D` flag dump, including the WiFi PSK and the MQTT password. Only lines that
match one of the diagnostic patterns below are ever lifted out of it, and each
is length-capped. Never widen this to "last line of the log".
"""

from __future__ import annotations

import re


# Emitted by docker/build_firmware.sh when it knows exactly what went wrong.
# One line, `MB_FAILURE code=<code> phase=<phase> detail=<free text>`.
FAILURE_LINE_RE = re.compile(
    r"^MB_FAILURE code=(?P<code>[a-z_]+) phase=(?P<phase>[a-z_]+)(?: detail=(?P<detail>.*))?$",
    re.MULTILINE,
)

# Codes the page knows how to translate. Anything else renders as `unknown`.
CODE_PATCH_FAILED = "patch_failed"
CODE_COMPILE_ERROR = "compile_error"
CODE_FIRMWARE_TOO_BIG = "firmware_too_big"
CODE_NO_ARTIFACTS = "no_artifacts"
CODE_TIMEOUT = "timeout"
CODE_INFRASTRUCTURE = "infrastructure"
CODE_INTERNAL = "internal"
CODE_UNKNOWN = "unknown"

KNOWN_CODES = {
    CODE_PATCH_FAILED,
    CODE_COMPILE_ERROR,
    CODE_FIRMWARE_TOO_BIG,
    CODE_NO_ARTIFACTS,
    CODE_TIMEOUT,
    CODE_INFRASTRUCTURE,
    CODE_INTERNAL,
    CODE_UNKNOWN,
}

DETAIL_MAX_CHARS = 300

# A compiler diagnostic: `src/mesh/NodeDB.cpp:705:27: error: 'info' was not ...`.
# Anchored on a source path so a stray `error:` inside the flag dump is ignored.
COMPILER_ERROR_RE = re.compile(
    r"^\s*(?P<line>[\w./+-]+\.(?:c|cc|cpp|cxx|h|hh|hpp|ino|S):\d+(?::\d+)?: (?:fatal )?error: .+)$",
    re.MULTILINE,
)

# The linker ran out of flash or RAM. Its own code: the user can act on it by
# dropping options, and it is not a source defect.
OVERFLOW_RE = re.compile(
    r"^\s*(?P<line>.*region [`'\"]?\w+[`'\"]? overflowed by [\d,]+ bytes.*)$",
    re.MULTILINE,
)

LINKER_ERROR_RE = re.compile(
    r"^\s*(?P<line>.*undefined reference to .+)$",
    re.MULTILINE,
)


# A tool the build calls could not be started: `sh: 1: <path>: not found` with
# PlatformIO's `Error 127`. The builder environment is at fault, not the user's
# settings; seen with a 32-bit ARM srec_cat on an arm64 image.
MISSING_TOOL_RE = re.compile(
    r"^\s*(?P<line>sh: \d+: \S+: (?:not found|Permission denied|cannot execute.*))$",
    re.MULTILINE,
)


class BuildFailure(Exception):
    """A build that failed for a reason we can name.

    `log` is the full build output, kept separate from the message so the
    operator log and the user-facing text never have to be the same string.
    """

    def __init__(self, code: str, *, detail: str = "", phase: str = "", log: str = "") -> None:
        self.code = code if code in KNOWN_CODES else CODE_UNKNOWN
        self.detail = _clip(detail)
        self.phase = phase
        self.log = log
        super().__init__(self.detail or self.code)


def _clip(text: str) -> str:
    collapsed = " ".join(str(text).split())
    if len(collapsed) <= DETAIL_MAX_CHARS:
        return collapsed
    return collapsed[: DETAIL_MAX_CHARS - 1] + "…"


def classify_build_log(log: str) -> tuple[str, str, str]:
    """Return (code, phase, detail) for a failed build's output.

    The builder script's own MB_FAILURE line wins when present: it knows what it
    was doing. Otherwise fall back to reading PlatformIO's diagnostics.
    """
    declared = None
    for declared in FAILURE_LINE_RE.finditer(log or ""):
        pass  # The last one is the one that killed the build.
    if declared is not None:
        code = declared.group("code")
        return (
            code if code in KNOWN_CODES else CODE_UNKNOWN,
            declared.group("phase"),
            _clip(declared.group("detail") or ""),
        )

    overflow = OVERFLOW_RE.search(log or "")
    if overflow:
        return CODE_FIRMWARE_TOO_BIG, "compile", _clip(overflow.group("line"))

    compile_error = COMPILER_ERROR_RE.search(log or "")
    if compile_error:
        return CODE_COMPILE_ERROR, "compile", _clip(compile_error.group("line"))

    linker_error = LINKER_ERROR_RE.search(log or "")
    if linker_error:
        return CODE_COMPILE_ERROR, "compile", _clip(linker_error.group("line"))

    missing_tool = MISSING_TOOL_RE.search(log or "")
    if missing_tool and "Error 127" in (log or ""):
        return CODE_INFRASTRUCTURE, "compile", _clip(missing_tool.group("line"))

    return CODE_UNKNOWN, "", ""


def failure_summary(code: str, phase: str, detail: str) -> str:
    """The block prepended to a stored build log, so `head` answers 'what broke'."""
    lines = [
        "===== BUILD FAILED =====",
        f"code:   {code}",
        f"phase:  {phase or 'unknown'}",
    ]
    if detail:
        lines.append(f"detail: {detail}")
    lines.append("========================")
    return "\n".join(lines)
