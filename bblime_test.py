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
        if x + len(text) > self.width:
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
CANONICAL_CONTENTS["boo.py"] = (
    "A = 'B'\n"
    "B = 'C'\n"
    "C = 'D'\n"
)
CANONICAL_CONTENTS["long.py"] = "\n".join([f"line {i}" for i in range(1, 20)])

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
    context.receiveChars(bblime.KEY_CTRL_P, *"file", "\n")

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

    # go to the beginning of 'def f(x)'
    context.receiveChars(bblime.KEY_CTRL_G, *"4\n")
    assert context.currentOpenFile().lines[3] == "def f(x):"

    # hit enter
    context.receiveChars("\n")
    assert context.currentOpenFile().lines[3] == ""
    assert context.currentOpenFile().lines[4] == "def f(x):"

def test_multi_copy_paste():
    context = bblime.DisplayContext(FakeWindow(100, 50), canonicalFakeFileSet())

    # select 'file.py'
    context.receiveChars(bblime.KEY_CTRL_P, *"boo", "\n")

    # hit 'alt-shift-down' twice
    context.receiveChars(bblime.KEY_SHIFT_ALT_DOWN, bblime.KEY_SHIFT_ALT_DOWN)

    context.receiveChars(bblime.KEY_SHIFT_RIGHT, bblime.KEY_CTRL_C)

    context.receiveChars("KEY_END", bblime.KEY_CTRL_V)

    assert context.currentOpenFile().lines[0] == "A = 'B'A"
    assert context.currentOpenFile().lines[1] == "B = 'C'B"
    assert context.currentOpenFile().lines[2] == "C = 'D'C"

    # unselect
    context.receiveChars(bblime.KEY_ESC)

    # copy a whole line
    context.receiveChars(bblime.KEY_CTRL_C)

    # go to the middle of the line and paste
    context.receiveChars("KEY_PPAGE")
    context.receiveChars("KEY_RIGHT", bblime.KEY_CTRL_V)

    assert context.currentOpenFile().lines[0] == "C = 'D'C"
    assert context.currentOpenFile().lines[1] == "A = 'B'A"

def test_find():
    context = bblime.DisplayContext(FakeWindow(100, 50), canonicalFakeFileSet())

    # select 'file.py'
    context.receiveChars(bblime.KEY_CTRL_P, *"boo", "\n")

    context.receiveChars(bblime.KEY_CTRL_F, *" = ", bblime.KEY_CTRL_A)

    assert len(context.currentOpenFile().selections) == 3

    context.receiveChars(bblime.KEY_ESC, 'KEY_PPAGE')
    assert len(context.currentOpenFile().selections) == 1
    assert context.currentOpenFile().selections[0].line0 == 0

    context.receiveChars(bblime.KEY_CTRL_F, bblime.KEY_CTRL_BACKSPACE, "'", "\n")
    assert len(context.currentOpenFile().selections) == 1

    assert context.currentOpenFile().selections[0].line0 == 0
    assert context.currentOpenFile().selections[0].col0 == 4

    context.receiveChars(bblime.KEY_F3)
    assert context.currentOpenFile().selections[0].line0 == 0
    assert context.currentOpenFile().selections[0].col0 == 6

    context.receiveChars(bblime.KEY_F3)
    assert context.currentOpenFile().selections[0].line0 == 1
    assert context.currentOpenFile().selections[0].col0 == 4

    context.receiveChars(bblime.KEY_F3)
    assert context.currentOpenFile().selections[0].line0 == 1
    assert context.currentOpenFile().selections[0].col0 == 6

    context.receiveChars(bblime.KEY_F3, bblime.KEY_F3)
    assert context.currentOpenFile().selections[0].line0 == 2

    context.receiveChars(bblime.KEY_F3, bblime.KEY_F3)
    assert context.currentOpenFile().selections[0].line0 == 0
    assert context.currentOpenFile().selections[0].col0 == 6

    context.receiveChars(bblime.KEY_SHIFT_F3)
    assert context.currentOpenFile().selections[0].line0 == 0
    assert context.currentOpenFile().selections[0].col0 == 4

    context.receiveChars(bblime.KEY_SHIFT_F3)
    assert context.currentOpenFile().selections[0].line0 == 2
    assert context.currentOpenFile().selections[0].col0 == 6

