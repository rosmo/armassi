
__all__ = ( "Screen", "WRITE_FUNC", "SCREEN_SIZE" )

WRITE_FUNC = None
SCREEN_SIZE = (0, 0)

class Screen:

    @staticmethod
    def wr(s):
        # TODO: When Python is 3.5, update this to use only bytes
        if isinstance(s, str):
            s = bytes(s, "utf-8")
        WRITE_FUNC(s)

    @staticmethod
    def wr_fixedw(s, width):
        # Write string in a fixed-width field
        s = s[:width]
        Screen.wr(s)
        Screen.wr(" " * (width - len(s)))
        # Doesn't work here, as it doesn't advance cursor
        #Screen.clear_num_pos(width - len(s))

    @staticmethod
    def cls():
        Screen.wr(b"\x1b[2J")

    @staticmethod
    def goto(x, y):
        # TODO: When Python is 3.5, update this to use bytes
        Screen.wr("\x1b[%d;%dH" % (y + 1, x + 1))

    @staticmethod
    def clear_to_eol():
        Screen.wr(b"\x1b[0K")

    # Clear specified number of positions
    @staticmethod
    def clear_num_pos(num):
        if num > 0:
            Screen.wr("\x1b[%dX" % num)

    @staticmethod
    def get_attr_color(fg, bg=-1):
        if bg == -1:
            bg = fg >> 4
            fg &= 0xf
        # TODO: Switch to b"%d" % foo when py3.5 is everywhere
        if bg is None:
            if (fg > 8):
                return "\x1b[%d;1m" % (fg + 30 - 8)
            else:
                return "\x1b[%dm" % (fg + 30)
        else:
            assert bg <= 8
            if (fg > 8):
                return "\x1b[%d;%d;1m" % (fg + 30 - 8, bg + 40)
            else:
                return "\x1b[0;%d;%dm" % (fg + 30, bg + 40)
        return ""

    @staticmethod
    def attr_color(fg, bg=-1):
        Screen.wr(Screen.get_attr_color(fg, bg))

    @staticmethod
    def attr_reset():
        Screen.wr(b"\x1b[0m")

    @staticmethod
    def cursor(onoff):
        if onoff:
           Screen.wr(b"\x1b[?25h")
        else:
           Screen.wr(b"\x1b[?25l")
        
    def draw_box(self, left, top, width, height):
        # Use http://www.utf8-chartable.de/unicode-utf8-table.pl
        # for utf-8 pseudographic reference
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
        # doesn't work
        #self.wr("\x1b[%s;%s;%s;%s$z" % (top + 1, left + 1, top + height, left + width))
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
            #pos = (width - len(title)) / 2
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
       return SCREEN_SIZE

    # Set function to redraw an entire (client) screen
    # This is called to restore original screen, as we don't save it.
    @classmethod
    def set_screen_redraw(cls, handler):
        cls.screen_redraw = handler

    @classmethod
    def set_screen_resize(cls, handler):
        pass
