import pytest
import bblime

class FakeFileSet(bblime.FileSet):
    def __init__(self, fileContents):
        self.namesToPaths = {k: k for k in fileContents}
        self.fileContents = fileContents
        self.sortedNames = sorted(self.namesToPaths)

    def readlines(self, path):
        res = self.fileContents[path].split("\n")

        # the last line (should) have a trailing newline
        if res and not res[-1]:
            res.pop()

        return res

    def writelines(self, path, lines):
        # in this mock, names and paths are the same
        assert path in self.namesToPaths

        self.fileContents[path] = "".join(x + "\n" for x in lines)


class FakeWindow(bblime.CursesWindow):
    def __init__(self, width, height):
        self.width = width
        self.height = height

    @property
    def A_STANDOUT(self):
        return 'A_STANDOUT'

    @property
    def A_DIM(self):
        return 'A_DIM'

    @property
    def A_BOLD(self):
        return 'A_BOLD'

    @property
    def A_STANDOUT(self):
        return 'A_STANDOUT'

    @property
    def ACS_ULCORNER(self):
        return 'ACS_ULCORNER'

    @property
    def ACS_LLCORNER(self):
        return 'ACS_LLCORNER'

    @property
    def ACS_URCORNER(self):
        return 'ACS_URCORNER'

    @property
    def ACS_LRCORNER(self):
        return 'ACS_LRCORNER'

    @property
    def ACS_HLINE(self):
        return 'ACS_HLINE'

    @property
    def ACS_VLINE(self):
        return 'ACS_VLINE'

    def getmaxyx(self):
        return (self.height, self.width)

    def chgat(self, y, x, count, mode):
        pass

    def addch(self, y, x, ch):
        pass

    def erase(self):
        pass

    def addstr(self, y, x, text):
        if x + len(text) >= self.width:
            raise Exception("The real 'curses' would throw an exception here")

    def hline(self, y, x, linechar, count):
        if x + count >= self.width:
            raise Exception("The real 'curses' would throw an exception here")

    def vline(self, y, x, linechar, count):
        if y + count >= self.height:
            raise Exception("The real 'curses' would throw an exception here")


CANONICAL_CONTENTS = {}
CANONICAL_CONTENTS["file.py"] = (
    "# a comment\n"
    "CONSTANT = 'hi'\n"
    "\n"
    "def f(x):\n"
    "    pass\n"
)

def canonicalFakeFileSet():
    return FakeFileSet(CANONICAL_CONTENTS)


def test_basic():
    context = bblime.DisplayContext(FakeWindow(100, 50), canonicalFakeFileSet())

    # select 'file.py'
    context.receiveChars(bblime.KEY_CTRL_P, *"file", "KEY_DOWN", "\n")

    assert context.currentOpenFile().fileName == "file.py"

    # KEY_SEND is shift-end
    context.receiveChars("KEY_DOWN", "KEY_SEND", "a")

    assert context.currentOpenFile().lines[1] == "a"

def test_newline_with_indent():
    context = bblime.DisplayContext(FakeWindow(100, 50), canonicalFakeFileSet())

    # select 'file.py'
    context.receiveChars(bblime.KEY_CTRL_P, *"file", "KEY_DOWN", "\n")

    # go to end of line 5 and hit enter
    context.receiveChars(bblime.KEY_CTRL_G, *"5\n", "KEY_END", "\n")

    # we should have inserted some spaces to meet the four tabs
    assert context.currentOpenFile().lines[5] == "    "

    # now, if we hit backspace, go back to the start of the line
    context.receiveChars("KEY_BACKSPACE")

    assert context.currentOpenFile().lines[5] == ""

    # now, hit a space
    context.receiveChars(" ")
    assert context.currentOpenFile().lines[5] == " "
    context.receiveChars("KEY_BACKSPACE")
    assert context.currentOpenFile().lines[5] == ""

    # now, hit two spaces
    context.receiveChars(*"  ")
    assert context.currentOpenFile().lines[5] == "  "
    context.receiveChars("KEY_BACKSPACE")
    assert context.currentOpenFile().lines[5] == ""

    # now, hit five spaces
    context.receiveChars(*"     ")
    assert context.currentOpenFile().lines[5] == "     "
    context.receiveChars("KEY_BACKSPACE")
    assert context.currentOpenFile().lines[5] == "    "
    context.receiveChars("KEY_BACKSPACE")
    assert context.currentOpenFile().lines[5] == ""

    context.receiveChars("\t")
    assert context.currentOpenFile().lines[5] == "    "

    context.receiveChars("KEY_LEFT", "\t")
    assert context.currentOpenFile().lines[5] == "     "