def test_backspace():
    context = bblime.DisplayContext(FakeWindow(100, 50), canonicalFakeFileSet())

    # select 'file.py'
    context.receiveChars(bblime.KEY_CTRL_P, *"file", "\n")

    # go to line 4, "def f(x):"
    context.receiveChars(bblime.KEY_CTRL_G, *"4\n")
    assert context.currentOpenFile().lines[3] == "def f(x):"

    # control-right to end of 'def', then control shift right to select 'f'
    assert context.currentOpenFile().selections[0].col0 == 0
    context.receiveChars(bblime.KEY_CTRL_RIGHT)

    assert context.currentOpenFile().selections[0].col0 == 3
    assert context.currentOpenFile().selections[0].col1 == 3

    context.receiveChars(bblime.KEY_CTRL_SHIFT_RIGHT)
    assert context.currentOpenFile().selections[0].col0 == 3
    assert context.currentOpenFile().selections[0].col1 == 5

    # delete the 'f'
    context.receiveChars('KEY_DC')
    assert context.currentOpenFile().lines[3] == "def(x):"
    assert context.currentOpenFile().selections[0].col0 == 3
    assert context.currentOpenFile().selections[0].col1 == 3

    # now hit backspace
    context.receiveChars('KEY_BACKSPACE')
    assert context.currentOpenFile().lines[3] == "de(x):"

    # now hit backspace
    context.receiveChars('KEY_BACKSPACE')
    context.receiveChars('KEY_BACKSPACE')
    assert context.currentOpenFile().lines[3] == "(x):"

    context.receiveChars('KEY_BACKSPACE')
    assert context.currentOpenFile().lines[2] == "(x):"

    context.receiveChars('KEY_BACKSPACE')
    assert context.currentOpenFile().lines[1] == "CONSTANT = 'hi'(x):"

def test_backspace2():
    context = bblime.DisplayContext(FakeWindow(100, 50), canonicalFakeFileSet())

    # select 'file.py'
    context.receiveChars(bblime.KEY_CTRL_P, *"file", "\n")

    # go to line 4, "def f(x):"
    context.receiveChars(bblime.KEY_CTRL_G, *"4\n")
    assert context.currentOpenFile().lines[3] == "def f(x):"

    # control-shift-right and delete 'def'
    context.receiveChars(bblime.KEY_CTRL_SHIFT_RIGHT)
    assert context.currentOpenFile().selections[0].col0 == 0
    assert context.currentOpenFile().selections[0].col1 == 3

    # delete the 'def'
    context.receiveChars('KEY_DC')
    assert context.currentOpenFile().lines[3] == " f(x):"
    assert context.currentOpenFile().selections[0].col0 == 0
    assert context.currentOpenFile().selections[0].col1 == 0

    # now hit backspace
    context.receiveChars('KEY_BACKSPACE')
    assert context.currentOpenFile().lines[2] == " f(x):"

def test_cut_multiline():
    context = bblime.DisplayContext(FakeWindow(100, 50), canonicalFakeFileSet())

    # select 'long.py'
    context.receiveChars(bblime.KEY_CTRL_P, *"long", "\n")

    # go to line 4 and select three lines
    context.receiveChars(bblime.KEY_CTRL_G, *"4\n", *[bblime.KEY_SHIFT_DOWN]*3)

    # now cut
    context.receiveChars(bblime.KEY_CTRL_X)

    assert context.currentOpenFile().lines[2] == "line 3"
    assert context.currentOpenFile().lines[3] == "line 7"

    assert context.clipboard == ["line 4\nline 5\nline 6\n"]

    # now paste
    context.receiveChars(bblime.KEY_CTRL_V)
    assert context.currentOpenFile().lines[2] == "line 3"
    assert context.currentOpenFile().lines[3] == "line 4"
    assert context.currentOpenFile().lines[4] == "line 5"
    assert context.currentOpenFile().lines[5] == "line 6"
    assert context.currentOpenFile().lines[6] == "line 7"


