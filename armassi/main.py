import os
import sys
try:
    sys.path.append(os.path.join(os.getcwd(), "armassi", "lib"))
except Exception:
    sys.path.append(os.getcwd() + "/armassi/lib")
    
from terminal import Terminal
from comms import Communication
import gc
import time
import json
import random
import binascii
import board
import digitalio
import gc

gc.collect()

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
class Armassi:
    def __init__(self, display=None, input_fn=None, lora_config={}, my_address=None, remote_address=None, encryption_key=None, encryption_iv=None, beep=None):
        print("Armassi starting...")
        if display:
            display.auto_refresh = False

        ini_exists = False
        try:
            self.ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
            ini_exists = os.path.exists(self.ini_path)
        except Exception:
            self.ini_path = os.getcwd() + "/armassi/config.json"
            try:
                f = open(self.ini_path, "r")
                ini_exists = True
            except Exception:
                ini_exists = False
                
        self.json_config = None
        if ini_exists:
            with open(self.ini_path) as f:
                self.json_config = json.load(f)
        if not self.json_config:
            self.my_address = os.urandom(4)
            self.json_config = {"lora_mac": binascii.hexlify(self.my_address), "nick": ("user%d" % (random.randint(1, 1000)))}
            self.write_config()
        else:
            self.my_address = binascii.unhexlify(self.json_config["lora_mac"])
        encryption_key = None
        
        self.nicknames = {}
        nick = (self.get_nick, self.set_nick, self.get_nick_for_id, self.add_nick_for_id)
        gc.collect()
        self.comms = Communication(lora_config, my_address=self.my_address, remote_address=remote_address,
                                   encryption_key=encryption_key, encryption_iv=encryption_iv, nick=nick, beep=beep)
        
        gc.collect()
        self.terminal = Terminal(display=display, width=display.width if display else 320,
                                 height=display.height if display else 240, input_fn=input_fn, comms=self.comms, nick=nick)

    def write_config(self):
        with open(self.ini_path, "w") as outfile:
            json_config = self.json_config
            json_config["lora_mac"] = str(json_config["lora_mac"], "utf-8")
            outfile.write(json.dumps(json_config))

    def get_nick(self):
        return self.json_config["nick"]
    
    def get_nick_for_id(self, id):
        if id == self.my_address:
            return self.get_nick()
        hex_id = binascii.hexlify(id).decode("utf-8")
        if hex_id in self.nicknames:
            return self.nicknames[hex_id]
        return hex_id

    def add_nick_for_id(self, id, nick):
        hex_id = binascii.hexlify(id).decode("utf-8")
        if hex_id in self.nicknames and self.nicknames[hex_id] == nick:
            return False
        
        self.nicknames[hex_id] = nick
        return True

    def set_nick(self, nick):
        self.json_config["nick"] = nick
        self.write_config()

    def main(self):
        gc.collect()
        self.terminal.draw()
        self.comms.initialize()
        last_time = int(time.monotonic() * 1000)
        jiffies = 0
        while True:
            had_comms = self.terminal.handle_comms()
            had_inputs = self.terminal.process_inputs()
            current_time = int(time.monotonic() * 1000)
            if (current_time - last_time) > 250:
                self.terminal.handle_tick()
                last_time = current_time
                had_tick = True        
            else:
                had_tick = False
            if had_comms or had_inputs or had_tick:
                if led.value:
                    led.value = False
                else:
                    led.value = True
            
                self.terminal.draw()
            if self.terminal.should_quit():
                break
            jiffies += 1

if __name__ == "__main__":
    armassi = Armassi()
    armassi.main()
