from adafruit_bitmap_font import bitmap_font
import time
import math
from .textwrap import wrap
from .picotui import screen, widgets, menu, defs
from .keys import get_keymaps
try:
    from .pyte import Stream as PyteStream, Screen as PyteScreen
except ImportError as e:
    print(e)
try:
    from collections import defaultdict # noqa
    on_device = False
except ImportError:
    on_device = True
import gc
    
if on_device:
    import displayio
    import bitmaptools
    import terminalio
    gc.collect()
else:
    import sdl2.ext

__all__ = ["Terminal"]

class Terminal:
    pixel_width = None
    pixel_height = None
    width = None
    height = None

    font = None
    font_width = None
    font_height = None

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

    lines = []
    amount_of_lines = 1

    # Picotui widgets
    root_container = None
    menubar = None
    messages = None
    statusbar = None
    inputbox = None
    prompt = None

    events = []
    kb_state = 0

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
                        self.pyte_screen.dirty.add(self.pyte_screen.cursor.y)
                        state_updated = True
                    elif event.key.keysym.sym in [sdl2.SDLK_RALT, sdl2.SDLK_LALT]:
                        self.kb_state = 2
                        self.pyte_screen.dirty.add(self.pyte_screen.cursor.y)
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
                if input == "alt":
                    gc.collect()
                    self.kb_state += 1
                    state_updated = True
                    if self.kb_state > 2:
                        self.kb_state = 0
                    self.pyte_screen.dirty.add(self.pyte_screen.cursor.y)
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
                        self.comms.send_message(text)
                        self.root_container.handle_input(defs.KEY_ENTER)
                        self.inputbox.set("")
                        self.inputbox.redraw()
                        self.pyte_screen.dirty.add(self.pyte_screen.cursor.y)
                    else:
                        self.menubar.handle_input(defs.KEY_ENTER)
                elif input == "bsp":
                    self.root_container.handle_input(defs.KEY_BACKSPACE)
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
            gc.collect()
            return state_updated
        return state_updated

    def handle_comms(self):
        self.comms.loop()
        received_messages = self.comms.get_messages()
        if len(received_messages) > 0:
            for message in received_messages:
                self.add_line("[%02d:%02d] <%s> %s" % (message.tstamp.tm_hour, message.tstamp.tm_min, self.comms.format_address(message.src), message.text))

            self.comms.clear_messages()
            self.render_lines()
            gc.collect()
            return True
        return False
        
    def should_quit(self):
        if not on_device:
            for event in self.events:
                if event.type == sdl2.SDL_QUIT:
                    return True
        return False

    def get_current_time(self):
        now = time.localtime()
        return "%02d:%02d" % (now.tm_hour, now.tm_min)

    def set_status_bar(self, text):
        self.statusbar.t = " [%s] [rosmo] [#general]" % (
            self.get_current_time())
        self.statusbar.t = self.statusbar.t + (" " * (self.width - len(self.statusbar.t)))

    def add_line(self, line, timestamp=False):
        self.lines.append(line)

    def render_lines(self):
        range_start = len(self.lines)
        range_end = 0 if len(self.lines) < self.amount_of_lines else len(
            self.lines) - self.amount_of_lines
        result = []
        for idx in range(range_start, range_end, -1):
            wrapped = wrap(
                self.lines[idx - 1], self.width, indent1='| ')
            result = wrapped + result
            if len(result) > self.amount_of_lines:
                break
        if len(result) > self.amount_of_lines:
            result = result[len(result)-self.amount_of_lines:len(result)]
        self.messages.set_lines(result)
        self.messages.redraw()

    def __init__(self, display=None, width=320, height=240, input_fn=None, comms=None):
        self.input_fn = input_fn
        self.comms = comms
        self.pixel_width = width
        self.pixel_height = height
        self.display = display

        keymap_normal, keymap_shift, keymap_alt = get_keymaps()
        for ridx, row in enumerate(keymap_normal):
            for cidx, col in enumerate(row):
                self.keymap_shift[col] = keymap_shift[ridx][cidx]
                self.keymap_alt[col] = keymap_alt[ridx][cidx]

        if not on_device:
            self.font = bitmap_font.load_font("fonts/gohu-14.pcf")
        else:
            self.font = terminalio.FONT
        font_box = self.font.get_bounding_box()
        self.font_width = font_box[0]
        self.font_height = font_box[1]
        self.width = math.floor(self.pixel_width / self.font_width)
        self.height = math.floor(self.pixel_height / self.font_height)
        self.amount_of_lines = self.height - 3
                
        self.pyte_screen = PyteScreen(self.width, self.height)
        self.pyte_stream = PyteStream(self.pyte_screen)

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
            gc.collect()

            self.pico_palette = displayio.Palette((len(self.ansi_palette)) * 2)
            idx = 0
            for idx, colors in enumerate(self.ansi_palette):
                self.pico_palette[idx] = (colors[0][0] << 16) | (
                    colors[0][1] << 8) | colors[0][2]
                self.pico_palette[8 + idx] = (colors[1][0]
                                                << 16) | (colors[1][1] << 8) | colors[1][2]
            self.ansi_palette = None
            
            gc.collect()

            self.display_bitmap = displayio.Bitmap(self.pixel_width, self.pixel_height, 16)
            self.tilegrid = displayio.TileGrid(self.display_bitmap, pixel_shader=self.pico_palette)
            self.tilemap = []
            tiles_per_row = self.font.bitmap.width / self.font_width
            for tile_index in range(255):
                dy = int((math.floor(tile_index / tiles_per_row)) * self.font_height)
                dx = int((tile_index % tiles_per_row) * self.font_width) 
                self.tilemap.append((dx, dy))

            self.ui_group.append(self.tilegrid)

            gc.collect()

        screen.WRITE_FUNC = self.picotui_write
        screen.SCREEN_SIZE = (self.width, self.height)
        screen.Screen.set_screen_redraw(self.screen_redraw)

        self.root_container = widgets.Container(0, 0, self.width, self.height)

        self.messages = widgets.WMultiEntry(
            self.width, self.amount_of_lines, ["foo", "bar"], fg=7, bg=0)
        self.render_lines()
        self.root_container.add(0, 1, self.messages)

        self.statusbar = widgets.WLabel("", self.width, fg=15, bg=4)
        self.set_status_bar("NEW MESSAGE")
        self.root_container.add(0, self.height - 2, self.statusbar)

        self.prompt = widgets.WLabel("> ", 2, fg=13, bg=0)
        self.root_container.add(0, self.height - 1, self.prompt)

        self.inputbox = widgets.WTextEntry(self.width - 3, "", bg=0)
        self.root_container.add(2, self.height - 1, self.inputbox)
        self.root_container.redraw()

        self.menubar = menu.WMenuBar(
            [("Settings", None), ("Radio", None), ("Debug", None)])
        self.menubar.permanent = True
        self.menubar.redraw()

        self.root_container.change_focus(self.inputbox)
        gc.collect()

    def screen_redraw(self, allow_cursor=False):
        #screen.Screen.attr_color(7, 0)
        #screen.Screen.cls()
        #screen.Screen.attr_reset()
        #self.root_container.redraw()
        pass

    def picotui_write(self, buf):
        self.pyte_stream.feed(buf.decode("UTF-8"))

    def draw_pc(self):
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window.window)
        cursor_x = self.pyte_screen.cursor.x
        cursor_y = self.pyte_screen.cursor.y
        for y in self.pyte_screen.dirty:
            for x in range(self.width):
                data = self.pyte_screen.buffer[y][x].data
                fg_color = self.pyte_screen.buffer[y][x].fg
                bg_color = self.pyte_screen.buffer[y][x].bg
                if y == cursor_y and x == cursor_x:
                    fg_color = 9
                    bg_color = 6
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
        self.pyte_screen.dirty.clear()

    def draw_device(self):
        cursor_x = self.pyte_screen.cursor.x
        cursor_y = self.pyte_screen.cursor.y
        for y in self.pyte_screen.dirty:
            for x in range(self.width):
                tx = self.font_width * x
                ty = self.font_height * y
                buf = self.pyte_screen.buffer[y][x]
                data = buf.data
                fg_color = buf.fg
                bg_color = buf.bg
                if y == cursor_y and x == cursor_x:
                    fg_color = 9
                    bg_color = 6
                    if self.kb_state == 1:
                        data = "^"
                    elif self.kb_state == 2:
                        data = "|"
                if data != " ":
                    idx = ord(data)
                    glyph = self.font.get_glyph(idx)
                    dx, dy = self.tilemap[glyph.tile_index]
                    for fy in range(self.font_height):
                        for fx in range(self.font_width):
                            if glyph.bitmap[dx + fx, dy + fy] == 1:
                                self.display_bitmap[tx + fx, ty + fy] = fg_color
                            else:
                                self.display_bitmap[tx + fx, ty + fy] = bg_color
                else:
                    bitmaptools.fill_region(self.display_bitmap, tx, ty, tx + self.font_width, ty + self.font_height, bg_color)

        self.pyte_screen.dirty.clear()
        self.display.refresh()
        gc.collect()

    def draw(self):
        if not on_device:
            self.draw_pc()
        else:
            self.draw_device()
