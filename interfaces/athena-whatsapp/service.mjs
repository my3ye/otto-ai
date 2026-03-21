import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  useMultiFileAuthState,
  downloadContentFromMessage,
} from 'baileys'
import P from 'pino'
import { appendFileSync, mkdirSync, createWriteStream } from 'fs'
import { createServer } from 'http'
import path from 'path'

const logger = P({ level: 'warn' })

const AUTH_DIR = '/home/web3relic/interfaces/athena-whatsapp/auth_state'
const LOG_DIR = '/home/web3relic/interfaces/athena-whatsapp/logs'
const DOC_DIR = '/mnt/media/documents'
const OTTO_API = 'http://localhost:8100'
const HTTP_PORT = 3002
const DEDUP_WINDOW_MS = 5 * 60 * 1000 // 5 minutes
const LIVENESS_INTERVAL_MS = 60 * 1000 // check every 60s
const LIVENESS_TIMEOUT_MS = 30 * 60 * 1000 // no activity for 30 min = stale (customer line gets long idle gaps)

mkdirSync(LOG_DIR, { recursive: true })
mkdirSync(DOC_DIR, { recursive: true })

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`
  console.log(line)
  appendFileSync(`${LOG_DIR}/whatsapp.log`, line + '\n')
}

function logMessage(msg) {
  const from = msg.key.remoteJid
  const name = msg.pushName || 'unknown'
  const direction = msg.key.fromMe ? 'OUT' : 'IN'

  // Extract content and type from all common message formats
  let text
  let messageType = 'text'
  let attachmentMeta = null

  const raw = msg.message || {}

  if (raw.conversation) {
    text = raw.conversation
    messageType = 'text'
  } else if (raw.extendedTextMessage?.text) {
    text = raw.extendedTextMessage.text
    messageType = 'text'
  } else if (raw.documentMessage) {
    const doc = raw.documentMessage
    const fname = doc.fileName || 'document'
    const mime = doc.mimetype || 'application/octet-stream'
    const caption = doc.caption ? ` — "${doc.caption}"` : ''
    text = `[Document: ${fname} (${mime})${caption}]`
    messageType = 'document'
    attachmentMeta = {
      fileName: doc.fileName || null,
      mimetype: doc.mimetype || null,
      caption: doc.caption || null,
      pageCount: doc.pageCount || null,
      fileLength: doc.fileLength ? String(doc.fileLength) : null,
    }
  } else if (raw.imageMessage) {
    const img = raw.imageMessage
    const caption = img.caption ? `: "${img.caption}"` : ''
    text = `[Image${caption}]`
    messageType = 'image'
    attachmentMeta = {
      mimetype: img.mimetype || null,
      caption: img.caption || null,
      width: img.width || null,
      height: img.height || null,
    }
  } else if (raw.videoMessage) {
    const vid = raw.videoMessage
    const caption = vid.caption ? `: "${vid.caption}"` : ''
    text = `[Video${caption}]`
    messageType = 'video'
    attachmentMeta = {
      mimetype: vid.mimetype || null,
      caption: vid.caption || null,
      seconds: vid.seconds || null,
    }
  } else if (raw.audioMessage) {
    const aud = raw.audioMessage
    const secs = aud.seconds ? ` (${aud.seconds}s)` : ''
    text = `[Audio message${secs}]`
    messageType = 'audio'
    attachmentMeta = {
      mimetype: aud.mimetype || null,
      seconds: aud.seconds || null,
      ptt: aud.ptt || false,
    }
  } else if (raw.stickerMessage) {
    text = '[Sticker]'
    messageType = 'sticker'
  } else if (raw.locationMessage) {
    const loc = raw.locationMessage
    text = `[Location: ${loc.degreesLatitude}, ${loc.degreesLongitude}]`
    messageType = 'location'
    attachmentMeta = {
      lat: loc.degreesLatitude,
      lng: loc.degreesLongitude,
      name: loc.name || null,
    }
  } else if (raw.contactMessage) {
    text = `[Contact: ${raw.contactMessage.displayName || 'unknown'}]`
    messageType = 'contact'
  } else {
    text = `[${Object.keys(raw).join(', ')}]`
    messageType = 'unknown'
  }

  const line = `[${new Date().toISOString()}] ${direction} | ${name} (${from}): ${text}`
  console.log(line)
  appendFileSync(`${LOG_DIR}/messages.log`, line + '\n')

  return { from, name, text, direction, messageType, attachmentMeta }
}

// ── Document downloader ──────────────────────────────────────────────
async function downloadDocument(msg, doc) {
  try {
    const ts = Date.now()
    const safeName = (doc.fileName || 'document').replace(/[^a-zA-Z0-9._-]/g, '_')
    const localPath = path.join(DOC_DIR, `${ts}_${safeName}`)

    const stream = await downloadContentFromMessage(doc, 'document')
    await new Promise((resolve, reject) => {
      const fileStream = createWriteStream(localPath)
      stream.pipe(fileStream)
      fileStream.on('finish', resolve)
      fileStream.on('error', reject)
      stream.on('error', reject)
    })

    log(`Document downloaded: ${localPath} (${doc.fileName})`)
    return localPath
  } catch (err) {
    log(`Document download failed: ${err.message}`)
    return null
  }
}

// ── Connection state ─────────────────────────────────────────────────
let _sock = null
let _connected = false
let _needsAuth = false
let _lastActivity = Date.now()
let _livenessTimer = null
let _startingUp = false
let _latestQR = null  // latest QR code string (null if not waiting for QR)

// ── Message dedup ────────────────────────────────────────────────────
// Track recently processed message IDs to avoid reprocessing on reconnect
const _processedMessages = new Map() // msgId -> timestamp

function isDuplicate(msgId) {
  if (_processedMessages.has(msgId)) return true
  _processedMessages.set(msgId, Date.now())
  // Prune old entries
  const cutoff = Date.now() - DEDUP_WINDOW_MS
  for (const [id, ts] of _processedMessages) {
    if (ts < cutoff) _processedMessages.delete(id)
    else break
  }
  return false
}

// ── Liveness monitor ─────────────────────────────────────────────────
function startLivenessMonitor() {
  if (_livenessTimer) clearInterval(_livenessTimer)
  _livenessTimer = setInterval(() => {
    if (!_connected) return
    const silentMs = Date.now() - _lastActivity
    if (silentMs > LIVENESS_TIMEOUT_MS) {
      log(`Connection stale (no activity for ${Math.round(silentMs / 1000)}s), forcing reconnect`)
      _connected = false
      // NOTE: do NOT call start() here — _sock.end() triggers connection.update('close')
      // which already schedules setTimeout(start, 5000). Calling start() here as well
      // creates a second concurrent connection (the double-connect bug).
      try { _sock?.end(undefined) } catch {}
      _sock = null
    }
  }, LIVENESS_INTERVAL_MS)
}

// ── Main connection ──────────────────────────────────────────────────
async function start() {
  if (_startingUp) return
  _startingUp = true

  try {
    // Clean up old socket
    if (_sock) {
      try { _sock.ev.removeAllListeners(); _sock.end(undefined) } catch {}
      _sock = null
    }
    _connected = false

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)
    const { version } = await fetchLatestBaileysVersion()

    log(`Starting Athena WhatsApp service (WA v${version.join('.')})`)

    const sock = makeWASocket({
      version,
      logger,
      auth: {
        creds: state.creds,
        keys: makeCacheableSignalKeyStore(state.keys, logger),
      },
      generateHighQualityLinkPreview: true,
      syncFullHistory: false, // skip full history sync — prevents AwaitingInitialSync delays
    })

    _sock = sock

    sock.ev.on('creds.update', saveCreds)

    sock.ev.on('connection.update', (update) => {
      const { connection, lastDisconnect, qr } = update
      _lastActivity = Date.now()

      if (qr) {
        _latestQR = qr
        log('QR code ready — scan with WhatsApp to link Athena')
      }

      if (connection === 'open') {
        _connected = true
        _latestQR = null  // clear QR once connected
        log(`Athena connected as ${sock.user?.name || sock.user?.id}`)
      }

      if (connection === 'close') {
        _connected = false
        _sock = null
        const code = lastDisconnect?.error?.output?.statusCode
        if (code !== DisconnectReason.loggedOut) {
          log(`Disconnected (code ${code}), reconnecting in 5s...`)
          setTimeout(start, 5000)
        } else {
          log('Logged out. Auth state cleared — QR re-scan required via login.mjs.')
          _needsAuth = true
          // Clear stale auth state so next login.mjs run starts fresh
          import('fs').then(({ rmSync }) => {
            try {
              rmSync(AUTH_DIR, { recursive: true, force: true })
              import('fs').then(({ mkdirSync: mk }) => mk(AUTH_DIR, { recursive: true }))
              log('Auth state cleared. Run login.mjs to re-authenticate.')
            } catch (e) {
              log(`Failed to clear auth state: ${e.message}`)
            }
          })
          // Stay running — health endpoint will report needs_auth
        }
      }
    })

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
      if (type !== 'notify') return
      _lastActivity = Date.now()

      for (const msg of messages) {
        if (!msg.message) continue

        // Dedup: skip messages we've already processed
        const msgId = msg.key.id
        if (isDuplicate(msgId)) {
          log(`Skipping duplicate message ${msgId}`)
          continue
        }

        const { from, name, text, direction, messageType, attachmentMeta } = logMessage(msg)

        // Forward all incoming 1:1 messages to gateway (groups excluded)
        if (direction === 'IN' && !from.endsWith('@g.us')) {
          try {
            const metadata = {
              from_jid: from,
              message_type: messageType,
              account: 'athena',
            }
            if (attachmentMeta) {
              metadata.attachment = { ...attachmentMeta }

              // Download document to disk so the LLM can read its contents
              if (messageType === 'document' && msg.message?.documentMessage) {
                const localPath = await downloadDocument(msg, msg.message.documentMessage)
                if (localPath) {
                  metadata.attachment.local_path = localPath
                }
              }
            }

            const resp = await fetch(`${OTTO_API}/gateway/incoming`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                channel: 'whatsapp',
                sender_id: from,
                sender_name: name,
                content: text,
                metadata,
              }),
            })
            const data = await resp.json()
            log(`Gateway response: ${JSON.stringify(data).slice(0, 200)}`)

            // Deliver reply back to WhatsApp (skip ignored/unknown contacts)
            if (data.content && data.metadata?.status !== 'ignored') {
              await sock.sendMessage(from, { text: data.content })
              log(`Replied to ${from}: ${data.content.slice(0, 100)}`)
            }
          } catch (err) {
            log(`Gateway error: ${err.message}`)
          }
        }
      }
    })

    startLivenessMonitor()

    // Graceful shutdown
    const shutdown = () => {
      log('Athena shutting down...')
      if (_livenessTimer) clearInterval(_livenessTimer)
      sock.end(undefined)
      process.exit(0)
    }
    process.on('SIGTERM', shutdown)
    process.on('SIGINT', shutdown)

  } finally {
    _startingUp = false
  }
}

// ── HTTP Server for outbound messages and health ──────────────────────
const httpServer = createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/send') {
    let body = ''
    for await (const chunk of req) body += chunk
    try {
      const { jid, message } = JSON.parse(body)
      if (!jid || !message) {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ error: 'jid and message required' }))
        return
      }
      if (!_sock || !_connected) {
        res.writeHead(503, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ error: 'Athena WhatsApp not connected' }))
        return
      }
      await _sock.sendMessage(jid, { text: message })
      log(`Sent message to ${jid}: ${message.slice(0, 100)}`)
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ status: 'sent' }))
    } catch (err) {
      log(`Send error: ${err.message}`)
      res.writeHead(500, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ error: err.message }))
    }
  } else if (req.method === 'GET' && req.url === '/health') {
    const silentSec = Math.round((Date.now() - _lastActivity) / 1000)
    let status = 'disconnected'
    if (_connected) status = 'ok'
    else if (_needsAuth) status = 'needs_auth'
    else if (_latestQR) status = 'needs_qr'
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({
      status,
      connected: _connected,
      needs_auth: _needsAuth,
      has_qr: !!_latestQR,
      account: 'athena',
      phone: '+94743768830',
      silent_seconds: silentSec,
      dedup_cache_size: _processedMessages.size,
    }))
  } else if (req.method === 'GET' && req.url === '/qr') {
    // Returns the latest QR code string for the OMS to render
    if (_connected) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ status: 'already_connected', qr: null }))
    } else if (_latestQR) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ status: 'qr_ready', qr: _latestQR }))
    } else {
      // Not connected, no QR yet — trigger reconnect
      if (!_startingUp) {
        log('QR requested — triggering reconnect...')
        start()
      }
      res.writeHead(202, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ status: 'connecting', qr: null }))
    }
  } else {
    res.writeHead(404, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ error: 'not found' }))
  }
})

httpServer.listen(HTTP_PORT, () => {
  log(`Athena HTTP server listening on :${HTTP_PORT}`)
})

start()
