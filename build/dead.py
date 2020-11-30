from discord.ext import commands
import asyncio
import logging
import os
import socket
import time
import traceback


bot = commands.Bot(command_prefix='OK,あるぱか ')
channel_name = os.environ['CHANNEL_NAME']
token = os.environ['ALPACA_TWINS_TOKEN']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 相方からの情報受信用
sock.setblocking(False)
sock.bind(('dead', 50007))


@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, 'original', error)
    error_msg = ''.join(
        traceback.TracebackException.from_exception(orig_error).format())
    print(error_msg)


@bot.command(aliases=['繋いで', '繋げ', '入って', '入れ'])
async def connect(ctx):
    try:
        # 同時に繋ぎに行くと競合して片方失敗するので相方の成功を待つ
        loop = asyncio.get_running_loop()
        logging.info("listen start...")
        recv = await loop.sock_recv(sock, 1024)
        logging.info('recieved: {}'.format(recv))

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

        buffer = []
        while True:
            packet = await loop.sock_recv(sock, 512)
            asyncio.run_coroutine_threadsafe(client.ws.speak(), client.loop)
            buffer.append(packet)
            client.send_audio_packet(packet, encode=False)

            if len(buffer) == 50:
                logging.info('sent.')
                buffer = []
                time.sleep(3)

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

sock.close()
