try:
    from .lib.terminal import Terminal
    from .lib.comms import Communication
except ImportError:
    from armassi.lib.terminal import Terminal
    from armassi.lib.comms import Communication
import gc


class Armassi:
    terminal = None
    display = None

    def __init__(self, display=None, input_fn=None, lora_config={}, my_address=None, remote_address=None, encryption_key=None, encryption_iv=None):
        print("Armassi starting...")
        if display:
            display.auto_refresh = False
        self.comms = Communication(lora_config, my_address=my_address, remote_address=remote_address,
                                   encryption_key=encryption_key, encryption_iv=encryption_iv)
        self.terminal = Terminal(display=display, width=display.width if display else 320,
                                 height=display.height if display else 240, input_fn=input_fn, comms=self.comms)

    def main(self):
        gc.collect()
        self.terminal.draw()
        self.comms.initialize()
        while True:
            had_comms = self.terminal.handle_comms()
            had_inputs = self.terminal.process_inputs()
            if had_comms or had_inputs:
                self.terminal.draw()
            if self.terminal.should_quit():
                break


if __name__ == "__main__":
    armassi = Armassi()
    armassi.main()
