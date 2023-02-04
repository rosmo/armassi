from adafruit_bitmap_font import bitmap_font
import time
import math

from screen import Screen
from textwrap import wrap
from picotui import widgets, menu, defs
from keys import get_keymaps

try:
    pass
except ImportError as e:
    print(e)
try:
    from collections import defaultdict # noqa
    on_device = False
except ImportError:
    on_device = True
    
if on_device:
    import displayio
    import bitmaptools
    import terminalio
else:
    import sdl2.ext

__all__ = ["Terminal"]

class Terminal:

    ansi_palette = [
        ((0, 0, 0), (85, 87, 83)),
        ((128, 128, 128), (255, 255, 255)),
        ((128, 0, 0), (239, 41, 41)),
        ((0, 128, 6), (138, 226, 52)),
        ((128, 128, 0), (252, 233, 79)),
        ((0, 0, 128), (50, 175, 255)),
        ((128, 0, 128), (173, 127, 168)),
        ((0, 128, 128), (52, 226, 226)),
    ]

    keymap_shift = {}
    keymap_alt = {}

    def process_inputs(self):
        inputs = []
        state_updated = False
        if not on_device:
            self.events = sdl2.ext.get_events()
            for event in self.events:
                if event.type == sdl2.SDL_KEYUP:
                    if event.key.keysym.sym in [sdl2.SDLK_RSHIFT, sdl2.SDLK_LSHIFT]:
                        self.kb_state = 1
                        Screen.dirty_cursor()
                        state_updated = True
                    elif event.key.keysym.sym in [sdl2.SDLK_RALT, sdl2.SDLK_LALT]:
                        self.kb_state = 2
                        Screen.dirty_cursor()
                        state_updated = True
                    else:
                        input = None
                        if (event.key.keysym.sym >= sdl2.SDLK_a and event.key.keysym.sym <= sdl2.SDLK_z) or event.key.keysym.sym == sdl2.SDLK_SPACE:
                            input = chr(event.key.keysym.sym)
                        if event.key.keysym.sym == sdl2.SDLK_RETURN:
                            input = "ent"
                        if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
                            input = "bsp"
                        if input:
                            if self.kb_state == 1:
                                inputs.append(self.keymap_shift[input])
                                self.kb_state = 0
                            elif self.kb_state == 2:
                                inputs.append(self.keymap_alt[input])
                                self.kb_state = 0
                            else:
                                inputs.append(input)
        
        if on_device:
            input = self.input_fn()
            if input:
                current_input_time = int(time.monotonic() * 1000)
                if (current_input_time - self.last_input) < 180:
                    input = None
                else:
                    self.last_input = current_input_time

            if input:
                if input == "alt":
                    self.kb_state += 1
                    state_updated = True
                    if self.kb_state > 2:
                        self.kb_state = 0
                    Screen.dirty_cursor()
                    state_updated = True
                else:
                    if self.kb_state == 1:
                        inputs.append(self.keymap_shift[input])
                        self.kb_state = 0
                    elif self.kb_state == 2:
                        inputs.append(self.keymap_alt[input])
                        self.kb_state = 0
                    else:                    
                        inputs.append(input)

        if len(inputs) > 0:
            state_updated = True
            for input in inputs:
                if input == "ent":
                    if not self.menubar.focus:
                        text = self.inputbox.get()
                        if text.startswith("/"): # Command
                            cmd = text[1:].split(" ", 3)
                            if cmd[0].strip().lower() == "set" and len(cmd) == 3:
                                if cmd[1].strip().lower() == "nick":
                                    self.nick[1](cmd[2].strip())
                                    self.add_line("Nick changed to: %s" % (self.nick[0]()))
                        else:
                            self.comms.send_message(text=text)
                        
                        self.root_container.handle_input(defs.KEY_ENTER)
                        self.inputbox.set("")
                        self.inputbox.redraw()
                        Screen.dirty_cursor()
                    else:
                        self.menubar.handle_input(defs.KEY_ENTER)
                elif input == "bsp":
                    self.root_container.handle_input(defs.KEY_BACKSPACE)
                elif input == "lt" or input == "up":
                    self.kb_state = 0
                    Screen.dirty_cursor()
                    state_updated = True
                elif input == "up" or input == "dn":
                    if not self.menubar.focus:
                        self.menubar.focus = True
                        self.menubar.redraw()
                    else:
                        self.menubar.focus = False
                else:
                    if self.menubar.focus:
                        if input == "w" or input == "W":
                            self.menubar.handle_input(defs.KEY_UP)
                        elif input == "s" or input == "S":
                            self.menubar.handle_input(defs.KEY_DOWN)
                        elif input == "a" or input == "A":
                            self.menubar.handle_input(defs.KEY_LEFT)
                        elif input == "d" or input == "D":
                            self.menubar.handle_input(defs.KEY_RIGHT)
                    else:
                        self.root_container.handle_input(input.encode("utf-8"))
            return state_updated
        return state_updated

    def handle_comms(self):
        self.comms.loop()
        received_messages = self.comms.get_messages()
        if len(received_messages) > 0:
            for message in received_messages:
                if not isinstance(message, str):
                    message_text = message.packet['payload'].decode("utf-8")
                    self.add_line(message_text, nick_id=message.src, timestamp=message.tstamp)
                else:
                    self.add_line(message, timestamp=time.localtime())

            self.comms.clear_messages()
            self.render_lines()
            return True
        return False

    def handle_tick(self):
        self.update_status_bar()
        
    def should_quit(self):
        if not on_device:
            for event in self.events:
                if event.type == sdl2.SDL_QUIT:
                    return True
        return False

    def get_current_time(self):
        now = time.localtime()
        return "%02d:%02d" % (now.tm_hour, now.tm_min)

    def update_status_bar(self):
        previous_statusbar = self.statusbar.t
        self.statusbar.t = " [%s] [%s] [#general]" % (
            self.get_current_time(), self.nick[0]())
        self.statusbar.t = self.statusbar.t + (" " * (self.width - len(self.statusbar.t)))
        if self.statusbar.t != previous_statusbar:
            self.statusbar.redraw()

    def add_line(self, line, nick_id=None, timestamp=False):
        self.lines.append((time.localtime() if timestamp else None, nick_id, line))

    def render_lines(self):
        lines = []
        for k, v in enumerate(self.lines):
            nick = ""
            timestamp = ""
            if v[1]:
                nick = "<%s> " % (self.nick[2](v[1]))
            if v[0]:
                timestamp = "%02d:%02d " % (v[0].tm_hour, v[0].tm_min)
            lines.append("%s%s%s" % (timestamp, nick, v[2]))

        range_start = len(lines)
        range_end = 0 if len(lines) < self.amount_of_lines else len(
            lines) - self.amount_of_lines
        result = []
        for idx in range(range_start, range_end, -1):
            wrapped = wrap(
                lines[idx - 1], self.width, indent1='| ')
            result = wrapped + result
            if len(result) > self.amount_of_lines:
                break
        if len(result) > self.amount_of_lines:
            result = result[len(result)-self.amount_of_lines:len(result)]
        self.messages.set_lines(result)
        self.messages.redraw()

    def __init__(self, display=None, width=320, height=240, input_fn=None, comms=None, nick=None):
        self.last_input = (time.monotonic() * 1000)
        self.tick = True

        self.input_fn = input_fn
        self.comms = comms
        self.nick = nick

        self.pixel_width = width
        self.pixel_height = height
        self.display = display

        keymap_normal, keymap_alt, keymap_shift = get_keymaps()
        for ridx, row in enumerate(keymap_normal):
            for cidx, col in enumerate(row):
                self.keymap_shift[col] = keymap_shift[ridx][cidx]
                self.keymap_alt[col] = keymap_alt[ridx][cidx]

        if not on_device:
            self.font = bitmap_font.load_font("fonts/gohu-14.pcf")
        else:
            self.font = terminalio.FONT
        
        self.lines = []
        self.events = []
        self.kb_state = 0

        font_box = self.font.get_bounding_box()
        self.font_width = font_box[0]
        self.font_height = font_box[1]
        self.width = math.floor(self.pixel_width / self.font_width)
        self.height = math.floor(self.pixel_height / self.font_height)
        self.amount_of_lines = self.height - 3

        self.screen = Screen(self.width, self.height)
                
        if not on_device:
            sdl2.ext.init()

            self.sdl_window = sdl2.ext.Window("Armassi", size=(width, height))
            self.sdl_window.show()

            self.sdl_glyphs = {}

            self.sdl_palette = {}
            for idx, colors in enumerate(self.ansi_palette):
                self.sdl_palette[idx] = sdl2.SDL_Color(
                    colors[0][0], colors[0][1], colors[0][2])
                self.sdl_palette[8 + idx] = sdl2.SDL_Color(colors[1][0], colors[1][1], colors[1][2])

            for c in range(0x20, 0x7E):
                glyph = self.font.get_glyph(c)
                self.sdl_glyphs[c] = sdl2.ext.image.pillow_to_surface(
                    glyph.bitmap._image, as_argb=False)
                sdl2.SDL_SetPaletteColors(
                    self.sdl_glyphs[c].format.contents.palette, self.sdl_palette[1], 1, 1)
        else:
            self.ui_group = displayio.Group()
            self.display.show(self.ui_group)

            self.pico_palette = displayio.Palette((len(self.ansi_palette)) * 2)
            idx = 0
            for idx, colors in enumerate(self.ansi_palette):
                self.pico_palette[idx] = (colors[0][0] << 16) | (
                    colors[0][1] << 8) | colors[0][2]
                self.pico_palette[8 + idx] = (colors[1][0]
                                                << 16) | (colors[1][1] << 8) | colors[1][2]
            self.ansi_palette = None
            
            self.display_bitmap = displayio.Bitmap(self.pixel_width, self.pixel_height, 16)
            self.tilegrid = displayio.TileGrid(self.display_bitmap, pixel_shader=self.pico_palette)
            self.tilemap = []
            tiles_per_row = self.font.bitmap.width / self.font_width
            for tile_index in range(255):
                dy = int((math.floor(tile_index / tiles_per_row)) * self.font_height)
                dx = int((tile_index % tiles_per_row) * self.font_width) 
                self.tilemap.append((dx, dy))

            self.ui_group.append(self.tilegrid)

        self.root_container = widgets.Container(0, 0, self.width, self.height)

        self.messages = widgets.WMultiEntry(
            self.width, self.amount_of_lines, ["foo", "bar"], fg=1, bg=0)
        self.render_lines()
        self.root_container.add(0, 1, self.messages)

        self.statusbar = widgets.WLabel("", self.width, fg=9, bg=5)
        self.update_status_bar()
        self.root_container.add(0, self.height - 2, self.statusbar)

        self.prompt = widgets.WLabel("> ", 2, fg=1, bg=0)
        self.root_container.add(0, self.height - 1, self.prompt)

        self.inputbox = widgets.WTextEntry(self.width - 3, "", bg=0, fg=1)
        self.root_container.add(2, self.height - 1, self.inputbox)
        self.root_container.redraw()

        self.menubar = menu.WMenuBar(
            [("Settings", None), ("Radio", None), ("Debug", None)])
        self.menubar.permanent = True
        self.menubar.redraw()

        self.root_container.change_focus(self.inputbox)

    def draw_pc(self):
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window.window)
        cursor_x = Screen.x
        cursor_y = Screen.y
        dirty_lines = Screen.get_dirty()
        if len(dirty_lines) == 0 and Screen.cursor_is_dirty and Screen.cursor_on:
            if Screen.cursor_on and y == cursor_y and x == cursor_x:
                data = " "
                fg_color = 9
                bg_color = 6 if self.tick else 0
                if self.kb_state == 1:
                    data = "^"
                elif self.kb_state == 2:
                    data = "|"
                idx = ord(data)
                dst = sdl2.SDL_Rect(cursor_x * self.font_width,
                                    cursor_y * self.font_height)
                sdl2.SDL_SetPaletteColors(self.sdl_glyphs[idx].format.contents.palette, self.sdl_palette[fg_color], 1, 1)
                sdl2.SDL_SetPaletteColors(self.sdl_glyphs[idx].format.contents.palette, self.sdl_palette[bg_color], 0, 1)

                sdl2.SDL_BlitSurface(
                    self.sdl_glyphs[idx], None,
                    window_surface, dst
                )

        for y in dirty_lines:
            for x in range(self.width):
                data, fg_color, bg_color = Screen.buffer[y][x]
                if Screen.cursor_on and y == cursor_y and x == cursor_x:
                    fg_color = 9
                    bg_color = 6 if self.tick else 0
                    if self.kb_state == 1:
                        data = "^"
                    elif self.kb_state == 2:
                        data = "|"
                idx = ord(data)
                dst = sdl2.SDL_Rect(x * self.font_width,
                                    y * self.font_height)
                sdl2.SDL_SetPaletteColors(self.sdl_glyphs[idx].format.contents.palette, self.sdl_palette[fg_color], 1, 1)
                sdl2.SDL_SetPaletteColors(self.sdl_glyphs[idx].format.contents.palette, self.sdl_palette[bg_color], 0, 1)

                sdl2.SDL_BlitSurface(
                    self.sdl_glyphs[idx], None,
                    window_surface, dst
                )
        sdl2.SDL_UpdateWindowSurface(self.sdl_window.window)
        Screen.clean()

    def draw_device(self):
        cursor_x = Screen.x
        cursor_y = Screen.y
        dirty_lines = Screen.get_dirty()
        if len(dirty_lines) == 0 and Screen.cursor_is_dirty and Screen.cursor_on:
            tx = self.font_width * cursor_x
            ty = self.font_height * cursor_y
            data = " "
            fg_color = 9
            bg_color = 6 if self.tick else 0
            if self.kb_state == 1:
                data = "^"
            elif self.kb_state == 2:
                data = "|"
            if data != " ":
                idx = ord(data)
                glyph = self.font.get_glyph(idx)
                dx, dy = self.tilemap[glyph.tile_index]
                fy, fx = 0, 0
                while fy < self.font_height:
                    fx = 0
                    while fx < self.font_width:
                        if glyph.bitmap[dx + fx, dy + fy] == 1:
                            self.display_bitmap[tx + fx, ty + fy] = fg_color
                        else:
                            self.display_bitmap[tx + fx, ty + fy] = bg_color
                        fx += 1
                    fy += 1
            else:
                bitmaptools.fill_region(self.display_bitmap, tx, ty, tx + self.font_width, ty + self.font_height, bg_color)

        for y in dirty_lines:
            x = 0
            while x < (self.width - 1):
                tx = self.font_width * x
                ty = self.font_height * y
                data, fg_color, bg_color = Screen.buffer[y][x]
                if Screen.cursor_on and y == cursor_y and x == cursor_x:
                    fg_color = 9
                    bg_color = 6 if self.tick else 0
                    data = "_"
                    if self.kb_state == 1:
                        data = "^"
                    elif self.kb_state == 2:
                        data = "|"
                if data != " ":
                    idx = ord(data)
                    glyph = self.font.get_glyph(idx)
                    dx, dy = self.tilemap[glyph.tile_index]
                    fy, fx = 0, 0
                    while fy < self.font_height:
                        fx = 0
                        while fx < self.font_width:
                            if glyph.bitmap[dx + fx, dy + fy] == 1:
                                self.display_bitmap[tx + fx, ty + fy] = fg_color
                            else:
                                self.display_bitmap[tx + fx, ty + fy] = bg_color
                            fx += 1
                        fy += 1
                else:
                    bx = x
                    while bx < self.width:
                        if Screen.buffer[y][bx][0] != data or Screen.buffer[y][bx][2] != bg_color:
                            break
                        bx += 1
                    bx -= 1
                    bitmaptools.fill_region(self.display_bitmap, tx, ty, (bx * self.font_width) + self.font_width, ty + self.font_height, bg_color)
                    x = bx
                x += 1        
        Screen.clean()
        self.display.refresh()

    def draw(self):
        tick = True if int(time.monotonic() % 1 * 1000) < 500 else False
        if self.tick != tick:
            Screen.dirty_cursor()
            self.tick = tick
        if not self.menubar.focus:
            self.inputbox.set_cursor()

        if not on_device:
            self.draw_pc()
        else:
            self.draw_device()
