#!/usr/bin/env python3
"""Fortune Cookies for Machines — entry program.

The fortune lives in fortune.txt next to this script. The program reads
it, checks it against the competition's gate (UTF-8 text, 1-200
characters, exactly one line, not only whitespace) and writes it verbatim
to /output/entry.txt (or $MAKEFUN_OUTPUT_DIR/entry.txt when that is set).

The write is atomic — the fortune goes to a temporary file in the same
directory first and is then moved into place — and the finished file is
read back and compared byte for byte with the fortune, so a run can never
report success while leaving a partial or wrong entry.txt behind.

Python 3 standard library only; no network, no arguments needed.
"""

import os
import sys
import tempfile
from pathlib import Path

FORTUNE_FILE = Path(__file__).resolve().parent / "fortune.txt"
MIN_CHARS = 1
MAX_CHARS = 200


def read_fortune() -> str:
    """Return the fortune, without a single trailing line ending."""
    text = FORTUNE_FILE.read_text(encoding="utf-8")
    for ending in ("\r\n", "\n", "\r"):
        if text.endswith(ending):
            return text[: -len(ending)]
    return text


def gate_errors(text: str) -> list[str]:
    """All the ways the fortune can fail the gate, as plain reasons."""
    errors: list[str] = []
    if "\n" in text or "\r" in text:
        errors.append("fortune must be exactly one line")
    if not text.strip():
        errors.append("fortune must not be empty or only whitespace")
    if not MIN_CHARS <= len(text) <= MAX_CHARS:
        errors.append(
            f"fortune must be {MIN_CHARS}-{MAX_CHARS} characters, got {len(text)}"
        )
    return errors


def write_entry(fortune: str, out_dir: Path) -> Path:
    """Write the fortune to <out_dir>/entry.txt, atomically and verified.

    The bytes go to a temporary file in the same directory first and
    os.replace() moves it into place, so a run killed halfway can never
    leave a half-written entry.txt behind. The finished file is read
    back and compared byte for byte with the fortune; a mismatch is an
    error, not a success message. Raises OSError on any failure.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "entry.txt"
    if out_path.is_dir():
        raise IsADirectoryError(f"output path is a directory: {out_path}")
    data = fortune.encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(dir=out_dir, prefix=".entry-", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, out_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    if out_path.read_bytes() != data:
        raise OSError(f"verification failed: {out_path} does not match the fortune")
    return out_path


def main() -> int:
    try:
        fortune = read_fortune()
    except FileNotFoundError:
        print(f"error: fortune file not found: {FORTUNE_FILE}", file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print(
            f"error: fortune file is not valid UTF-8: {FORTUNE_FILE}",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"error: cannot read fortune file: {exc}", file=sys.stderr)
        return 1

    errors = gate_errors(fortune)
    if errors:
        for reason in errors:
            print(f"error: {reason}", file=sys.stderr)
        return 1

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    try:
        out_path = write_entry(fortune, out_dir)
    except OSError as exc:
        print(f"error: cannot write entry: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {len(fortune)} characters to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
