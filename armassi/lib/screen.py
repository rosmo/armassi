
__all__ = ( "Screen", "WRITE_FUNC", "SCREEN_SIZE" )


class Screen:
    buffer = []
    dirty = []
    width = 0
    height = 0
    cursor = (" ", 9, 6)
    cursor_on = True
    fmt = None
    x = 0
    y = 0

    def __init__(self, width, height):
        Screen.width = width
        Screen.height = height
        Screen.attr_reset()
        Screen.cls()

    @staticmethod
    def wr(s):
        if isinstance(s, (bytes, bytearray)):
            s = s.decode("utf-8")
        cx = Screen.x
        cy = Screen.y
        idx = 0
        slen = len(s)
        while idx < slen:
            c = s[idx]
            if c == "\n":
                cy += 1
            elif c == "\r":
                cx = 0
            if cx > (Screen.width - 1):
                cx = 0
                cy += 1
            if cy > (Screen.height - 1):
                Screen.buffer.pop(0)
                Screen.buffer.append([])
                cy -= 1
                for col in range(Screen.width):
                    Screen.buffer[cy].append((" ", Screen.fmt[0], Screen.fmt[1]))
                for dy in range(Screen.height):
                    Screen.dirty[dy] = True
            if c != "\n" and c != "\r":
                Screen.buffer[cy][cx] = (c, Screen.fmt[0], Screen.fmt[1])
                cx += 1
                Screen.dirty[cy] = True
            idx += 1
        if cx > (Screen.width - 1):
            cx = 0
            cy += 1

        Screen.x = cx
        Screen.y = cy

    @staticmethod
    def wr_fixedw(s, width):
        s = s[:width]
        Screen.wr(s)
        Screen.wr(" " * (width - len(s)))

    @staticmethod
    def clean():
        for k, v in enumerate(Screen.dirty):
            if v:
                Screen.dirty[k] = False
    
    @staticmethod
    def get_dirty():
        dirty_lines = []
        for k, v in enumerate(Screen.dirty):
            if v:
                dirty_lines.append(k)
        return dirty_lines

    @staticmethod
    def dirty_cursor():
        Screen.dirty[Screen.y] = True

    @staticmethod
    def cls():
        Screen.buffer = []
        Screen.dirty = []
        for row in range(Screen.height):
            Screen.buffer.append([])
            Screen.dirty.append([])
            for col in range(Screen.width):
                Screen.buffer[row].append((" ", Screen.fmt[0], Screen.fmt[1]))

    @staticmethod
    def goto(x, y):
        Screen.x = x
        Screen.y = y

    @staticmethod
    def clear_to_eol():
        cursor_x = Screen.x
        Screen.wr((Screen.width - Screen.x) * " ")
        Screen.x = cursor_x

    @staticmethod
    def clear_num_pos(num):
        cursor_x = Screen.x
        if num > 0:
            Screen.wr(num * " ")
        Screen.x = cursor_x

    @staticmethod
    def attr_color(fg, bg=-1):
        if bg != -1:
            Screen.fmt = (fg, bg)
        else:
            Screen.fmt = (fg, Screen.fmt[1])

    @staticmethod
    def attr_reset():
        Screen.fmt = (1, 0)

    @staticmethod
    def cursor(onoff):
        Screen.cursor_on = onoff
        
    def draw_box(self, left, top, width, height):
        bottom = top + height - 1
        self.goto(left, top)
        # "┌"
        self.wr(b"+")
        # "─"
        hor = b"-" * (width - 2)
        self.wr(hor)
        # "┐"
        self.wr(b"+")

        self.goto(left, bottom)
        # "└"
        self.wr(b"+")
        self.wr(hor)
        # "┘"
        self.wr(b"+")

        top += 1
        while top < bottom:
            # "│"
            self.goto(left, top)
            self.wr(b"|")
            self.goto(left + width - 1, top)
            self.wr(b"|")
            top += 1

    def clear_box(self, left, top, width, height):
        s = b" " * width
        bottom = top + height
        while top < bottom:
            self.goto(left, top)
            self.wr(s)
            top += 1

    def dialog_box(self, left, top, width, height, title=""):
        self.clear_box(left + 1, top + 1, width - 2, height - 2)
        self.draw_box(left, top, width, height)
        if title:
            pos = 1
            self.goto(left + pos, top)
            self.attr_color(14)
            self.wr(title)
            self.attr_reset()

    @classmethod
    def init_tty(cls):
        pass

    @classmethod
    def deinit_tty(cls):
        pass
    
    @classmethod
    def enable_mouse(cls):
        pass

    @classmethod
    def disable_mouse(cls):
        pass

    @classmethod
    def screen_size(cls):
       return (Screen.width, Screen.height)

    @classmethod
    def screen_redraw(cls, handler):
        pass    

    @classmethod
    def set_screen_redraw(cls, handler):
        pass

    @classmethod
    def set_screen_resize(cls, handler):
        pass
