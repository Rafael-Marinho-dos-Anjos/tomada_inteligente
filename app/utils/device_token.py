from random import choice


chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345678"

def gen_device_token(len: int = 4) -> str:
    token = "".join([choice(chars) for _ in range(len)])

    return token
