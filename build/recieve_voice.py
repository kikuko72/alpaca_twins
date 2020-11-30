from discord import VoiceClient
import logging
import nacl.secret
import traceback

logger = logging.getLogger(__name__)


class RTPHeaderFirstByte:
    def __init__(self, value: int):
        # 渡ってきてるデータでフラグが立ってることになってるけど無視しても復号化できてるので間違ってるかも
        self.x = (value >> 4) & 1

        self.cc = value & 15


class RTPPacket:
    def __init__(self, data: bytearray):
        try:
            first_byte = RTPHeaderFirstByte(data[0])
            if first_byte.x == 1:
                # Discordは拡張ヘッダーは使わない想定で実装をサボるが、万が一検出したらログに出す
                logger.debug('Extension flag is detected: {}'.format(data))

            if data[0] == 129:  # 誰も喋ってない時？
                header_length = 8
                self.should_be_ignore = True
            else:
                header_length = 12 + 4 * first_byte.cc
                self.should_be_ignore = False

            self.header = data[:header_length]
            self.seq_no = int.from_bytes(data[2:4], byteorder='big')
            self.timestamp = data[4:8]
            self.payload = data[header_length:]
            self.data = data
        except IndexError:
            raise ValueError(
                'uhh... maybe this is not a RTP packet: {}'.format(data))

    def __str__(self):
        data = self.data
        return '[{0:08b}][{1:08b}][{2}][{3}][{4}][{5}], header_len={6}, timestamp={7}, payload_len={8}'.format(
            data[0], data[1],
            int.from_bytes(data[2:4], byteorder='big'),
            int.from_bytes(data[4:8], byteorder='big'),
            int.from_bytes(data[8:12], byteorder='big'),
            int.from_bytes(data[12:16], byteorder='big'),
            len(self.header), int.from_bytes(self.timestamp, byteorder='big'), len(self.payload))


class AlpacaPacket:
    def __init__(self, timestamp, decrypted_payload):
        self.timestamp = timestamp
        self.decrypted_payload = decrypted_payload

    def as_bytes(self) -> bytearray:
        return self.timestamp + self.decrypted_payload


def _decrypt_xsalsa20_poly1305_lite(data, secret_key):
    box = nacl.secret.SecretBox(bytes(secret_key))
    nonce = bytearray(24)

    nonce[:4] = data[-4:]
    ciphertext = data[:-4]

    return box.decrypt(bytes(ciphertext), bytes(nonce))


supported_modes = {
    'xsalsa20_poly1305_lite': _decrypt_xsalsa20_poly1305_lite,
    'xsalsa20_poly1305_suffix': None,  # TODO
    'xsalsa20_poly1305': None,  # TODO
}


class VoiceParser:
    def __init__(self, voice_client: VoiceClient):
        self.client = voice_client

    def calculate_alpaca_packet(self, rtp_packet: RTPPacket) -> AlpacaPacket:
        mode = self.client.mode
        decrypt_func = supported_modes.get(mode)
        if not decrypt_func:
            message = 'unsupported mode: {}'.format(mode)
            logging.warning(message)
            raise ValueError(message)

        secret_key = self.client.secret_key
        logger.debug('header:{}'.format(rtp_packet.header))
        logger.debug('payload:{}'.format(rtp_packet.payload))
        logger.debug('secret key:{}'.format(secret_key))

        try:
            decrepted_payload = decrypt_func(rtp_packet.payload, secret_key)
            return AlpacaPacket(rtp_packet.timestamp, decrepted_payload)
        except Exception:
            traceback.print_exc()
