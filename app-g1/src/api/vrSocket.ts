import { getBaseUrl } from './g1'

// 虚拟遥控器 Socket.IO（Engine.IO v4 polling）客户端。
// 镜像 voiceSocket.ts 的握手/轮询/保活骨架，但只用于发送
// virtual_remote_button_down / up 事件来触发后端舞蹈组合键。
// 后端 VirtualRemotePublisher 在服务启动时已自动初始化并 100Hz 发布，
// 因此本客户端无需发送 virtual_remote_init，连上后直接 emit 按键即可。
//
// 关键点：发送必须串行化。Engine.IO v4 轮询模式下，若多个 POST 并发发出，
// 会破坏正在挂起的 GET 长轮询会话，导致后续 GET 返回 400 BAD REQUEST、
// sid 失效、按键发不出去（表现为"点很多次只成功一次"）。
// 真正的 socket.io-client 内部也是串行 drain 发送队列。这里用一个轻量队列复刻。

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
let pendingConnects: Array<{ resolve: (value: any) => void; reject: (reason?: any) => void }> = []

// 串行发送队列：同一时刻只跑一个 POST，避免并发破坏轮询会话。
type SendItem = { payload: string; resolve: (ok: boolean) => void }
const sendQueue: SendItem[] = []
let sending = false

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

// 会话已坏：标记断开，清理发送队列，等下次 ensureVrSocket 重连。
function invalidateSession(reason: string) {
  if (!sid && !connected && !connecting) return
  console.warn('[VR] 会话失效: ' + reason)
  connected = false
  connecting = false
  sid = ''
  // 丢弃待发队列并通知失败
  const dropped = sendQueue.splice(0)
  dropped.forEach(function(item) { item.resolve(false) })
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
      if (eventName === 'connected' && connecting) {
        connected = true
        connecting = false
        settleConnects(true, true)
      }
    } catch (e) {
      // ignore malformed event packet
    }
    return
  }

  if (packet.indexOf('41') === 0 || packet.indexOf('44') === 0) {
    invalidateSession('服务端断开命名空间')
    settleConnects(false, new Error('Socket.IO连接已断开'))
  }
}

function pollLoop() {
  if (!sid || closedByUser) return

  requestPacket('GET').then(function(payload) {
    splitPackets(payload).forEach(handlePacket)
    if (!closedByUser && sid) pollLoop()
  }).catch(function(err) {
    // GET 失败：先尝试重试一次；连续失败则判定会话失效并清理，等下次重连。
    invalidateSession('轮询失败: ' + ((err && err.message) ? err.message : ''))
    settleConnects(false, err || new Error('Socket.IO轮询失败'))
    if (!closedByUser) {
      setTimeout(function() {
        if (!closedByUser && sid) pollLoop()
      }, 1000)
    }
  })
}

// 串行 drain 发送队列：一次只发一个 POST，收到响应再发下一个。
function drainQueue() {
  if (sending) return
  const item = sendQueue.shift()
  if (!item) return
  sending = true
  requestPacket('POST', item.payload).then(function() {
    sending = false
    item.resolve(true)
    if (sendQueue.length && !closedByUser) drainQueue()
  }).catch(function(err) {
    sending = false
    // POST 失败很可能是会话已坏，标记失效让下次重连，并丢弃后续队列。
    invalidateSession('发送失败: ' + ((err && err.message) ? err.message : ''))
    item.resolve(false)
    // 队列里剩余项已被 invalidateSession 清空并 resolve(false)。
  })
}

export function connectVrSocket(): Promise<any> {
  if (connected && sid) return Promise.resolve(true)
  if (connecting) return new Promise((resolve, reject) => pendingConnects.push({ resolve, reject }))

  disconnectVrSocket()
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
    invalidateSession(err && err.message ? err.message : '连接失败')
    settleConnects(false, err || new Error('Socket.IO连接失败'))
  })

  setTimeout(function() {
    if (connected || !connecting) return
    connecting = false
    settleConnects(false, new Error('Socket.IO连接超时'))
  }, 8000)

  return promise
}

export function disconnectVrSocket(abortRequest: boolean = true) {
  closedByUser = true
  connected = false
  connecting = false
  pendingConnects.splice(0)
  const dropped = sendQueue.splice(0)
  dropped.forEach(function(item) { item.resolve(false) })
  sending = false
  if (abortRequest && pollRequest && pollRequest.abort) {
    try { pollRequest.abort() } catch (e) {}
  }
  pollRequest = null
  sid = ''
}

export function isVrConnected(): boolean {
  return connected && !!sid
}

/**
 * 发送一个 Socket.IO 事件（入队，串行执行）。
 * 返回 Promise<boolean>：true 表示该事件已成功 POST，false 表示会话失效被丢弃。
 */
function emit(eventName: string, data?: any): Promise<boolean> {
  const payload = '42' + JSON.stringify([eventName, data === undefined ? null : data])
  return new Promise(function(resolve) {
    sendQueue.push({ payload: payload, resolve: resolve })
    if (!sending && connected && !closedByUser) drainQueue()
    // 若未连接，队列暂存；connectVrSocket 成功后由调用方触发 drain。
  })
}

function flushQueueIfReady() {
  if (connected && !sending && sendQueue.length && !closedByUser) drainQueue()
}

/**
 * 按下组合键并保持 ~300ms 后释放（对齐 web_arm_control/templates/index.html:4210 vrPressCombo，
 * 但保持时间略加长到 300ms，确保 R1+Select 等"修饰键+动作键"组合被固件稳定识别）。
 * 组合键内每个按键按下之间留 ~30ms 错峰（修饰键如 R1 先稳定置位，再按动作键），
 * 发送串行化，确保机器人稳定读到"组合键同时按下"的按键掩码。
 */
export function vrPressCombo(combo: string[]): Promise<void> {
  if (!combo || !combo.length) return Promise.resolve()

  // 逐个按下，每个间隔 30ms（让 R1 等修饰键先稳定置位）。
  function pressDown(idx: number, done: () => void) {
    if (idx >= combo.length) { done(); return }
    emit('virtual_remote_button_down', { name: combo[idx] })
    flushQueueIfReady()
    setTimeout(function() { pressDown(idx + 1, done) }, 30)
  }

  return new Promise(function(resolve) {
    pressDown(0, function() {
      // 保持 300ms，让固件稳定读到完整组合键掩码。
      setTimeout(function() {
        combo.forEach(function(name) {
          emit('virtual_remote_button_up', { name: name })
        })
        flushQueueIfReady()
        resolve()
      }, 300)
    })
  })
}

/**
 * 双击组合键（对齐 index.html:4230 vrPressDblClick，用于"舞蹈紧急中断"）。
 * 立即按一次（down→150ms→up），300ms 后再按一次。
 */
export function vrPressDblClick(keys: string[]): Promise<void> {
  if (!keys || !keys.length) return Promise.resolve()
  function doPress() {
    keys.forEach(function(name) {
      emit('virtual_remote_button_down', { name: name })
    })
    flushQueueIfReady()
    setTimeout(function() {
      keys.forEach(function(name) {
        emit('virtual_remote_button_up', { name: name })
      })
      flushQueueIfReady()
    }, 150)
  }
  doPress()
  setTimeout(doPress, 300)
  return new Promise(function(resolve) {
    setTimeout(resolve, 500)
  })
}

// 连接成功后，若有积压的发送项，开始 drain。
// （connectVrSocket 的调用方在 then 里通常会随后调用 vrPressCombo，故此处主要兜底。）
export function _flush() { flushQueueIfReady() }
