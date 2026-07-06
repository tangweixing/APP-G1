// G1机器人控制API - 动态后端地址
const DEFAULT_PORT = '5000'
const DEFAULT_SERVER_IP = '192.168.4.53'

let _baseUrl = ''

export function getDefaultServerIp(): string {
  return DEFAULT_SERVER_IP
}

/** 获取当前API基础地址 */
export function getBaseUrl(): string {
  // H5 开发环境必须走 localhost:8080 的同源代理，否则机器人后端缺少 CORS 头会被浏览器拦截。
  // #ifdef H5
  return ''
  // #endif

  if (_baseUrl) return _baseUrl
  try {
    const saved = uni.getStorageSync('g1_server_ip')
    if (saved) return `http://${saved}:${DEFAULT_PORT}`
  } catch (e) {
    // ignore
  }

  return `http://${DEFAULT_SERVER_IP}:${DEFAULT_PORT}`
}

/** 设置后端地址（IP或域名），自动拼接端口 */
export function setServerAddress(ip: string, port: string = DEFAULT_PORT) {
  // H5 开发环境统一走 vue.config.js 里的同源代理，避免 CORS。
  // 保存的 IP 只给 App 端使用。
  // #ifdef H5
  _baseUrl = ''
  return
  // #endif

  if (ip) {
    _baseUrl = `http://${ip}:${port}`
  } else {
    _baseUrl = ''
  }
}

/** 从本地存储恢复地址设置（需手动调用） */
export function loadSavedAddress() {
  // H5 开发环境统一走同源代理，避免 CORS。
  // #ifdef H5
  _baseUrl = ''
  return
  // #endif

  try {
    const saved = uni.getStorageSync('g1_server_ip')
    if (saved) {
      _baseUrl = `http://${saved}:${DEFAULT_PORT}`
    } else {
      _baseUrl = ''
    }
  } catch (e) {
    _baseUrl = ''
  }
}

// H5默认走同源代理，避免浏览器 CORS；App 端可保存 IP 后直连
loadSavedAddress()

/**
 * 封装uni.request请求
 */
function request(options: {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
  header?: Record<string, string>
}): Promise<any> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: getBaseUrl() + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...options.header
      },
      success: (res: any) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          // 透传后端错误信息：后端非 2xx 时通常返回 {success:false,message:"..."}，
          // 把 message 暴露给调用方，便于在 toast / 日志里看到真实失败原因
          // （例如 /api/gesture_send_key 返回 500 时携带 "发送按键失败: ..."）。
          // 若后端返回 HTML 错误页（无 message），则回退到状态码。
          const body = res.data
          const msg = (body && typeof body === 'object' && body.message)
            ? String(body.message)
            : `请求失败: ${res.statusCode}`
          const e: any = new Error(msg)
          e.statusCode = res.statusCode
          e.body = body
          reject(e)
        }
      },
      fail: (err: any) => {
        reject(err)
      }
    })
  })
}

// ============ API 接口定义 ============

/** 初始化SDK客户端 */
export function initApi(networkInterface: string = 'eth0') {
  return request({
    url: '/api/init',
    method: 'POST',
    data: { network_interface: networkInterface }
  })
}

/** 获取机器人状态 */
export function getStatus() {
  return request({ url: '/api/status' })
}

/** 获取动作列表 */
export function getActions() {
  return request({ url: '/api/actions' })
}

/** 设置运动速度 */
export function setVelocity(vx: number, vy: number, wz: number) {
  return request({
    url: '/api/set_velocity',
    method: 'POST',
    data: { vx, vy, wz }
  })
}

/** 获取当前速度 */
export function getVelocity() {
  return request({ url: '/api/get_velocity' })
}

/** 急停 */
export function emergencyStop() {
  return request({ url: '/api/emergency_stop', method: 'POST' })
}

/** 设置档位 */
export function setGear(gear: number) {
  return request({
    url: '/api/set_gear',
    method: 'POST',
    data: { gear }
  })
}

/** 设置FSM模式 */
export function setFsm(fsmId: number) {
  return request({
    url: '/api/set_fsm',
    method: 'POST',
    data: { fsm_id: fsmId }
  })
}

/** 执行机械臂动作 */
export function armAction(actionId: number) {
  return request({
    url: '/api/execute',
    method: 'POST',
    data: { action_id: actionId }
  })
}

/** 启动导航 */
export function startNavigation() {
  return request({ url: '/api/start_navigation', method: 'POST' })
}

