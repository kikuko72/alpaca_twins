from discord.ext import commands
from typing import List
import logging
import os
import recieve_voice
import socket
import traceback


bot = commands.Bot(command_prefix='OK,あるぱか ')
channel_name = os.environ['CHANNEL_NAME']
token = os.environ['ALPACA_TWINS_TOKEN']

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, 'original', error)
    error_msg = ''.join(
        traceback.TracebackException.from_exception(orig_error).format()
    )
    print(error_msg)


@bot.command(aliases=['繋いで', '繋げ', '入って', '入れ'])
async def connect(ctx):
    try:
        channel = await commands.VoiceChannelConverter().convert(
            ctx,
            channel_name
        )
        client = await channel.connect()

        endpoint_address = (client.endpoint_ip, client.voice_port)
        external_address = (client.ws._connection.ip,
                            client.ws._connection.port)
        logging.info('endpoint address:{}'.format(endpoint_address))
        logging.info('external address:{}'.format(external_address))

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setblocking(False)
            # 同時に繋ぎに行くと競合して片方失敗するので先に繋いで相方に知らせる
            s.sendto(b'Ready', ('dead', 50007))

            vp = recieve_voice.VoiceParser(client)

            alerted: bool = False
            buffer: List[recieve_voice.AlpacaPacket] = []
            while True:
                recv = await client.ws.loop.sock_recv(
                    client.ws._connection.socket,
                    2048  # どのくらい必要か不明。1人で「あー」と言ってみたくらいだと150もあれば十分そうだった
                )
                second_byte = recv[1] if len(recv) > 1 else None
                if not second_byte:
                    logging.debug('recieved empty or invalid bytes.')
                    continue
                elif 200 <= second_byte and second_byte >= 204:
                    logging.debug('recieved RTCP.')
                    continue

                logging.debug('recieved RTP.')
                try:
                    packet = recieve_voice.RTPPacket(recv)
                    if packet.should_be_ignore:
                        continue

                    logging.debug(packet)

                    alpaca_packet = vp.calculate_alpaca_packet(packet)
                    buffer.append(alpaca_packet)
                    if len(buffer) == 50:
                        stream = map(lambda ap: ap.decrypted_opus, sorted(
                            buffer, key=lambda ap: ap.seq_no))
                        for media in stream:
                            s.sendto(bytes(media), ('dead', 50007))
                        buffer = []
                        logging.info('sent.')

                except ValueError:
                    traceback.print_exc()
                    if not alerted:
                        await ctx.send('なんか変なデータ来たけど')
                        alerted = True

    except Exception:
        traceback.print_exc()
        await ctx.send('だめだった')


@bot.command(aliases=['出てけ', '出て', '出ろ', '切って', '切れ'])
async def disconnect(ctx):
    voice_client = ctx.message.guild.voice_client

    if not voice_client:
        await ctx.send('だめだった')
        return

    await voice_client.disconnect()

bot.run(token)
