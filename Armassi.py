from armassi.main import Armassi
display = None
try:
    from picomputer import *
except ImportError:
    pass

try:
    lora_config = {
        "m": model_lora,
        "hz": frequency,
        "bw": signal_bandwidth,
        "cr": coding_rate,
        "sf": spreading_factor,
        "pl": preamble_length,
        "tx": tx_power,
        "ld": 1,
        "cs": LORA_CS,
        "sck": LORA_SCK,
        "mosi": LORA_MOSI,
        "miso": LORA_MISO,
    }
except NameError:
    lora_config = {}
    myAddress = "1.1.1.1"
    password = "thisisnotanencryptionkey"
    passwordIv = "123567"
    destination = "2.2.2.2"

armassi = Armassi(display, input_fn=lambda: getKey(0), lora_config=lora_config,
                  my_address=myAddress, remote_address=destination, encryption_key=password, encryption_iv=passwordIv)
armassi.main()
