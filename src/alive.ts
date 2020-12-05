import net from 'net'
import { Client, VoiceChannel } from 'discord.js'
const prism = require('prism-media')
const fs = require('fs')

const TWINS_SOCKET = '/connection/communicate.sock'

const client = new Client()
const TOKEN = process.env.ALPACA_TWINS_TOKEN

const COMMAND_PREFIX = 'OK,あるぱか '

const options = {
  sourceChannel: '000000000000000000',
  destinationChannel: '000000000000000000',
  sourceUser: '000000000000000000'
}

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

  const connection = await message.member.voice.channel.join()
  const userToListenTo = await client.users.fetch(options.sourceUser)

  const connect = () => {
    try {
      const sock = net.createConnection(TWINS_SOCKET)

      const stream = connection.receiver.createStream(userToListenTo, {end: 'manual', mode: 'pcm'})
      const encoder = new prism.opus.Encoder({ channels: 2, rate: 48000, frameSize: 960 })
      stream.pipe(encoder)
      encoder.on('data', data => {
        sock.write(data)
        console.log(data)
      })
    } catch (error) {
      console.log('waiting...')
      setTimeout(connect, 1000)
    }
  }
  setTimeout(connect, 1000)
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
  const connection = await (client.channels.cache.get(options.sourceChannel) as VoiceChannel).join()
  const userToListenTo = await client.users.fetch(options.sourceUser)

  const connect = () => {
    try {
      const sock = net.createConnection(TWINS_SOCKET)

      const stream = connection.receiver.createStream(userToListenTo, {end: 'manual', mode: 'pcm'})
      const encoder = new prism.opus.Encoder({ channels: 2, rate: 48000, frameSize: 960 })
      stream.pipe(encoder)
      encoder.on('data', data => {
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
