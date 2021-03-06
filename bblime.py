#!/usr/bin/python3
import curses
import sys
import os
import re

KEY_F3 = "KEY_F(3)"
KEY_SHIFT_F3 = "KEY_F(15)"
KEY_CTRL_F3 = "KEY_F(27)"
KEY_ALT_F3 = "KEY_F(51)"

KEY_CTRL_A = "\x01"
KEY_CTRL_Z = "\x1a"
KEY_CTRL_Y = "\x19"
KEY_CTRL_F = "\x06"
KEY_CTRL_G = "\x07"
KEY_CTRL_P = "\x10"
KEY_CTRL_D = "\x04"
KEY_CTRL_R = "\x12"
KEY_CTRL_S = "\x13"
KEY_CTRL_W = "\x17"
KEY_CTRL_X = "\x18"
KEY_CTRL_O = "\x0f"
KEY_CTRL_C = "\x03"
KEY_CTRL_V = "\x16"
KEY_CTRL_Q = "\x11"
KEY_CTRL_BACKSPACE = "\x08"
KEY_CTRL_DELETE = "kDC5"
KEY_ESC = "\x1b"
KEY_SHIFT_ALT_DOWN = "kDN4"
KEY_SHIFT_ALT_UP = "kUP4"
KEY_CTRL_SHIFT_LEFT = "kLFT6"
KEY_CTRL_LEFT = "kLFT5"
KEY_CTRL_SHIFT_RIGHT = "kRIT6"
KEY_CTRL_RIGHT = "kRIT5"
KEY_ALT_PAGE_DOWN = "kNXT3"
KEY_ALT_PAGE_UP = "kPRV3"
MAX_COL = 1000000000
KEY_SHIFT_DOWN = "KEY_SF"
KEY_SHIFT_UP = "KEY_SR"
KEY_SHIFT_LEFT = "KEY_SLEFT"
KEY_SHIFT_RIGHT = "KEY_SRIGHT"

def pad(text, chars):
    if len(text) > chars:
        return text[:chars]
    return text + " " * (chars - len(text))


class FileSet:
    def __init__(self, namesToPaths):
        self.namesToPaths = namesToPaths
        self.sortedNames = sorted(namesToPaths)

    def readlines(self, path):
        def stripnewline(x):
            if x.endswith("\n"):
                return x[:-1]
            return x

        with open(path, "r") as f:
            return [stripnewline(x) for x in f.readlines()]

    def writelines(self, path, lines):
        with open(path, "w") as f:
            f.write("".join([x + "\n" for x in lines]))


class Display:
    """Baseclass for all things that make little windows."""
    def __init__(self, context):
        self.context = context

    def textWithCursors(self, x0, y0, text, cursors):
        self.context.stdscr.addstr(y0, x0, text)

        for i in cursors:
            self.context.stdscr.chgat(y0, x0 + i, 1, self.context.stdscr.A_STANDOUT)

    def lightText(self, x0, y0, text):
        self.context.stdscr.addstr(y0, x0, text)
        self.context.stdscr.chgat(y0, x0, len(text), self.context.stdscr.A_DIM)

    def textBold(self, x0, y0, text):
        self.context.stdscr.addstr(y0, x0, text)
        self.context.stdscr.chgat(y0, x0, len(text), self.context.stdscr.A_BOLD)

    def highlightedText(self, x0, y0, text):
        self.context.stdscr.addstr(y0, x0, text)
        self.context.stdscr.chgat(y0, x0, len(text), self.context.stdscr.A_STANDOUT)

    def text(self, x0, y0, text):
        self.context.stdscr.addstr(y0, x0, text)

    def box(self, x0, y0, x1, y1, clear=False):
        self.context.stdscr.addch(y0, x0, self.context.stdscr.ACS_ULCORNER)
        self.context.stdscr.addch(y1, x0, self.context.stdscr.ACS_LLCORNER)
        self.context.stdscr.addch(y0, x1, self.context.stdscr.ACS_URCORNER)
        self.context.stdscr.addch(y1, x1, self.context.stdscr.ACS_LRCORNER)
        self.context.stdscr.hline(y0, x0 + 1, self.context.stdscr.ACS_HLINE, x1 - x0 - 1)
        self.context.stdscr.hline(y1, x0 + 1, self.context.stdscr.ACS_HLINE, x1 - x0 - 1)
        self.context.stdscr.vline(y0 + 1, x0, self.context.stdscr.ACS_VLINE, y1 - y0 - 1)
        self.context.stdscr.vline(y0 + 1, x1, self.context.stdscr.ACS_VLINE, y1 - y0 - 1)

        if clear:
            for row in range(y0 + 1, y1):
                self.text(x0 + 1, row, " " * (x1 - x0 - 2))

    def receiveChar(self, char):
        pass

    def resized(self):
        pass

    def redraw(self):
        pass



class DirFileSet(FileSet):
    def __init__(self, directory):
        self.directory = os.path.abspath(directory)

        names = {}
        def walk(subdir):
            for badDir in ["__pycache__", ".git"]:
                if subdir.endswith("/" + badDir) or subdir == badDir:
                    return

            if subdir.split("/")[0].startswith("."):
                return

            dirPart = [subdir] if subdir is not None else []
            ownDir = os.path.join(self.directory, *dirPart)

            for f in os.listdir(ownDir):
                if os.path.isfile(os.path.join(ownDir, f)):
                    names[os.path.join(*dirPart, f)] = os.path.join(ownDir, f)
                elif os.path.isdir(os.path.join(ownDir, f)):
                    walk(os.path.join(*dirPart, f))

        walk("")

        super().__init__(names)


class FindBox(Display):
    def __init__(self, context):
        super().__init__(context)

        self.regex = False
        self.wholeWord = False
        self.caseSensitive = False

        self.visible = False
        self.showReplace = False
        self.allFiles = False

        self.pattern = ""
        self.cursor = 0

    def curHeight(self):
        return 1

    def setPattern(self, pattern):
        self.pattern = pattern

        openFile = self.context.currentOpenFile()

        if openFile is not None:
            selections = openFile.findAll(pattern)

            if selections:
                openFile.ensureOnScreen(selections[0])

    def redraw(self):
        ypos = self.context.windowY - 2
        width = self.context.windowX
        self.text(0, ypos, " " * width)
        self.textBold(0, ypos, "FIND:")
        self.textWithCursors(6, ypos, pad(self.pattern, width - 6), [self.cursor])

    def receiveChar(self, char):
        if char == KEY_ESC:
            self.visible = False
            return True

        if char == "KEY_BACKSPACE" and self.cursor > 0:
            self.setPattern(self.pattern[:self.cursor - 1] + self.pattern[self.cursor:])
            self.cursor -= 1
            return True

        if char == KEY_CTRL_BACKSPACE:
            self.setPattern(self.pattern[self.cursor:])
            self.cursor = 0
            return True

        if char == KEY_CTRL_DELETE:
            self.setPattern(self.pattern[:self.cursor])
            return True

        if char == "KEY_DC" and self.cursor < len(self.pattern):
            self.setPattern(self.pattern[:self.cursor] + self.pattern[self.cursor + 1:])
            return True

        if char == "KEY_LEFT":
            self.cursor = max(0, self.cursor - 1)
            return True

        if char == "KEY_RIGHT":
            self.cursor = min(len(self.pattern), self.cursor + 1)
            return True

        if char in ("\n", KEY_CTRL_A):
            openFile = self.context.currentOpenFile()

            if openFile is not None:
                if char == "\n":
                    curSel = openFile.selections[-1]
                    newSel = openFile.find(self.pattern, (curSel.line1, curSel.col1))
                    if newSel is None:
                        newSel = openFile.find(self.pattern, (0, 0))

                    if newSel is not None:
                        openFile.selections = [newSel]
                else:
                    openFile.selections = openFile.findAll(self.pattern)

                if openFile.selections:
                    openFile.ensureOnScreen(openFile.selections[0])

                self.visible = False

            return True

        if len(char) == 1 and char.isprintable():
            self.setPattern(self.pattern[:self.cursor] + char + self.pattern[self.cursor:])
            self.cursor += 1
            return True


