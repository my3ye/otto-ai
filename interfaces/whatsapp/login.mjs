import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  useMultiFileAuthState,
} from 'baileys'
import P from 'pino'
import qrcode from 'qrcode-terminal'

const logger = P({ level: 'silent' })

const AUTH_DIR = '/home/web3relic/interfaces/whatsapp/auth_state'

async function start() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)
  const { version } = await fetchLatestBaileysVersion()

  console.log(`Baileys v${version.join('.')} -- scan QR code with WhatsApp\n`)

  const sock = makeWASocket({
    version,
    logger,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    generateHighQualityLinkPreview: true,
  })

  sock.ev.on('creds.update', saveCreds)

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update

    if (qr) {
      console.clear()
      console.log('Scan this QR code with WhatsApp:\n')
      qrcode.generate(qr, { small: true })
      console.log('\nOpen WhatsApp > Settings > Linked Devices > Link a Device')
    }

    if (connection === 'open') {
      console.log('\nConnected! Logged in as', sock.user?.name || sock.user?.id)
      console.log('Auth state saved to', AUTH_DIR)
      console.log('You can close this with Ctrl+C.\n')
    }

    if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode
      if (code !== DisconnectReason.loggedOut) {
        console.log('Connection lost, reconnecting...')
        start()
      } else {
        console.log('Logged out.')
        process.exit(0)
      }
    }
  })
}

start()
