import net from 'net'
import { Client, VoiceChannel } from 'discord.js'
import { SOURCE_CHANNEL, USER_TO_LISTEN_TO } from './options'

const TWINS_SOCKET = '/connection/communicate.sock'

const client = new Client()
const TOKEN = process.env.ALPACA_TWINS_TOKEN

const COMMAND_PREFIX = 'OK,あるぱか '

client.on('debug', console.log)

client.login(TOKEN)

client.on('message', async (message) => {
  if (message.content === COMMAND_PREFIX + '入れ') {
    if (message.member === null) {
      return
    }
    if (message.member.voice.channel) {
      console.log(message.member)
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
  const connection = await (client.channels.cache.get(SOURCE_CHANNEL) as VoiceChannel).join()
  const userToListenTo = await client.users.fetch(USER_TO_LISTEN_TO)

  const connect = () => {
    try {
      const sock = net.createConnection(TWINS_SOCKET)

      const stream = connection.receiver.createStream(userToListenTo, {end: 'manual'})
      stream.on('data', data => {
        sock.write(data)
        console.log(data)
      })

    } catch (error) {
      console.log('waiting...')
      setTimeout(connect, 1000)
    }
  }
  setTimeout(connect, 1000)
  
})
