import { getBaseUrl } from './g1'

const DEFAULT_PORT = '5000'
const DEFAULT_SERVER_IP = '192.168.4.53'
const SOCKET_IO_PATH = '/socket.io/'
const EIO = '4'

let baseUrl = ''
let sid = ''
let connected = false
let connecting = false
let closedByUser = false
let pollRequest: any = null
let statusHandler: ((data: any) => void) | null = null
let pendingConnects: Array<{ resolve: (value: any) => void; reject: (reason?: any) => void }> = []

function getHttpBaseUrl(): string {
  const current = getBaseUrl()
  if (current) return current

  // H5 开发环境：Socket.IO polling 也走 localhost:8080 同源代理，避免 CORS。
  // #ifdef H5
  if (typeof window !== 'undefined' && window.location && window.location.port === '8080') return ''
  // #endif

  try {
    const saved = uni.getStorageSync('g1_server_ip')
    if (saved) return `http://${saved}:${DEFAULT_PORT}`
  } catch (e) {
    // ignore
  }

  return `http://${DEFAULT_SERVER_IP}:${DEFAULT_PORT}`
}

function socketUrl(extra: string = ''): string {
  const prefix = baseUrl || ''
  const sep = extra ? '&' + extra : ''
  const sidPart = sid ? `&sid=${encodeURIComponent(sid)}` : ''
  return `${prefix}${SOCKET_IO_PATH}?EIO=${EIO}&transport=polling${sidPart}&t=${Date.now()}${sep}`
}

function settleConnects(ok: boolean, value?: any) {
  const waits = pendingConnects.splice(0)
  waits.forEach(function(waiter) {
    if (ok) waiter.resolve(value)
    else waiter.reject(value)
  })
}

function requestPacket(method: 'GET' | 'POST', data?: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const task = uni.request({
      url: socketUrl(),
      method: method,
      data: data || '',
      header: method === 'POST' ? { 'Content-Type': 'text/plain;charset=UTF-8' } : {},
      success: function(res: any) {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
        else reject(new Error(`Socket.IO请求失败: ${res.statusCode}`))
      },
      fail: function(err: any) { reject(err) }
    })
    if (method === 'GET') pollRequest = task
  })
}

function splitPackets(payload: any): string[] {
  if (payload === undefined || payload === null) return []
  const text = typeof payload === 'string' ? payload : String(payload)
  if (!text) return []
  return text.split('\x1e').filter(function(packet) { return !!packet })
}

function handlePacket(packet: string) {
  if (!packet) return

  // Engine.IO open: 0{"sid":"..."}
  if (packet.charAt(0) === '0') {
    try {
      const openInfo = JSON.parse(packet.slice(1))
      sid = openInfo.sid || sid
    } catch (e) {
      // ignore malformed open packet
    }
    return
  }

  // Engine.IO ping，polling 模式同样需要 pong。
  if (packet === '2') {
    requestPacket('POST', '3').catch(function() {})
    return
  }

  // Socket.IO namespace connected。可能是 40 或 40{"sid":"..."}
  if (packet.indexOf('40') === 0) {
    connected = true
    connecting = false
    settleConnects(true, true)
    return
  }

  // 后端连接成功提示有时会先于 namespace ack 到达。
  if (packet.indexOf('42') === 0) {
    try {
      const payload = JSON.parse(packet.slice(2))
      const eventName = payload && payload[0]
      const data = payload && payload[1]
      if (eventName === 'connected' && connecting) {
        connected = true
        connecting = false
        settleConnects(true, true)
      }
      if (eventName === 'voice_action_status' && statusHandler) {
        statusHandler(data || {})
      }
    } catch (e) {
      // ignore malformed event packet
    }
    return
  }

  if (packet.indexOf('41') === 0 || packet.indexOf('44') === 0) {
    connected = false
    connecting = false
    settleConnects(false, new Error('Socket.IO连接已断开'))
  }
}

function pollLoop() {
  if (!sid || closedByUser) return

  requestPacket('GET').then(function(payload) {
    splitPackets(payload).forEach(handlePacket)
    if (!closedByUser) pollLoop()
  }).catch(function(err) {
    connected = false
    connecting = false
    if (!closedByUser) {
      settleConnects(false, err || new Error('Socket.IO轮询失败'))
      setTimeout(function() {
        if (!closedByUser && sid) pollLoop()
      }, 1000)
    }
  })
}

export function connectVoiceSocket(onStatus: (data: any) => void): Promise<any> {
  statusHandler = onStatus
  if (connected && sid) return Promise.resolve(true)
  if (connecting) return new Promise((resolve, reject) => pendingConnects.push({ resolve, reject }))

  disconnectVoiceSocket()
  baseUrl = getHttpBaseUrl()
  closedByUser = false
  connecting = true

  const promise = new Promise((resolve, reject) => pendingConnects.push({ resolve, reject }))

  requestPacket('GET').then(function(payload) {
    splitPackets(payload).forEach(handlePacket)
    if (!sid) throw new Error('Socket.IO握手失败')

    // 打开默认 namespace。后端确认后会返回 40，然后才算 connected。
    return requestPacket('POST', '40')
  }).then(function() {
    pollLoop()
  }).catch(function(err) {
    connected = false
    connecting = false
    settleConnects(false, err || new Error('Socket.IO连接失败'))
  })

  setTimeout(function() {
    if (connected || !connecting) return
    connecting = false
    settleConnects(false, new Error('Socket.IO连接超时'))
  }, 8000)

  return promise
}

export function disconnectVoiceSocket(abortRequest: boolean = true) {
  closedByUser = true
  connected = false
  connecting = false
  pendingConnects.splice(0)
  if (abortRequest && pollRequest && pollRequest.abort) {
    try { pollRequest.abort() } catch (e) {}
  }
  pollRequest = null
  sid = ''
  statusHandler = null
}

function emit(eventName: string, data?: any) {
  if (!sid) throw new Error('Socket.IO未连接')
  requestPacket('POST', '42' + JSON.stringify([eventName, data === undefined ? null : data])).catch(function(err) {
    if (statusHandler) statusHandler({ status: 'error', message: (err && err.message) ? err.message : 'Socket.IO发送失败' })
  })
}

export function emitVoiceExecute(text: string, actionId: number | null, autoReset: boolean = true) {
  emit('voice_action_execute', {
    text: text,
    action_id: actionId,
    auto_reset: autoReset,
  })
}

export function emitVoiceSpeakOnly(text: string) {
  emit('voice_speak_only', { text: text })
}

export function emitVoiceActionOnly(actionId: number) {
  emit('voice_action_only', { action_id: actionId })
}

export function emitVoiceResetArm() {
  emit('voice_reset_arm')
}
