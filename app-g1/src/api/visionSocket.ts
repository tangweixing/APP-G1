import { getBaseUrl } from './g1'

// 视觉识别模块 Socket.IO（Engine.IO v4 polling）客户端。
// 镜像 voiceSocket.ts 的握手 / 轮询 / 保活骨架，但只用于接收后端推送的
// face_greet_status / face_greet_log / gesture_control_status / gesture_control_log
// 四个事件（人脸 / 手势识别的运行状态与实时日志）。
//
// 视觉模块的启停、按键全部走 REST（见 g1.ts 的 startFaceGreet 等），
// 不需要经 socket 发送任何事件，因此本客户端不含 emit。
//
// 关键点：后端 Flask-SocketIO 在 start_* / 子进程打印日志时会广播这些事件，
// 连上后即可实时收到日志行与状态变更；但页面初始进入时仍需调用 REST
// *_status 接口同步"已在运行"的初始状态——因为 started 事件发生在本连接建立之前。

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
let eventHandler: ((name: string, data: any) => void) | null = null
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

function socketUrl(): string {
  const prefix = baseUrl || ''
  const sidPart = sid ? `&sid=${encodeURIComponent(sid)}` : ''
  return `${prefix}${SOCKET_IO_PATH}?EIO=${EIO}&transport=polling${sidPart}&t=${Date.now()}`
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

  // 服务端推送事件：42["event_name", {...payload...}]
  if (packet.indexOf('42') === 0) {
    try {
      const payload = JSON.parse(packet.slice(2))
      const eventName = payload && payload[0]
      const data = payload && payload[1]
      // 后端连接成功提示有时会先于 namespace ack 到达。
      if (eventName === 'connected' && connecting) {
        connected = true
        connecting = false
        settleConnects(true, true)
        return
      }
      // 其余事件全部交给页面注册的 handler 派发
      // （face_greet_status / face_greet_log / gesture_control_status / gesture_control_log）。
      if (eventName && eventHandler) {
        eventHandler(eventName, data || {})
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

/**
 * 连接视觉识别 Socket。onEvent 会被后端推送的每个事件调用 (eventName, data)。
 * 已连接 / 连接中时幂等。页面 onHide / onUnload 时应调用 disconnectVisionSocket。
 */
export function connectVisionSocket(onEvent: (name: string, data: any) => void): Promise<any> {
  eventHandler = onEvent
  if (connected && sid) return Promise.resolve(true)
  if (connecting) return new Promise((resolve, reject) => pendingConnects.push({ resolve, reject }))

  disconnectVisionSocket()
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

export function disconnectVisionSocket(abortRequest: boolean = true) {
  closedByUser = true
  connected = false
  connecting = false
  pendingConnects.splice(0)
  if (abortRequest && pollRequest && pollRequest.abort) {
    try { pollRequest.abort() } catch (e) {}
  }
  pollRequest = null
  sid = ''
  eventHandler = null
}

export function isVisionConnected(): boolean {
  return connected && !!sid
}
