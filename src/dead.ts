import net from 'net'
import { Client, VoiceChannel } from 'discord.js'
import { DESTINATION_CHANNEL } from './options'
const fs = require('fs')

const TWINS_SOCKET = '/connection/communicate.sock'

const client = new Client()
const TOKEN = process.env.ALPACA_TWINS_TOKEN

const COMMAND_PREFIX = 'OK,あるぱか '

client.on('debug', console.log)

client.login(TOKEN)

client.on('message', async (message) => {
  if (message.content === COMMAND_PREFIX + '入れ') {
    if (message.guild === null) {
      return
    }
    if (message.member.voice.channel) {
      console.log(message.member)
      await message.member.voice.channel.join()
      if (client.voice === null)
      {
        console.log('client.voice is null.')
        return
      }
      console.log(client.voice.connections)
    } else {
      message.reply('You need to join a voice channel first!')
    }
  }
})

client.on('message', (message) => {
  if (message.content === COMMAND_PREFIX + '出ろ') {
    if (client.voice === null)
    {
      return
    }
    client.voice.connections.forEach(conn => conn.disconnect())
  }
})

client.on('ready', async () => {
  const connection = await (client.channels.cache.get(DESTINATION_CHANNEL) as VoiceChannel).join()

  const server = net.createServer(stream => {
    new Promise(res => connection.play(stream, {"type":"opus"}).on('finish', res))
    stream.on('data', data => console.log(data))
  })

  try {
    fs.unlinkSync(TWINS_SOCKET) // it's a garbage if exists.
  } catch (doesNotExist) {}

  server.listen(TWINS_SOCKET)
  
})