class DisplayContext:
    def __init__(self, stdscr, fileSet):
        self.fileSet = fileSet
        self.openFiles = {}
        self.clipboard = None
        self.clipboardIsWholeLine = False

        self.findBox = FindBox(self)

        self.stdscr = stdscr
        self.windowY, self.windowX = self.stdscr.getmaxyx()
        self.displays = [DefaultDisplay(self)]
        self.wantsToExit = False

    def pushDisplay(self, display):
        self.displays.append(display)
        self.fullRedraw()

    def pushDisplays(self, displays):
        self.displays.extend(displays)
        self.fullRedraw()

    def currentOpenFile(self):
        if isinstance(self.displays[-1], FileDisplay):
            return self.displays[-1]
        return None

    def openFile(self, fileName):
        self.displays = [d for d in self.displays if not isinstance(d, TextBufferDisplay)]

        if fileName not in self.openFiles:
            self.openFiles[fileName] = FileDisplay(self, fileName)

        self.openFiles[fileName].checkDisk()

        self.displays.append(self.openFiles[fileName])

        self.fullRedraw()

    def receiveChars(self, *chars):
        for c in chars:
            self.receiveChar(c)

    def receiveChar(self, char):
        if char in (KEY_ALT_PAGE_DOWN, KEY_ALT_PAGE_UP):
            # alt-page-down/up
            if self.openFiles:
                cof = self.currentOpenFile()
                if cof is not None:
                    index = sorted(self.openFiles).index(cof.fileName)
                    index = (index + (1 if char == KEY_ALT_PAGE_DOWN else -1)) % len(self.openFiles)
                    self.openFile(sorted(self.openFiles)[index])
            return True

        if char == "KEY_RESIZE":
            self.windowY, self.windowX = self.stdscr.getmaxyx()

            for d in self.displays:
                d.resized()

            self.fullRedraw()

            return True

        if char == KEY_CTRL_P:
            self.newWindow(FileSelector(self))
            return True

        if char == KEY_CTRL_O:
            whichFile = 0

            if self.displays and isinstance(self.displays[-1], FileDisplay):
                try:
                    whichFile = sorted(self.openFiles).index(self.displays[-1].fileName)
                except ValueError:
                    pass

            self.newWindow(OpenFiles(self, whichFile))
            return True

        if self.displays[-1].receiveChar(char):
            return True

        if char == KEY_CTRL_Q:
            needClose = [o for o in self.openFiles.values() if o.isChanged()]
            if not needClose:
                self.wantsToExit = True
            else:
                isFirst = True
                displays = []
                for n in needClose:
                    displays.append(CloseBeforeSavingDialog(self, n, postAction=self.setExitFlag))
                    isFirst = False
                self.pushDisplays(displays)

            return True

    def setExitFlag(self):
        self.wantsToExit = True

    def removeDisplay(self, disp):
        self.displays.remove(disp)

        if len(self.displays) == 0:
            self.displays.append(DefaultDisplay(self))

        self.fullRedraw()

    def fullRedraw(self):
        self.stdscr.erase()

        for disp in self.displays:
            disp.redraw()

    def newWindow(self, window):
        self.displays.append(window)
        window.redraw()