/** 停止导航 */
export function stopNavigation() {
  return request({ url: '/api/stop_navigation', method: 'POST' })
}

/** 切换运动控制（启/停） */
export function toggleLoco() {
  return request({ url: '/api/toggle_loco', method: 'POST' })
}

/** 启动小野AI */
export function startXiaoye() {
  return request({ url: '/api/start_xiaoye', method: 'POST' })
}

/** 停止小野AI */
export function stopXiaoye() {
  return request({ url: '/api/stop_xiaoye', method: 'POST' })
}

/* ========== 语音动作输出模块 ========== */

/** 获取语音动作列表和预设语音 */
export function getVoiceActions() {
  return request({ url: '/api/voice_actions' })
}

/* ========== 视觉识别模块 ========== */

/** 启动人脸识别（拍照→百度识别→挥手+语音） */
export function startFaceGreet(networkInterface: string = 'eth0') {
  return request({
    url: '/api/start_face_greet',
    method: 'POST',
    data: { network_interface: networkInterface }
  })
}

/** 停止人脸识别 */
export function stopFaceGreet() {
  return request({ url: '/api/stop_face_greet', method: 'POST' })
}

/** 获取人脸识别状态与日志 */
export function getFaceGreetStatus() {
  return request({ url: '/api/face_greet_status' })
}

/** 启动手势识别（五模式：控制/跟随/走近/导航/问候） */
export function startGestureControl(networkInterface: string = 'eth0') {
  return request({
    url: '/api/start_gesture_control',
    method: 'POST',
    data: { network_interface: networkInterface }
  })
}

/** 停止手势识别 */
export function stopGestureControl() {
  return request({ url: '/api/stop_gesture_control', method: 'POST' })
}

/** 获取手势识别状态与日志 */
export function getGestureControlStatus() {
  return request({ url: '/api/gesture_control_status' })
}

/** 发送手势模式按键（R/1/2/3/4/5/Q） */
export function gestureSendKey(key: string) {
  return request({
    url: '/api/gesture_send_key',
    method: 'POST',
    data: { key: key }
  })
}

/* ========== 小智智能体配置代理（转发 xiaozhi.me）========== */

/** 保存用户手动粘贴的 token */
export function agentSaveToken(token: string) {
  return request({ url: '/api/agent/save_token', method: 'POST', data: { token } })
}

/** 检查本地 token 是否有效 */
export function agentAuthStatus() {
  return request({ url: '/api/agent/auth_status' })
}

/** 退出登录 */
export function agentLogout() {
  return request({ url: '/api/agent/logout', method: 'POST' })
}

/** 切换当前智能体 */
export function agentSelect(agentId: string | number) {
  return request({ url: '/api/agent/select', method: 'POST', data: { agent_id: agentId } })
}

/** 列智能体 */
export function agentList() {
  return request({ url: '/api/agent/list' })
}

/** 读当前智能体配置 */
export function agentGetConfig() {
  return request({ url: '/api/agent/config' })
}

/** 保存智能体配置 */
export function agentSaveConfig(config: Record<string, any>) {
  return request({ url: '/api/agent/config', method: 'POST', data: config })
}

/** 音色列表 */
export function agentVoices() {
  return request({ url: '/api/agent/voices' })
}

/** AI 优化人设 */
export function agentOptimizeCharacter(character: string) {
  return request({ url: '/api/agent/optimize_character', method: 'POST', data: { character } })
}

/** 保存后重启小野 AI 让配置生效 */
export function agentApply() {
  return request({ url: '/api/agent/apply', method: 'POST' })
}

export default {
  initApi,
  getStatus,
  getActions,
  setVelocity,
  getVelocity,
  emergencyStop,
  setGear,
  setFsm,
  armAction,
  toggleLoco,
  startNavigation,
  stopNavigation,
  startXiaoye,
  stopXiaoye,
  // 语音动作
  getVoiceActions,
  // 视觉识别
  startFaceGreet,
  stopFaceGreet,
  getFaceGreetStatus,
  startGestureControl,
  stopGestureControl,
  getGestureControlStatus,
  gestureSendKey,
  // 小智智能体配置
  agentSaveToken,
  agentAuthStatus,
  agentLogout,
  agentSelect,
  agentList,
  agentGetConfig,
  agentSaveConfig,
  agentVoices,
  agentOptimizeCharacter,
  agentApply,
  getDefaultServerIp,
  getBaseUrl,
  setServerAddress,
}
