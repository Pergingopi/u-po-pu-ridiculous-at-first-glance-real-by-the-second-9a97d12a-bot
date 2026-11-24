#!/usr/bin/env python3
"""Ridiculous at First Glance, Real by the Second - one sentence pitching a
bizarre startup idea that sounds absurd until you realise it would sell.

Pure Python 3.13 standard library. The program writes one pitch to
/output/entry.txt. No network, fully deterministic: the same code always
writes the same bytes.

The pitch (128 characters, no trailing newline):

    We rent hungry goats to clear overgrown lots for landlords, then sell
    tickets to neighbours who pay to watch the lawn disappear.

Why this sentence: renting out hungry goats to clear land sounds like a
joke, but goatscaping is a real business - landowners already pay for it
because goats clear brush cheaper and cleaner than machines on rough lots.
The second look is the double revenue: landlords pay for the clearing and
neighbours pay for tickets to watch the lawn disappear, so the same herd
earns twice from one job. One sentence names the odd thing being sold
(goat clearing as a show), who pays (landlords, then ticket-buying
neighbours), and why it holds together (a real service plus a real
audience).

The program validates the pitch against the competition gate before writing
anything: 1 to 200 characters, not only whitespace, a single line, no
control characters, ASCII only so the file's byte count equals the
character count. The gate counts the file exactly, so the file is written
with no trailing newline: total bytes equal the pitch's character count.
A pitch that fails the gate raises instead of producing an invalid entry.

The write itself is hardened: the temporary file is created with O_EXCL
(a stale temp from an interrupted run is removed and retried once), the
bytes are fsynced before the atomic rename, and the directory is fsynced
after it, so a crash cannot leave a partial entry.txt behind.

Usage: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os

PITCH = (
    "We rent hungry goats to clear overgrown lots for landlords, "
    "then sell tickets to neighbours who pay to watch the lawn disappear."
)

# Competition gate: entry.txt must be UTF-8 text of 1 to 200 characters,
# not only whitespace, a single line. The gate counts the file exactly,
# so no trailing newline is added. Validate before writing so a bad pitch
# can never reach the judge as an invalid entry.
assert 1 <= len(PITCH) <= 200, f"pitch is {len(PITCH)} chars, outside 1-200"
assert PITCH.strip(), "pitch must not be only whitespace"
assert PITCH == PITCH.strip(), "pitch must not start or end with whitespace"
assert "\n" not in PITCH and "\r" not in PITCH, "pitch must be one line"
assert all(ord(c) >= 0x20 and ord(c) != 0x7F for c in PITCH), (
    "pitch must not contain control characters"
)
data = PITCH.encode("utf-8")
# ASCII only, so the file's byte count is exactly the character count the
# gate measures.
assert len(data) == len(PITCH), "pitch must be ASCII so bytes equal chars"


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, ".entry.txt.tmp")
    final = os.path.join(out_dir, "entry.txt")
    for _attempt in range(2):
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            break
        except FileExistsError:
            os.unlink(tmp)
    else:
        raise RuntimeError("could not create a fresh temporary file")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    os.chmod(tmp, 0o644)
    os.replace(tmp, final)
    os.chmod(final, 0o644)
    _fsync_dir(out_dir)
    # Read back what landed on disk: the judge reads the file, not the
    # variable, so confirm the bytes are exactly the validated pitch.
    with open(final, "rb") as f:
        assert f.read() == data, "entry.txt on disk differs from the pitch"


if __name__ == "__main__":
    main()