class Selection:
    def __init__(self, line0, col0, line1, col1):
        self.line0 = line0
        self.col0 = col0
        self.line1 = line1
        self.col1 = col1

    def asTuple(self):
        # ensure the sort-order is based on the earliest visible point
        if not self.isOrdered():
            return (self.line1, self.col1, self.line0, self.col0, 1)
        else:
            return (self.line0, self.col0, self.line1, self.col1, 0)

    def isOrdered(self):
        return (self.line0, self.col0) <= (self.line1, self.col1)

    def overlaps(self, other):
        t1 = self.asTuple()
        t2 = other.asTuple()

        low1 = (t1[0], t1[1])
        high1 = (t1[2], t1[3])

        low2 = (t2[0], t2[1])
        high2 = (t2[2], t2[3])

        if low1 > high2:
            return False

        if low2 > high1:
            return False

        return True

    def merge(self, other):
        t1 = self.asTuple()
        t2 = other.asTuple()

        low1 = (t1[0], t1[1])
        high1 = (t1[2], t1[3])

        low2 = (t2[0], t2[1])
        high2 = (t2[2], t2[3])

        low = min(low1, low2)
        high = min(high1, high2)

        return Selection(*low, *high)

    def __eq__(self, other):
        return self.asTuple() == other.asTuple()

    def __lt__(self, other):
        return self.asTuple() < other.asTuple()

    def __hash__(self):
        return hash(self.asTuple())

    def __str__(self):
        if self.isSingle():
            return f"{self.line0}:{self.col0}"

        if self.isSingleLine():
            return f"{self.line0}:{self.col0}-{self.col1}"

        return f"({self.line0}:{self.col0})-({self.line1}:{self.col1})"

    def __repr__(self):
        return str(self)

    def isSingle(self):
        return (self.line0, self.col0) == (self.line1, self.col1)

    def isSingleLine(self):
        return self.line0 == self.line1

    def isTrivial(self):
        return (self.line0, self.line1, self.col0, self.col1) == (0, 0, 0, 0)

    def clipToReal(self, lines):
        l0, c0, l1, c1 = self.line0, self.col0, self.line1, self.col1

        if not lines:
            return Selection(0, 0, 0, 0)

        if l0 < 0:
            l0 = 0
            c0 = 0

        if l1 < 0:
            l1 = 0
            c1 = 0

        if l0 >= len(lines):
            l0 = len(lines) - 1
            c0 = len(lines[-1])

        if l1 >= len(lines):
            l1 = len(lines) - 1
            c1 = len(lines[-1])

        if c0 < 0:
            c0 = 0
        if c0 > len(lines[l0]):
            c0 = len(lines[l0])

        if c1 < 0:
            c1 = 0
        if c1 > len(lines[l1]):
            c1 = len(lines[l1])

        if l0 > l1 or l0 == l1 and c0 > c1:
            lt, ct = l0, c0
            l0, c0 = l1, c1
            l1, c1 = lt, ct

        return Selection(l0, c0, l1, c1)

    def extendCursors(self, cursorsByLine, lines):
        self = self.clipToReal(lines)

        if self.isTrivial():
            cursorsByLine.setdefault(0, []).append(0)
            return

        if self.isSingle():
            cursorsByLine.setdefault(self.line0, []).append(self.col0)

        if self.line0 != self.line1:
            cursorsByLine.setdefault(self.line0, []).extend(
                range(self.col0, len(lines[self.line0]) + 1)
            )
            cursorsByLine.setdefault(self.line1, []).extend(
                range(0, self.col1)
            )
            for line in range(self.line0 + 1, self.line1):
                cursorsByLine.setdefault(line, []).extend(
                    range(max(1, len(lines[line])))
                )
        else:
            cursorsByLine.setdefault(self.line0, []).extend(
                range(self.col0, self.col1)
            )

    @staticmethod
    def clipLine(lNumber, lines):
        return max(0, min(lNumber, max(len(lines) - 1, 0)))

    @staticmethod
    def wordDelta(lines, line, col, direction):
        if line < 0:
            return 0, 0

        if line >= len(lines):
            return max(0, len(lines) - 1), MAX_COL

        col = min(col, len(lines[line]))

        # we can skip space until we get to non-space
        # at which point, we don't skip space
        skippedIdentifier = False

        charsSkipped = 0

        while True:
            lineOut, colOut = Selection.charDelta(lines, line, col, direction)

            if lineOut != line and charsSkipped > 0:
                return line, col

            if (lineOut, colOut) == (line, col):
                return lineOut, colOut

            charCrossed = Selection.charCrossedBy(lines, line, col, lineOut, colOut)

            if not charCrossed.isidentifier() and not skippedIdentifier:
                pass
            else:
                if not charCrossed.isidentifier():
                    return line, col

                skippedIdentifier = True

            line, col = lineOut, colOut
            charsSkipped += len(charCrossed)

    @staticmethod
    def charCrossedBy(lines, l0, c0, l1, c1):
        if l0 != l1:
            return "\n"

        return lines[l0][min(c0, c1):max(c0, c1)]

    @staticmethod
    def charDelta(lines, line, col, direction):
        if col >= len(lines[line]) and direction == -1:
            col = len(lines[line]) - 1
            if col < 0:
                line -= 1
                col = MAX_COL
        elif col >= len(lines[line]) and direction == 1:
            col = 0
            line += 1
        else:
            col += direction

            if col < 0:
                line -= 1
                col = MAX_COL

        line = Selection.clipLine(line, lines)

        col = min(col, MAX_COL)

        return line, col

    def delta(self, lines, dLine, dCol, extend=False, word=False, isHomeKey=False, isTabBackspace=False):
        if not lines:
            return Selection(0, 0, 0, 0)

        l0, c0, l1, c1 = self.line0, self.col0, self.line1, self.col1

        if isTabBackspace and c0 > 0:
            assert dCol == -1

            frontWhitespaceChars = len(lines[l1]) - len(lines[l1].lstrip())
            if c0 <= frontWhitespaceChars:
                whitespace = lines[l1][:frontWhitespaceChars]
                if whitespace == " " * len(whitespace):
                    # it's all whitespace here
                    if c0 % 4 == 0:
                        dCol = -4
                    else:
                        dCol = -(c0 % 4)

        if isHomeKey:
            c1 = len(lines[l1]) - len(lines[l1].lstrip())
        elif word:
            assert dLine == 0
            l1, c1 = self.wordDelta(lines, l1, c1, dCol)
        else:
            if dCol != 0:
                # this is a character delta
                l1, c1 = self.charDelta(lines, l1, c1, dCol)
            else:
                # this is a line delta
                l1 += dLine

                if l1 < 0 and dLine < -1:
                    c1 = 0
                elif l1 >= len(lines) and dLine > 1:
                    c1 = MAX_COL

                l1 = self.clipLine(l1, lines)

        if extend:
            return Selection(l0, c0, l1, c1)
        else:
            return Selection(l1, c1, l1, c1)

    def selectedText(self, lines):
        self = self.clipToReal(lines)

        if self.line0 == self.line1:
            return lines[self.line0][self.col0:self.col1]

        return "\n".join(
            [lines[self.line0][self.col0:]]
            + lines[self.line0 + 1:self.line1]
            + [lines[self.line1][:self.col1]]
        )

    def selectWord(self, lines):
        self = self.clipToReal(lines)

        toLeft = self.charDelta(lines, self.line0, self.col0, -1)
        toRight = self.charDelta(lines, self.line1, self.col1, 1)

        crossedLeft = self.charCrossedBy(lines, self.line0, self.col0, toLeft[0], toLeft[1])
        crossedRight = self.charCrossedBy(lines, self.line1, self.col1, toRight[0], toRight[1])

        if crossedLeft.isidentifier():
            leftPoint = self.wordDelta(lines, self.line0, self.col0, -1)
        else:
            leftPoint = self.line0, self.col0

        if crossedRight.isidentifier():
            rightPoint = self.wordDelta(lines, self.line1, self.col1, 1)
        else:
            rightPoint = self.line1, self.col1

        return Selection(*leftPoint, *rightPoint)

    @staticmethod
    def mergeContiguous(selections):
        selections = sorted(selections)

        while True:
            newSelections = Selection.mergeContiguousSinglePass(selections)

            if newSelections == selections:
                return newSelections
            else:
                selections = newSelections

        return selections

    @staticmethod
    def mergeContiguousSinglePass(selections):
        selections = list(selections)

        i = 0
        while i + 1 < len(selections):
            if selections[i].overlaps(selections[i+1]):
                merged = selections[i].merge(selections[i+1])
                selections[i] = merged
                selections.pop(i+1)
            else:
                i += 1

        return selections

    def insertedChars(self, line, col, charsInserted):
        l0, c0, l1, c1 = self.line0, self.col0, self.line1, self.col1

        if line == l0 and col <= c0:
            c0 += charsInserted

        if line == l1 and col <= c1:
            c1 += charsInserted

        return Selection(l0, c0, l1, c1)

    def insertedLines(self, line, col, count=1):
        l0, c0, l1, c1 = self.line0, self.col0, self.line1, self.col1

        def mapPoint(l, c):
            if (l, c) < (line, col):
                return l, c
            if l == line:
                return l + count, c - col
            else:
                return l + count, c

        l0, c0 = mapPoint(l0, c0)
        l1, c1 = mapPoint(l1, c1)

        return Selection(l0, c0, l1, c1)

    def rangeDeleted(self, selection):
        assert selection.isOrdered()

        l0, c0, l1, c1 = self.line0, self.col0, self.line1, self.col1

        l0, c0 = selection.mapPointIfSelfDeleted(l0, c0)
        l1, c1 = selection.mapPointIfSelfDeleted(l1, c1)

        return Selection(l0, c0, l1, c1)

    def mapPointIfSelfDeleted(self, line, col):
        if (line, col) < (self.line0, self.col0):
            return (line, col)

        if (line, col) <= (self.line1, self.col1):
            return (self.line0, self.col0)

        if line == self.line1:
            return (self.line1, col - (self.col1 - self.col0))

        return (line - (self.line1 - self.line0), col)

    def ensureValid(self, lines):
        l0, c0, l1, c1 = self.line0, self.col0, self.line1, self.col1

        if l0 >= len(lines):
            l0 = max(0, len(lines) - 1)

        if l1 >= len(lines):
            l1 = max(0, len(lines) - 1)

        return Selection(l0, c0, l1, c1)


