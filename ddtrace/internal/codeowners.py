import os
import re
from typing import List
from typing import Optional
from typing import Tuple


def path_to_regex(pattern):
    # type: (str) -> re.Pattern
    """
    source https://github.com/sbdchd/codeowners/blob/c95e13d384ac09cfa1c23be1a8601987f41968ea/codeowners/__init__.py

    Copyright (c) 2019-2020 Steve Dignam

    Permission is hereby granted, free of charge, to any person obtaining
    a copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to
    the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
    LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
    WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

    ported from https://github.com/hmarr/codeowners/blob/d0452091447bd2a29ee508eebc5a79874fb5d4ff/match.go#L33

    MIT License

    Copyright (c) 2020 Harry Marr
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    """
    regex = ""

    slash_pos = pattern.find("/")
    anchored = slash_pos > -1 and slash_pos != len(pattern) - 1

    regex += r"\A" if anchored else r"(?:\A|/)"

    matches_dir = pattern[-1] == "/"
    pattern_trimmed = pattern.strip("/")

    in_char_class = False
    escaped = False

    iterator = enumerate(pattern_trimmed)
    for i, ch in iterator:

        if escaped:
            regex += re.escape(ch)
            escaped = False
            continue

        if ch == "\\":
            escaped = True
        elif ch == "*":
            if i + 1 < len(pattern_trimmed) and pattern_trimmed[i + 1] == "*":
                left_anchored = i == 0
                leading_slash = i > 0 and pattern_trimmed[i - 1] == "/"
                right_anchored = i + 2 == len(pattern_trimmed)
                trailing_slash = i + 2 < len(pattern_trimmed) and pattern_trimmed[i + 2] == "/"

                if (left_anchored or leading_slash) and (right_anchored or trailing_slash):
                    regex += ".*"

                    next(iterator, None)
                    next(iterator, None)
                    continue
            regex += "[^/]*"
        elif ch == "?":
            regex += "[^/]"
        elif ch == "[":
            in_char_class = True
            regex += ch
        elif ch == "]":
            if in_char_class:
                regex += ch
                in_char_class = False
            else:
                regex += re.escape(ch)
        else:
            regex += re.escape(ch)

    if in_char_class:
        raise ValueError("unterminated character class in pattern {pattern}".format(pattern=pattern))

    regex += "/" if matches_dir else r"(?:\Z|/)"
    return re.compile(regex)


class Codeowners(object):
    """Provide interface to parse CODEOWNERS file and match a given path against it."""

    KNOWN_LOCATIONS = (
        "CODEOWNERS",
        ".github/CODEOWNERS",
        "docs/CODEOWNERS",
        ".gitlab/CODEOWNERS",
    )

    def __init__(self, path=None, cwd=None):
        # type: (Optional[str], Optional[str]) -> None
        """Initialize Codeowners object.

        :param path: path to CODEOWNERS file otherwise try to use any from known locations
        """
        path = path or self.location(cwd)
        if path is not None:
            self.path = path  # type: str
        self.patterns = []  # type: List[Tuple[re.Pattern, List[str]]]
        self.parse()

    def location(self, cwd=None):
        # type: (Optional[str]) -> Optional[str]
        """Return the location of the CODEOWNERS file."""
        cwd = cwd or os.getcwd()
        for location in self.KNOWN_LOCATIONS:
            path = os.path.join(cwd, location)
            if os.path.isfile(path):
                return path
        raise ValueError("CODEOWNERS file not found")

    def parse(self):
        # type: () -> None
        """Parse CODEOWNERS file and store the lines and regexes."""
        with open(self.path) as f:
            patterns = []
            for line in f.readlines():
                line = line.strip()
                if line == "":
                    continue
                # Lines starting with '#' are comments.
                if line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    # found a code owners section
                    continue
                if line.startswith("^[") and line.endswith("]"):
                    # found an optional code owners section
                    continue

                elements = line.split()
                if len(elements) < 2:
                    continue

                path = elements[0]
                if path is None:
                    continue

                try:
                    pattern = path_to_regex(path)
                except (ValueError, IndexError):
                    continue

                owners = [owner for owner in elements[1:] if owner]

                if not owners:
                    continue
                patterns.append((pattern, owners))
            # Order is important. The last matching pattern has the most precedence.
            patterns.reverse()
            self.patterns = patterns

    def of(self, path):
        # type: (str) -> List[str]
        """Return code owners for a given path.

        :param path: path to check
        :return: list of file code owners identified by the given path
        """
        for pattern, owners in self.patterns:
            if pattern.search(path):
                return owners
        raise KeyError("no code owners found for {path}".format(path=path))
