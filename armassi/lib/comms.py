try:
    import busio
    import armachat_lora
    import aesio
except ImportError:
    pass

from collections import namedtuple
import time
import struct
import random

class Communication:
    def __init__(self, lora_config=None, my_address=None, remote_address=None, encryption_key=None, encryption_iv=None):
        self.lora_config = lora_config
        self.lora = None
        self.my_address = self.convert_address(my_address)
        self.remote_address = self.convert_address(remote_address)
        self.messages = []
        self.encryption_key = encryption_key
        self.encryption_iv = encryption_iv
        self.idx = 0

    Message = namedtuple(
        "Message", ["dst", "src", "id", "flags", "s", "rssi", "tstamp", "text"])

    def convert_address(self, address):
        return [int(i) for i in address.split(".")]
    
    def format_address(self, address):
        return ".".join([str(address[0]), str(address[1]), str(address[2]), str(address[3])])

    def initialize(self):
        if "m" not in self.lora_config:
            return

        if self.lora_config["m"] != "e5":
            spi = busio.SPI(
                self.lora_config["sck"], MOSI=self.lora_config["mosi"], MISO=self.lora_config["miso"])
            self.lora = armachat_lora.RFM9x(
                spi, self.lora_config["cs"], self.lora_config["hz"])
            self.lora.signal_bandwidth = self.lora_config["bw"]
            self.lora.coding_rate = self.lora_config["cr"]
            self.lora.spreading_factor = self.lora_config["sf"]
            self.lora.preamble_length = self.lora_config["pl"]
            self.lora.tx_power = self.lora_config["tx"]
            self.lora.low_datarate_optimize = self.lora_config["ld"]
            self.lora.listen()

    def get_messages(self):
        return self.messages

    def clear_messages(self):
        self.messages = []

    def loop(self):
        if self.lora and self.lora.rx_done():
            message = self.receive()
            if message:
                if message.flags & 0b1000 and not message.text.startswith("!"):
                     self.send(self.my_address, message.src, "!|" +
                                  str(message.rssi) + "|" + str(message.s), id=message.id, want_ack=False)
                self.messages.append(message)
                return True
        return False

    def send_message(self, text):
        msg_id = random.randint(0, 2147483647) 
        msg = self.send(self.my_address, self.remote_address, text, id=msg_id, want_ack=True)
        if msg:
            self.messages.append(msg)
            return True
        return False

    def receive(self):
        packet_text = None
        header = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        packet = self.lora.receive()
        if packet is None:
            print("Receiver error")
            return None

        packetSize = len(packet)
        if packetSize < 16:
            print("Short packet <16")
            return None

        header = packet[0:16]
        if bytearray(self.my_address) != header[0:4]:
            return None

        payload = bytes(packet[16:])
        if self.encryption_key:
            cipher = aesio.AES(self.encryption_key,
                               aesio.MODE_CTR, self.encryption_iv)
            decrypted_out = bytearray(len(payload))
            cipher.decrypt_into(payload, decrypted_out)
            payload = decrypted_out

        try:
            packet_text = str(payload, "utf-8")
        except UnicodeError:
            return None

        msgID = int.from_bytes(packet[8:12], 'big')
        msg = self.Message(dst=self.my_address, src=list(packet[4:8]), id=msgID, flags=packet[15],
                           s=self.lora.last_snr, rssi=self.lora.last_rssi, tstamp=time.localtime(), text=packet_text)
        return msg

    def send(self, sender, destination, text, id=0, hops=3, want_ack=True):
        dest = bytearray(destination)
        src = bytearray(sender)
        msg_id = struct.pack("!I", id)
        flags = bytearray(struct.pack("!I", hops|0b1000 if want_ack else hops&0b0111))
        
        payload = bytearray(len(text))
        if self.encryption_key:
            cipher = aesio.AES(self.encryption_key,
                               aesio.MODE_CTR, self.encryption_iv)
            encrypted_out = bytearray(len(payload))
            cipher.encrypt_into(bytes(text, "utf-8"), encrypted_out)
            payload = encrypted_out
        else:
            payload.extend(text.encode("utf-8"))

        header = bytearray(dest + src + msg_id + flags)
        if self.lora_config["m"] != "e5":
            body = bytearray(header) + bytearray(payload)
            self.lora.send(body)
            if not text.startswith("!"):
                return self.Message(dst=list(header[4:8]), src=self.my_address, id=id, flags=header[15],
                                    s=self.lora.last_snr, rssi=self.lora.last_rssi, tstamp=time.localtime(), text=text)
        return None
