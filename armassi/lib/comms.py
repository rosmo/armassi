import os
try:
    import busio
    import armachat_lora
    import aesio
except ImportError:
    pass

from collections import namedtuple
import time
import struct
import binascii

import minipb

MeshtasticData = minipb.Wire([
    ("portnum", "t"),
    ("payload", "a"),
    ("want_response", "b"),
    ("dest", "I"),
    ("source", "I"),
    ("request_id", "I"),
    ("reply_id", "I"),
    ("emoji", "I"),
])

MeshtasticNodeInfo = minipb.Wire([
    ("num", "T"),
    ("user", [
        ("id", "U"),
        ("long_name", "U"),
        ("short_name", "U"),
        ("macaddr", "a"),
        ("hw_model", "x"),
        ("is_licensed", "b"),
    ]),
    ("position", "x"),
    ("snr", "f"),
    ("last_heard", "I"),
    ("device_metrics", "x"),
])


class Communication:
    broadcast = b"\xff\xff\xff\xff"

    def __init__(self, lora_config=None, my_address=None, remote_address=None, encryption_key=None, encryption_iv=None, nick=None):
        self.lora_config = lora_config
        self.lora = None
        self.my_address = my_address
        self.messages = []
        self.encryption_key = encryption_key
        self.encryption_key = None
        self.encryption_iv = encryption_iv
        self.idx = 0
        self.nick = nick

    Message = namedtuple(
        "Message", ["dst", "src", "id", "flags", "s", "rssi", "tstamp", "packet"])

    def initialize(self):
        if "m" not in self.lora_config:
            self.lora_config = {"m": "e5"}
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

        self.announce_myself()

    def get_messages(self):
        return self.messages

    def clear_messages(self):
        self.messages = []

    def format_address(self, address):
        return str(binascii.hexlify(address), "utf-8")

    def loop(self):
        if self.lora and self.lora.rx_done():
            message = self.receive()
            if message:
                refresh = False
                if message.packet['portnum'] == 1: # Text message
                    self.messages.append(message)
                    refresh = True
                if message.packet['portnum'] == 4: # Nodeinfo message
                    node_info = MeshtasticNodeInfo.decode(message.packet['payload'])
                    if node_info:
                        refresh = self.nick[3](node_info['user']['macaddr'], node_info['user']['id'])
                        if refresh:
                            self.messages.append("-!- %s [%s@%s] has joined." % (node_info['user']['id'], node_info['user']['short_name'], binascii.hexlify(node_info['user']['macaddr']).decode("utf-8")))
                        self.announce_myself()
                return refresh
        self.idx += 1
        if self.idx > 1000:
            self.announce_myself()
            self.idx = 0
        return False

    def announce_myself(self):
        nodeinfo_packet = {
            "num": int.from_bytes(self.my_address, 'little'),
            "user": {
                "id": self.nick[0](),
                "long_name": self.nick[0](),
                "short_name": self.nick[0]()[0:2].upper(),
                "macaddr": self.my_address,
                "hw_model": None,
                "is_licensed": False,
            },
            "position": None,
            "snr": self.lora.last_snr,
            "last_heard": None,
            "device_metrics": None,
        }
        packet = {
            "portnum": 4,
            "payload": MeshtasticNodeInfo.encode(nodeinfo_packet),
            "want_response": None,
            "dest": None,
            "source": None,
            "request_id": None,
            "reply_id": None,
            "emoji": None,
        }
        msg_id = os.urandom(4)
        self.send(self.my_address, self.broadcast, packet, id=msg_id, want_ack=False)

    def send_message(self, remote_address=b"\xff\xff\xff\xff", text=""):
        msg_id = os.urandom(4)
        packet = {
            "portnum": 1,
            "payload": text.encode("utf-8"),
            "want_response": None,
            "dest": None,
            "source": None,
            "request_id": None,
            "reply_id": None,
            "emoji": None,
        }
        msg = self.send(self.my_address, remote_address,
                        packet, id=msg_id, want_ack=True)
        if msg:
            self.messages.append(msg)
            return True
        return False

    def receive(self):
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
        if bytearray(self.my_address) != header[0:4] and header[0:4] != self.broadcast:
            return None

        payload = bytes(packet[16:])
        if self.encryption_key:
            cipher = aesio.AES(self.encryption_key,
                               aesio.MODE_CTR, self.encryption_iv)
            decrypted_out = bytearray(len(payload))
            cipher.decrypt_into(payload, decrypted_out)
            payload = decrypted_out

        try:
            decoded_packet = MeshtasticData.decode(payload)
        except Exception as e:
            print("Failed to decode packet", str(e))
            return 
        
        msgID = int.from_bytes(packet[8:12], 'big')
        msg = self.Message(dst=self.my_address, src=packet[4:8], id=msgID, flags=packet[15],
                           s=self.lora.last_snr, rssi=self.lora.last_rssi, tstamp=time.localtime(), packet=decoded_packet)
        return msg

    def send(self, sender, destination, packet, id, hops=3, want_ack=True):
        dest = bytearray(destination)
        src = bytearray(sender)
        # msg_id = struct.pack("!I", id)
        msg_id = bytearray(id)
        flags = bytearray(struct.pack(
            "!I", hops | 0b1000 if want_ack else hops & 0b0111))

        packet_bytes = MeshtasticData.encode(packet)
        payload = bytearray(len(packet_bytes))
        if self.encryption_key:
            nonce = src + msg_id

            cipher = aesio.AES(self.encryption_key,
                               aesio.MODE_CTR, nonce)
            encrypted_out = bytearray(len(payload))
            cipher.encrypt_into(packet_bytes, encrypted_out)
            payload = encrypted_out
        else:
            payload = packet_bytes
        header = bytearray(dest + src + msg_id + flags)
        if self.lora_config["m"] != "e5":
            body = bytearray(header) + bytearray(payload)
            self.lora.send(body)
            return self.Message(dst=header[4:8], src=self.my_address, id=id, flags=header[15],
                                s=self.lora.last_snr, rssi=self.lora.last_rssi, tstamp=time.localtime(), packet=packet)
        return None