class UndoBuffer:
    def __init__(self):
        self.history = []
        self.currentHistoryPos = None
        self.topHistoryPosIsInsert = False

    def pushState(self, state, changeIsNav=False):
        if not self.history:
            self.history.append(state)
            self.currentHistoryPos = 0
            self.topHistoryPosIsInsert = False
        else:
            if self.currentHistoryPos < len(self.history) - 1:
                self.history = self.history[:self.currentHistoryPos + 1]

            if changeIsNav:
                # we navigated - just set the flag
                self.topHistoryPosIsInsert = False
                return

            if self.topHistoryPosIsInsert:
                # replace the top history with this
                self.history[self.currentHistoryPos] = state
            else:
                self.history.append(state)
                self.currentHistoryPos += 1
                self.topHistoryPosIsInsert = True

    def undo(self):
        if not self.history:
            return None

        self.currentHistoryPos = max(0, self.currentHistoryPos - 1)

        return self.history[self.currentHistoryPos]

    def redo(self):
        if not self.history:
            return None

        self.currentHistoryPos = min(len(self.history) - 1, self.currentHistoryPos + 1)

        return self.history[self.currentHistoryPos]


class TextBufferDisplay(Display):
    def __init__(self, context):
        super().__init__(context)

        self.topLine = 0
        self.leftmostCol = 0

        self.selections = [Selection(0, 0, 0, 0)]

        self.linecountWidth = 5

        self.lines = []

        self.isReadOnly = False

        self._undoBuffer = None

    def isPythonFile(self):
        return False

    @property
    def undoBuffer(self):
        if self._undoBuffer is None:
            self._undoBuffer = UndoBuffer()

        return self._undoBuffer

    def getTitle(self):
        return None

    def save(self):
        pass

    def revert(self):
        pass

    def checkDisk(self):
        pass

    def receiveChar(self, char):
        if char == KEY_CTRL_F:
            if not self.context.findBox.visible:
                self.context.findBox.visible = True

                # put the currently selected text into the find box
                if not self.selections[-1].isSingle():
                    s = self.selections[-1]
                    if s.line0 == s.line1:
                        self.context.findBox.pattern = s.selectedText(self.lines)
                        self.context.findBox.cursor = len(self.context.findBox.pattern)

                self.redraw()
            return

        if char in (KEY_F3, KEY_SHIFT_F3):
            if not self.context.findBox.pattern:
                return

            direction = 1 if char == KEY_F3 else -1

            selPoint = (self.selections[-1].line1, self.selections[-1].col1)
            nextPt = self.find(self.context.findBox.pattern, selPoint, direction)

            if nextPt is None:
                if direction == 1:
                    startPoint = (0, 0)
                elif self.lines:
                    startPoint = (len(self.lines) - 1, len(self.lines[-1]) + 1)
                else:
                    startPoint = (0, 0)

                nextPt = self.find(self.context.findBox.pattern, startPoint, direction)

            if nextPt is not None:
                self.selections = [nextPt]
                self.ensureOnScreen(nextPt)
                self.redraw()

            return

        if self.context.findBox.visible:
            if self.context.findBox.receiveChar(char):
                self.redraw()
            return

        # make sure we have an undo buffer
        if char == KEY_CTRL_Z:
            newState = self.undoBuffer.undo()
            if newState is not None:
                self.lines, self.selections = list(newState[0]), list(newState[1])

                self.ensureOnScreen(self.selections[-1])
                self.redraw()
            return

        if char == KEY_CTRL_Y:
            newState = self.undoBuffer.redo()
            if newState is not None:
                self.lines, self.selections = list(newState[0]), list(newState[1])

                self.ensureOnScreen(self.selections[-1])
                self.redraw()
            return

        if char in (KEY_CTRL_C, KEY_CTRL_X):
            if len(self.selections) == 1 and self.selections[0].isSingle():
                # grab the line
                sel = self.selections[0].clipToReal(self.lines)
                if self.lines:
                    self.context.clipboard = [self.lines[sel.line0]]
                    self.context.clipboardIsWholeLine = True

                    if char == KEY_CTRL_X:
                        self.deleteSelection(Selection(self.line0, 0, self.line1, 0))
                else:
                    self.context.clipboardIsWholeLine = False
                    self.context.clipboard = None
            else:
                self.context.clipboardIsWholeLine = False

                self.context.clipboard = [
                    s.selectedText(self.lines) for s in self.selections
                ]

                if char == KEY_CTRL_X:
                    for i in range(len(self.selections)):
                        self.deleteSelection(self.selections[i])

            if char == KEY_CTRL_X:
                self.undoBuffer.pushState((list(self.lines), list(self.selections)))
                self.ensureOnScreen(self.selections[-1])
                self.redraw()

            return

        if char == KEY_CTRL_V:
            if self.context.clipboard:
                if self.context.clipboardIsWholeLine:
                    for i in range(len(self.selections)):
                        assert "\n" not in self.context.clipboard[0]
                        self.insert(self.selections[i].line0, 0, self.context.clipboard[0] + "\n")
                else:
                    for i in range(len(self.selections)):
                        self.replaceText(self.selections[i], self.context.clipboard[i % len(self.context.clipboard)])

                self.undoBuffer.pushState((list(self.lines), list(self.selections)))
                self.ensureOnScreen(self.selections[-1])
                self.redraw()
            return

        if char == KEY_ESC:
            self.selections = self.selections[-1:]
            return True

        if char == KEY_CTRL_S:
            self.save()
            self.redraw()
            return

        if char == KEY_CTRL_R:
            self.revert()
            self.redraw()
            return

        if char in (
            'KEY_LEFT', 'KEY_RIGHT', 'KEY_UP', 'KEY_DOWN', 'KEY_PPAGE', 'KEY_NPAGE', 'KEY_SPREVIOUS',
            'KEY_SNEXT', KEY_SHIFT_DOWN, KEY_SHIFT_UP, 'KEY_SLEFT', 'KEY_SF', 'KEY_HOME', 'KEY_SHOME',
            'KEY_END', 'KEY_SEND', KEY_SHIFT_RIGHT, KEY_SHIFT_LEFT,
            KEY_CTRL_SHIFT_RIGHT, KEY_CTRL_RIGHT, KEY_CTRL_SHIFT_LEFT, KEY_CTRL_LEFT,
            KEY_CTRL_D, KEY_SHIFT_ALT_UP, KEY_SHIFT_ALT_DOWN, KEY_ESC
        ):
            if not self.selections:
                self.selections = [Selection(0, 0, 0, 0)]

            if char == KEY_ESC:
                self.selections = self.selections[-1:]

            if char == "KEY_LEFT":
                self.selections = [d.delta(self.lines, 0, -1) for d in self.selections]

            if char == "KEY_RIGHT":
                self.selections = [d.delta(self.lines, 0, 1) for d in self.selections]

            if char == "KEY_UP":
                self.selections = [d.delta(self.lines, -1, 0) for d in self.selections]

            if char == "KEY_DOWN":
                self.selections = [d.delta(self.lines, 1, 0) for d in self.selections]

            if char == "KEY_PPAGE":
                self.selections = [d.delta(self.lines, -self.context.windowY, 0) for d in self.selections]

            if char == "KEY_NPAGE":
                self.selections = [d.delta(self.lines, self.context.windowY, 0) for d in self.selections]

            if char == "KEY_SPREVIOUS":
                self.selections = [d.delta(self.lines, -self.context.windowY, 0, extend=True) for d in self.selections]

            if char == "KEY_SNEXT":
                self.selections = [d.delta(self.lines, self.context.windowY, 0, extend=True) for d in self.selections]

            if char == KEY_SHIFT_UP:
                self.selections = [d.delta(self.lines, -1, 0, extend=True) for d in self.selections]

            if char == KEY_SHIFT_RIGHT:
                self.selections = [d.delta(self.lines, 0, 1, extend=True) for d in self.selections]

            if char == KEY_SHIFT_LEFT:
                self.selections = [d.delta(self.lines, 0, -1, extend=True) for d in self.selections]

            if char == KEY_SHIFT_DOWN:
                self.selections = [d.delta(self.lines, 1, 0, extend=True) for d in self.selections]

            if char == "KEY_HOME":
                self.selections = [
                    d.delta(self.lines, 0, -d.col1)
                    if d.col1 else d.delta(self.lines, 0, 1, isHomeKey=True)
                    for d in self.selections
                ]

            if char == "KEY_SHOME":
                self.selections = [
                    d.delta(self.lines, 0, -d.col1, extend=True)
                    if d.col1 else d.delta(self.lines, 0, 1, isHomeKey=True, extend=True)
                    for d in self.selections
                ]

            if char == "KEY_END":
                self.selections = [d.delta(self.lines, 0, MAX_COL) for d in self.selections]

            if char == "KEY_SEND":
                self.selections = [d.delta(self.lines, 0, MAX_COL, extend=True) for d in self.selections]

            if char == KEY_CTRL_RIGHT:
                self.selections = [d.delta(self.lines, 0, 1, word=True) for d in self.selections]

            if char == KEY_CTRL_SHIFT_RIGHT:
                self.selections = [d.delta(self.lines, 0, 1, word=True, extend=True) for d in self.selections]

            if char == KEY_CTRL_LEFT:
                self.selections = [d.delta(self.lines, 0, -1, word=True) for d in self.selections]

            if char == KEY_CTRL_SHIFT_LEFT:
                self.selections = [d.delta(self.lines, 0, -1, word=True, extend=True) for d in self.selections]

            if char == KEY_SHIFT_ALT_UP:
                # shift-alt-up
                self.selections = self.selections + [d.delta(self.lines, -1, 0) for d in self.selections]

            if char == KEY_SHIFT_ALT_DOWN:
                # shift-alt-down
                self.selections = self.selections + [d.delta(self.lines, 1, 0) for d in self.selections]

            if char == KEY_CTRL_D:
                newSelection = [d.selectWord(self.lines) for d in self.selections]

                if newSelection == self.selections:
                    # that didn't do anything. So, find the next word like the last one
                    text = newSelection[-1].selectedText(self.lines)

                    nextSelect = self.find(text, (newSelection[-1].line1, newSelection[-1].col1))
                    if nextSelect is not None:
                        self.selections = newSelection + [nextSelect]
                else:
                    self.selections = newSelection

            self.selections = Selection.mergeContiguous(self.selections)

            self.undoBuffer.pushState((list(self.lines), list(self.selections)), True)

            self.ensureOnScreen(self.selections[-1])
            self.redraw()
            return

        if not self.isReadOnly:
            if char == "KEY_BACKSPACE":
                self.selections = [
                    s.delta(self.lines, 0, -1, extend=True, isTabBackspace=self.isPythonFile())
                    if s.isSingle() else s for s in self.selections
                ]

                for i in range(len(self.selections)):
                    self.deleteSelection(self.selections[i])

                self.selections = Selection.mergeContiguous(self.selections)

                self.undoBuffer.pushState((list(self.lines), list(self.selections)))

                self.ensureOnScreen(self.selections[-1])
                self.redraw()
                return

            if char == "KEY_DC":
                self.selections = [s.delta(self.lines, 0, 1, extend=True) if s.isSingle() else s for s in self.selections]

                for i in range(len(self.selections)):
                    self.deleteSelection(self.selections[i])

                self.selections = Selection.mergeContiguous(self.selections)

                self.undoBuffer.pushState((list(self.lines), list(self.selections)))

                self.ensureOnScreen(self.selections[-1])
                self.redraw()
                return

            if char == "\n":
                for i in range(len(self.selections)):
                    self.deleteSelection(self.selections[i])

                for i in range(len(self.selections)):
                    self.insertNewlineWithIndent(self.selections[i].line1, self.selections[i].col1)

                self.selections = Selection.mergeContiguous(self.selections)

                self.undoBuffer.pushState((list(self.lines), list(self.selections)))

                self.ensureOnScreen(self.selections[-1])
                self.redraw()
                return

            if char == "KEY_BTAB":
                if len(self.selections) == 1 and self.selections[0].line0 != self.selections[0].line1:
                    for i in range(self.selections[0].line0, self.selections[0].line1 + (1 if self.selections[0].col1 else 0)):
                        if self.lines[i][:4] == "    ":
                            self.deleteSelection(Selection(i, 0, i, 4))

                    self.ensureOnScreen(self.selections[0])
                    self.redraw()
                    return True

            if char == "\t":
                if len(self.selections) == 1 and self.selections[0].line0 != self.selections[0].line1:
                    for i in range(self.selections[0].line0, self.selections[0].line1 + (1 if self.selections[0].col1 else 0)):
                        self.insert(i, 0, "    ")

                    self.ensureOnScreen(self.selections[0])
                    self.redraw()
                    return True
                else:
                    for i in range(len(self.selections)):
                        self.deleteSelection(self.selections[i])

                    for i in range(len(self.selections)):
                        self.insertTabWithIndent(self.selections[i].line1, self.selections[i].col1)

                    self.selections = Selection.mergeContiguous(self.selections)

                    self.undoBuffer.pushState((list(self.lines), list(self.selections)))

                    self.ensureOnScreen(self.selections[-1])
                    self.redraw()
                    return

            if len(char) == 1 and char.isprintable():
                # we're typing
                for i in range(len(self.selections)):
                    self.replaceText(self.selections[i], char)

                self.selections = Selection.mergeContiguous(self.selections)

                self.undoBuffer.pushState((list(self.lines), list(self.selections)))

                self.ensureOnScreen(self.selections[-1])
                self.redraw()
                return

        # display the character
        self.text(self.context.windowX - len(repr(char)) - 2, 0, repr(char))

    def replaceText(self, selection, newContents):
        selection = selection.clipToReal(self.lines)

        self.deleteSelection(selection)
        selection = selection.rangeDeleted(selection)

        self.insert(selection.line1, selection.col1, newContents)

    def deleteSelection(self, selection):
        if selection.isSingle():
            return

        selection = selection.clipToReal(self.lines)

        if selection.line0 == selection.line1:
            self.lines[selection.line0] = (
                self.lines[selection.line0][:selection.col0] + self.lines[selection.line0][selection.col1:]
            )
        else:
            self.lines = (
                self.lines[:selection.line0]
                + [self.lines[selection.line0][:selection.col0] + self.lines[selection.line1][selection.col1:]]
                + self.lines[selection.line1 + 1:]
            )

        for i in range(len(self.selections)):
            self.selections[i] = self.selections[i].rangeDeleted(selection)

    def insertNewlineWithIndent(self, line, col):
        indent = ""

        # implement python newlines
        if self.isPythonFile():
            if 0 <= line < len(self.lines):
                indent = self.lines[line][:len(self.lines[line]) - len(self.lines[line].lstrip())]
                if len(indent) > col:
                    indent = indent[:col]

                if self.lines[line].endswith(":") and col >= len(self.lines[line]):
                    indent += "    "

        self.insert(line, col, "\n")
        if indent:
            self.insert(line + 1, 0, indent)

    def insertTabWithIndent(self, line, col):
        if not self.isPythonFile() or not (0 <= line < len(self.lines)):
            self.insert(line, col, "\t")
        else:
            frontWhitespaceChars = len(self.lines[line]) - len(self.lines[line].lstrip())

            if col <= frontWhitespaceChars and self.lines[line][:frontWhitespaceChars] == (" " * frontWhitespaceChars):
                # we're hitting 'tab' in a bunch of spaces. round up to the nearest 4
                self.insert(line, col, " " * (4 - (col % 4)))
            else:
                self.insert(line, col, "    ")

    def insert(self, line, col, newText):
        if not newText:
            return
        if newText == "\n" * len(newText):
            for i in range(len(self.selections)):
                self.selections[i] = self.selections[i].insertedLines(line, col, len(newText))

            self.lines = (
                self.lines[:line]
                + [self.lines[line][:col]]
                + ([""] * (len(newText) - 1))
                + [self.lines[line][col:]]
                + self.lines[line+1:]
            )
        elif "\n" in newText:
            lines = newText.split("\n")

            self.insert(line, col, lines[0])
            self.insert(line, col + len(lines[0]), "\n" * (len(lines) - 1))
            self.insert(line + len(lines) - 1, 0, lines[-1])

            for internalLineIx in range(1, len(lines) - 1):
                self.lines[line + internalLineIx] = lines[internalLineIx]
        else:
            for i in range(len(self.selections)):
                self.selections[i] = self.selections[i].insertedChars(line, col, len(newText))

            self.lines[line] = self.lines[line][:col] + newText + self.lines[line][col:]

    def findAll(self, searchFor, maxCount=1000):
        result = []

        while len(result) < maxCount:
            if not result:
                searchPoint = (0, 0)
            else:
                searchPoint = (result[-1].line1, result[-1].col1)

            sel = self.find(searchFor, searchPoint)

            if sel is None:
                return result

            result.append(sel)

        return result

    def find(self, searchFor, startLineAndCol, direction=1):
        def indexIn(needle, haystack, startPos=None):
            if direction == -1:
                res = haystack.rfind(needle, None, startPos - 1 if startPos is not None else None)
            else:
                res = haystack.find(needle, startPos)

            if res == -1:
                return None
            else:
                return res

        if "\n" in searchFor:
            # not implemented yet
            return None
        else:
            line, col = startLineAndCol

            index = indexIn(searchFor, self.lines[line], col)

            if index is not None:
                return Selection(line, index, line, index + len(searchFor))

            line += direction
            while 0 <= line < len(self.lines):
                index = indexIn(searchFor, self.lines[line])

                if index is not None:
                    return Selection(line, index, line, index + len(searchFor))

                line += direction

            return None

    def ensureOnScreen(self, lineAndCol):
        line, col = lineAndCol.line1, lineAndCol.col1

        windowY = self.context.windowY

        if line < self.topLine:
            if self.topLine - line > 5:
                self.topLine = max(0, line - windowY // 2)
            else:
                self.topLine = max(0, line - 1)

        if line > self.topLine + windowY - 3:
            if line - (self.topLine + windowY - 1) > 8:
                self.topLine = max(0, min(len(self.lines) - 1, line - windowY // 2))
            else:
                self.topLine = max(0, min(len(self.lines) - 1, line - windowY + 3))

    def redraw(self):
        cursorsByLine = {}

        for selection in self.selections:
            selection.extendCursors(cursorsByLine, self.lines)

        if self.context.findBox.visible:
            bottomRows = 2 + self.context.findBox.curHeight()
        else:
            bottomRows = 2

        for screenRow in range(self.context.windowY - bottomRows):
            lineNumber = self.topLine + screenRow + 1

            self.lightText(0, screenRow + 1, pad(str(lineNumber), self.linecountWidth + 2))

            self.textWithCursors(
                self.linecountWidth + 2,
                screenRow + 1,
                self.visibleTextForLine(lineNumber - 1),
                cursorsByLine.get(lineNumber - 1, [])
            )

        if self.context.findBox.visible:
            self.context.findBox.redraw()

        if self.getTitle() is not None:
            self.textBold(0, 0, pad(str(self.getTitle()), self.context.windowX - 20))

    def visibleTextForLine(self, lineIndex):
        width = self.context.windowX - self.linecountWidth - 5

        if lineIndex < 0 or lineIndex >= len(self.lines):
            return pad("", width)

        return pad(self.lines[lineIndex][self.leftmostCol:], width)


class FileDisplay(TextBufferDisplay):
    def __init__(self, context, fileName):
        super().__init__(context)

        self.fileName = fileName
        self.path = context.fileSet.namesToPaths[fileName]

        self.lines = self.context.fileSet.readlines(self.path)
        self.linesOnDisk = list(self.lines)

        self.undoBuffer.pushState((list(self.lines), list(self.selections)))

    def isPythonFile(self):
        return self.fileName.endswith(".py")

    def isChanged(self):
        return self.lines != self.linesOnDisk

    def getTitle(self):
        return ("* " if self.isChanged() else "  ") + self.fileName

    def save(self):
        if self.isChanged():
            self.context.fileSet.writelines(self.path, self.lines)
            self.linesOnDisk = list(self.lines)

    def checkDisk(self):
        if not self.isChanged():
            newLines = self.context.fileSet.readlines(self.path)

            if newLines != self.lines:
                self.lines = newLines
                self.linesOnDisk = list(newLines)

                self.selections = [s.ensureValid(lines) for s in self.selections]

    def revert(self):
        self.lines = list(self.linesOnDisk)
        self.checkDisk()

    def receiveChar(self, char):
        if char == KEY_CTRL_W:
            self.close()
            return

        if char == KEY_CTRL_G:
            self.context.pushDisplay(
                GoToLineDisplay(self.context, self)
            )

        return super().receiveChar(char)

    def close(self):
        if self.isChanged():
            self.context.pushDisplay(
                CloseBeforeSavingDialog(self.context, self, postAction=self.completeClose)
            )
        else:
            self.completeClose()

    def completeClose(self):
        self.context.openFiles.pop(self.fileName)
        self.context.removeDisplay(self)


class DefaultDisplay(TextBufferDisplay):
    def __init__(self, context):
        super().__init__(context)

        self.isReadOnly = True

        self.lines = [
            "",
            "                    Welcome to braxblime",
            "",
            "key bindings:",
            "    Ctrl-Q to quit",
            "    Ctrl-P to open files",
            "    Ctrl-O to see open files",
            "    Alt-PageDn to go to next open file",
            "    Alt-PageUp to go to prior open file",
            "",
            "within a file:",
            "    Ctrl-W to close",
            "    Ctrl-S to save",
            "    Ctrl-R to revert",
            "    Ctrl-D to select words",
            "    Ctrl-F to find",
            "        Ctrl-A to select all finds simultaneously",
            "    F3 to go to next find item",
            "    Shift-F3 to go to prior find item"
        ]


class CloseBeforeSavingDialog(Display):
    def __init__(self, context, file, postAction):
        super().__init__(context)
        self.file = file
        self.postAction = postAction

        self.resized()

    def resized(self):
        self.width = min(self.context.windowX - 30, 150)
        self.xPos = self.context.windowX // 2 - self.width // 2
        self.yPos = 5

    def redraw(self):
        self.box()

    def redraw(self):
        self.box(self.xPos, self.yPos, self.xPos + self.width, self.yPos + 6, clear=True)
        self.text(self.xPos + 2, self.yPos + 2, pad("File " + self.file.fileName + " is dirty", self.width - 10))
        self.text(self.xPos + 2, self.yPos + 4, pad("Save before exiting? [Y/n]", self.width - 10))

    def receiveChar(self, char):
        if char in "yYn\n":
            if char != "n":
                self.file.save()

            self.context.removeDisplay(self)
            self.postAction()


class OpenFiles(Display):
    def __init__(self, context, whichFileIx=0):
        self.context = context
        self.whichFileIx = whichFileIx
        self.topLineIx = 0

    def redraw(self):
        text = "Open Files"
        self.text(0, 0, " " * self.context.windowX)
        self.textBold(self.context.windowX // 2 - len(text) // 2, 0, text)
        for row in range(1, self.context.windowY - 1):
            self.text(0, row, " " * self.context.windowX)

        if not self.context.openFiles:
            text = "<no open files>"
            self.lightText(self.context.windowX // 2 - len(text) // 2, self.context.windowY // 2, text)
            return

        openFilesList = sorted(self.context.openFiles)

        for screenRow in range(self.context.windowY - 4):
            fileIx = screenRow + self.topLineIx

            if fileIx >= 0 and fileIx < len(openFilesList):
                if fileIx == self.whichFileIx:
                    self.highlightedText(2, screenRow + 2, self.context.openFiles[openFilesList[fileIx]].getTitle())
                else:
                    self.text(2, screenRow + 2, self.context.openFiles[openFilesList[fileIx]].getTitle())

    def receiveChar(self, char):
        res = self._receiveChar(char)

        if res:
            self.redraw()

        return res

    def getOpenFile(self):
        fnames = sorted(self.context.openFiles)
        if 0 <= self.whichFileIx < len(fnames):
            return self.context.openFiles[fnames[self.whichFileIx]]
        return None

    def _receiveChar(self, char):
        if char == KEY_ESC:
            self.context.removeDisplay(self)
            return True

        if char == "KEY_DOWN":
            self.whichFileIx = min(self.whichFileIx + 1, len(self.context.openFiles) - 1)
            self.ensureOnScreen()
            return True

        if char == "KEY_UP":
            self.whichFileIx = max(self.whichFileIx - 1, 0)
            self.ensureOnScreen()
            return True

        if char == "KEY_PPAGE":
            self.whichFileIx = min(self.whichFileIx + self.context.windowY, len(self.context.openFiles) - 1)
            self.ensureOnScreen()
            return True

        if char == "KEY_NPAGE":
            self.whichFileIx = max(self.whichFileIx - self.context.windowY, 0)
            self.ensureOnScreen()
            return True

        if char in (KEY_CTRL_S, KEY_CTRL_R, KEY_CTRL_W):
            fileObj = self.getOpenFile()
            if fileObj:
                if char == KEY_CTRL_S:
                    fileObj.save()
                if char == KEY_CTRL_R:
                    fileObj.revert()
                if char == KEY_CTRL_W:
                    fileObj.close()
                self.redraw()

            return

        if char == "\n":
            if 0 <= self.whichFileIx < len(self.context.openFiles):
                self.context.removeDisplay(self)
                self.context.openFile(sorted(self.context.openFiles)[self.whichFileIx])
                self.context.fullRedraw()
                return False
            return True

    def ensureOnScreen(self):
        if self.whichFileIx < self.topLineIx:
            self.topLineIx = max(0, self.whichFileIx - 1)

        if self.whichFileIx > self.topLineIx + self.context.windowY - 2:
            self.topLineIx = max(0, self.whichFileIx - self.context.windowY // 2)


class GoToLineDisplay(Display):
    def __init__(self, context, file):
        super().__init__(context)
        self.file = file
        self.contents = ""
        self.cursor = 0
        self.resized()

    def resized(self):
        self.width = min(self.context.windowX - 30, 150)
        self.xPos = self.context.windowX // 2 - self.width // 2
        self.yPos = 5

    def redraw(self):
        self.box()

    def redraw(self):
        self.box(self.xPos, self.yPos, self.xPos + self.width, self.yPos + 6, clear=True)
        self.text(self.xPos + 2, self.yPos + 2, pad("Go to line:", self.width - 10))
        self.text(self.xPos + 2, self.yPos + 4, pad(self.contents, self.width - 10))

    def setContents(self, contents):
        self.contents = contents

    def receiveChar(self, char):
        res = self._receiveChar(char)

        if res:
            self.redraw()

        return res

    def _receiveChar(self, char):
        if char == KEY_ESC:
            self.context.removeDisplay(self)
            return True

        if char == "KEY_BACKSPACE" and self.cursor > 0:
            self.setContents(self.contents[:self.cursor - 1] + self.contents[self.cursor:])
            self.cursor -= 1
            return True

        if char == KEY_CTRL_BACKSPACE:
            self.setContents(self.contents[self.cursor:])
            self.cursor = 0
            return True

        if char == KEY_CTRL_DELETE:
            self.setContents(self.contents[:self.cursor])
            return True

        if char == "KEY_DC" and self.cursor < len(self.contents):
            self.setContents(self.contents[:self.cursor] + self.contents[self.cursor + 1:])
            return True

        if char == "KEY_LEFT":
            self.cursor = max(0, self.cursor - 1)
            return True

        if char == "KEY_RIGHT":
            self.cursor = min(len(self.contents), self.cursor + 1)
            return True

        if char == "\n":
            try:
                line = int(self.contents)
            except Exception:
                line = 1

            line -= 1

            self.file.selections = [Selection(line, 0, line, 0)]
            self.file.ensureOnScreen(self.file.selections[-1])

            self.context.removeDisplay(self)
            return False

        if len(char) == 1 and (char.isalnum() or char in ("/ _.")):
            self.setContents(self.contents[:self.cursor] + char + self.contents[self.cursor:])
            self.cursor += 1
            return True


class FileSelector(Display):
    def __init__(self, context):
        self.context = context
        self.filterText = ""
        self.cursor = 0
        self.selectedMatchIx = None
        self.matches = self.context.fileSet.sortedNames

        self.resized()

    def resized(self):
        self.width = min(self.context.windowX - 30, 150)
        self.xPos = self.context.windowX // 2 - self.width // 2
        self.yPos = 5

    def setFilter(self, filterText):
        self.filterText = filterText

        filterFun = self.buildFilter(self.filterText)

        self.matches = [x for x in self.context.fileSet.sortedNames if filterFun(x)]
        self.selectedMatchIx = None

    def buildFilter(self, filterText):
        if not filterText:
            return lambda x: True

        regex = []

        breakpoints = [0]

        for i in range(1, len(filterText)):
            if filterText[i].isupper() or filterText[i] == "_":
                breakpoints.append(i)
            elif filterText[i] == "/":
                breakpoints.append(i)
            elif filterText[i] == ".":
                breakpoints.append(i)
            elif i > 0 and filterText[i - 1] == "/":
                breakpoints.append(i)

        breakpoints.append(len(filterText))

        dumpedSoFar = 0

        for b in breakpoints:
            regex.append(filterText[dumpedSoFar:b].replace(".", "\\."))
            regex.append("[a-z0-9]*")
            dumpedSoFar = b

        pat = re.compile(".*" + "".join(regex) + ".*")

        return lambda c: pat.match(c)

    def redraw(self):
        self.box(self.xPos, self.yPos, self.xPos + self.width, self.yPos + 20, clear=True)
        self.textWithCursors(self.xPos + 1, self.yPos + 1, pad(self.filterText, self.width - 2), [self.cursor])

        self.startMatchIx = 0
        if self.selectedMatchIx is not None:
            self.startMatchIx = max(0, self.selectedMatchIx - 4)

        for lineIx in range(15):
            matchIx = self.startMatchIx + lineIx

            if matchIx >= 0 and matchIx < len(self.matches):
                if matchIx == self.selectedMatchIx:
                    self.highlightedText(self.xPos + 2, self.yPos + 3 + lineIx, pad(self.matches[matchIx], self.width - 4))
                else:
                    self.text(self.xPos + 2, self.yPos + 3 + lineIx, pad(self.matches[matchIx], self.width - 4))
            else:
                self.text(self.xPos + 2, self.yPos + 3 + lineIx, pad("", self.width - 4))

    def receiveChar(self, char):
        res = self._receiveChar(char)

        if res:
            self.redraw()

        return res

    def _receiveChar(self, char):
        if char == KEY_ESC:
            self.context.removeDisplay(self)
            return True

        if char == "KEY_BACKSPACE" and self.cursor > 0:
            self.setFilter(self.filterText[:self.cursor - 1] + self.filterText[self.cursor:])
            self.cursor -= 1
            return True

        if char == KEY_CTRL_BACKSPACE:
            self.setFilter(self.filterText[self.cursor:])
            self.cursor = 0
            return True

        if char == KEY_CTRL_DELETE:
            self.setFilter(self.filterText[:self.cursor])
            return True

        if char == "KEY_DC" and self.cursor < len(self.filterText):
            self.setFilter(self.filterText[:self.cursor] + self.filterText[self.cursor + 1:])
            return True

        if char == "KEY_LEFT":
            self.cursor = max(0, self.cursor - 1)
            return True

        if char == "KEY_RIGHT":
            self.cursor = min(len(self.filterText), self.cursor + 1)
            return True

        if char == "KEY_DOWN":
            if self.selectedMatchIx is None:
                self.selectedMatchIx = -1

            self.selectedMatchIx = min(self.selectedMatchIx + 1, len(self.matches))
            return True

        if char == "KEY_UP":
            if self.selectedMatchIx is None:
                self.selectedMatchIx = -1

            self.selectedMatchIx = max(0, self.selectedMatchIx - 1)
            return True

        if char == "\n":
            if not self.matches:
                return False

            self.context.removeDisplay(self)
            self.context.openFile(self.matches[self.selectedMatchIx or 0])
            return False

        if len(char) == 1 and (char.isalnum() or char in ("/ _.")):
            self.setFilter(self.filterText[:self.cursor] + char + self.filterText[self.cursor:])
            self.cursor += 1
            return True


class CursesWindow:
    """A wrapper around a standard curses 'window' object.

    We need this so we can test the object. Curses has a behavior
    where you have to initialize the screen to determine some of these
    constants - in a test environment, it's easier to just intercept
    the whole interface.

    Outside of 'main', all curses interactions should go through
    this object.
    """
    def __init__(self, stdscr):
        self.stdscr = stdscr

    @property
    def A_STANDOUT(self):
        return curses.A_STANDOUT

    @property
    def A_DIM(self):
        return curses.A_DIM

    @property
    def A_BOLD(self):
        return curses.A_BOLD

    @property
    def A_STANDOUT(self):
        return curses.A_STANDOUT

    @property
    def ACS_ULCORNER(self):
        return curses.ACS_ULCORNER

    @property
    def ACS_LLCORNER(self):
        return curses.ACS_LLCORNER

    @property
    def ACS_URCORNER(self):
        return curses.ACS_URCORNER

    @property
    def ACS_LRCORNER(self):
        return curses.ACS_LRCORNER

    @property
    def ACS_HLINE(self):
        return curses.ACS_HLINE

    @property
    def ACS_VLINE(self):
        return curses.ACS_VLINE

    def getmaxyx(self):
        return self.stdscr.getmaxyx()

    def chgat(self, y, x, count, attr):
        self.stdscr.chgat(y, x, count, attr)

    def addch(self, y, x, ch):
        self.stdscr.addch(y, x, ch)

    def addstr(self, y, x, text):
        self.stdscr.addstr(y, x, text)

    def hline(self, y, x, linechar, count):
        self.stdscr.hline(y, x, linechar, count)

    def vline(self, y, x, linechar, count):
        self.stdscr.vline(y, x, linechar, count)

    def erase(self):
        self.stdscr.erase()


def main(stdscr, *args):
    # Clear screen
    stdscr.clear()
    curses.curs_set(0)
    curses.raw()
    stdscr.keypad(True)
    stdscr.refresh()

    if not len(args):
        dirpath = "."
    else:
        dirpath = args[0]

    context = DisplayContext(CursesWindow(stdscr), DirFileSet(dirpath))
    context.fullRedraw()
    stdscr.refresh()

    o = 0

    while not context.wantsToExit:
        key = stdscr.getkey()

        context.receiveChar(key)

        stdscr.refresh()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("bblime [dir]")
        print()
        print("Edit all the files within 'dir'.")
        sys.exit(-1)

    sys.exit(curses.wrapper(lambda stdscr: main(stdscr, *sys.argv[1:])))
