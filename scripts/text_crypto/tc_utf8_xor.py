from math import ceil
import secrets

from PIL import Image


MAGIC = b"VCT1"
HEADER_SIZE = len(MAGIC) + 4
SHARE_WIDTH = 256


def get_config():
    return {
        "name": "Text - UTF-8 Two-Share Encryption",
        "description": get_description(),
        "requirements": get_requirements(),
        "encrypt": encrypt,
        "decrypt": decrypt,
        "extension": "png",
        "image_type": "L",
        "result_type": "text",
    }


def get_requirements():
    return {
        "encryption": {
            "num_images": 0,
            "parameters": {
                "text": {
                    "type": "text",
                    "label": "Text to encrypt:",
                    "default": "",
                }
            },
        },
        "decryption": {"num_images": 2, "parameters": {}},
    }


def get_description():
    return {
        "text": "Encrypts UTF-8 text into two PNG shares. Both shares are required to recover the original text.",
        "links": [],
    }


def encrypt(text):
    if not isinstance(text, str) or not text:
        raise ValueError("Enter text to encrypt.")

    payload = text.encode("utf-8")
    data = MAGIC + len(payload).to_bytes(4, "big") + payload
    share_one = secrets.token_bytes(len(data))
    share_two = bytes(left ^ right for left, right in zip(data, share_one))
    return _bytes_to_image(share_one), _bytes_to_image(share_two)


def decrypt(share_one, share_two):
    if share_one.size != share_two.size:
        raise ValueError("Text shares must have matching dimensions.")

    first_bytes = bytes(share_one.convert("L").getdata())
    second_bytes = bytes(share_two.convert("L").getdata())
    data = bytes(left ^ right for left, right in zip(first_bytes, second_bytes))

    if len(data) < HEADER_SIZE or data[:len(MAGIC)] != MAGIC:
        raise ValueError("These images are not valid text shares.")

    payload_length = int.from_bytes(data[len(MAGIC):HEADER_SIZE], "big")
    payload = data[HEADER_SIZE:HEADER_SIZE + payload_length]
    if len(payload) != payload_length:
        raise ValueError("The text shares are incomplete.")

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("The text shares could not be decoded.") from error


def _bytes_to_image(data):
    height = ceil(len(data) / SHARE_WIDTH)
    padded_data = data + bytes(SHARE_WIDTH * height - len(data))
    return Image.frombytes("L", (SHARE_WIDTH, height), padded_data)