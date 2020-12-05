from discord import VoiceClient
import logging
import nacl.secret
import traceback

logger = logging.getLogger(__name__)


class RTPHeaderFirstByte:
    def __init__(self, value: int):
        '''
        拡張ヘッダ立ってるって言ってる人が他にも居るので
        誰か喋ってる時のパケットでは拡張ヘッダは立ってるっぽい
        https://github.com/discordjs/discord.js/issues/1310
        '''
        self.x = (value >> 4) & 1

        self.cc = value & 15


class RTPPacket:
    def __init__(self, data: bytearray):
        try:
            first_byte = RTPHeaderFirstByte(data[0])

            if data[0] == 129:  # 誰も喋ってない時？
                header_length = 8
                self.should_be_ignore = True
            else:
                header_length = 12 + 4 * first_byte.cc
                self.should_be_ignore = False

            self.has_extension = first_byte.x == 1
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
        return '[{0:08b}][{1:08b}][{2}][{3}][{4}][{5}], header_len={6}, timestamp={7}, payload_len={8}'.format(  # NOQA  許せ
            data[0], data[1],
            int.from_bytes(data[2:4], byteorder='big'),
            int.from_bytes(data[4:8], byteorder='big'),
            int.from_bytes(data[8:12], byteorder='big'),
            int.from_bytes(data[12:16], byteorder='big'),
            len(self.header), int.from_bytes(self.timestamp, byteorder='big'),
            len(self.payload))


class AlpacaPacket:
    def __init__(self, seq_no, timestamp, decrypted_opus):
        self.seq_no = seq_no
        self.timestamp = timestamp
        self.decrypted_opus = decrypted_opus

    def as_bytes(self) -> bytearray:
        return self.timestamp + self.decrypted_opus


def _decrypt_xsalsa20_poly1305_lite(data, secret_key) -> bytearray:
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


# 拡張ヘッダは暗号化されている部分に入ってるっぽい。https://twitter.com/vivid_UDON/status/1333404067410788352
def _drop_extension_header(has_extension: bool, decrepted_payload: bytearray):
    if not has_extension:
        return decrepted_payload

    extension_header_length = int.from_bytes(
        decrepted_payload[2:4], byteorder='big')
    logger.debug('dropped extension header. length:{}'.format(
        extension_header_length))
    return decrepted_payload[4 + extension_header_length:]


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
            logger.debug('decrepted payload:{}'.format(decrepted_payload))

            decrepted_opus = _drop_extension_header(
                rtp_packet.has_extension, decrepted_payload)

            return AlpacaPacket(rtp_packet.seq_no, rtp_packet.timestamp,
                                decrepted_opus)
        except Exception:
            traceback.print_exc()
