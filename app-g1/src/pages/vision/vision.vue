<template>
	<view class="vision-page">
		<!-- 顶部栏 -->
		<view class="top-bar">
			<button class="btn-back" @click="goBack">&#x25C0; 返回</button>
			<view class="status-mini" :class="{ online: socketConnected }">
				{{ socketConnected ? '实时连接' : '未连接' }}
			</view>
		</view>

		<!-- 人脸识别 -->
		<view class="card">
			<view class="card-header">
				<text class="card-title">&#x1F464; 人脸识别</text>
				<view class="run-status" :class="{ on: faceRunning }">
					{{ faceRunning ? '&#x25CF; 运行中' : '&#x25CB; 未启动' }}
				</view>
			</view>
			<view class="card-body">
				<text class="desc">D435i 拍照 &#x2192; 百度 API 识别人名 &#x2192; 执行挥手 &#x2192; 语音播报"你好，{姓名}！"</text>

				<view class="btn-row">
					<button v-if="!faceRunning" class="btn-start" @click="doStartFace" :disabled="faceLoading || gestureRunning">
						{{ faceLoading ? '启动中...' : '&#x25B6; 启动' }}
					</button>
					<button v-else class="btn-stop" @click="doStopFace" :disabled="faceLoading">
						{{ faceLoading ? '停止中...' : '&#x23F9; 停止' }}
					</button>
					<button class="btn-refresh" @click="doRefreshFaceLogs">&#x1F504; 刷新日志</button>
				</view>

				<view class="warn-box" :class="{ 'warn-block': gestureRunning }">
					<text class="warn-text">{{ gestureRunning ? '&#x26A0; 手势识别占用相机中，请先停止手势识别' : '&#x26A0; 与"手势识别"共用 RealSense 相机，二者不可同时运行。' }}</text>
				</view>

				<view class="log-title">&#x1F4F7; 人脸识别日志</view>
				<view class="log-area">
					<scroll-view scroll-y class="log-scroll" :scroll-top="faceScrollTop">
						<view v-if="faceLogs.length === 0" class="log-empty">点击"启动"开始</view>
						<view v-for="(log, idx) in faceLogs" :key="idx" class="log-item" :class="'log-' + log.type">
							<text class="log-time">{{ log.time }}</text>
							<text class="log-msg">{{ log.msg }}</text>
						</view>
					</scroll-view>
				</view>
			</view>
		</view>

		<!-- 手势识别 -->
		<view class="card">
			<view class="card-header">
				<text class="card-title">&#x270B; 手势识别</text>
				<view class="run-status" :class="{ on: gestureRunning }">
					{{ gestureRunning ? '&#x25CF; 运行中' : '&#x25CB; 未启动' }}
				</view>
			</view>
			<view class="card-body">
				<text class="desc">五模式：控制 / 跟随 / 走近 / 导航 / 问候。启动后默认 Mode1 且识别暂停，按 R 开始识别，再按切换模式。</text>

				<view class="btn-row">
					<button v-if="!gestureRunning" class="btn-start" @click="doStartGesture" :disabled="gestureLoading || faceRunning">
						{{ gestureLoading ? '启动中...' : '&#x25B6; 启动' }}
					</button>
					<button v-else class="btn-stop" @click="doStopGesture" :disabled="gestureLoading">
						{{ gestureLoading ? '停止中...' : '&#x23F9; 停止' }}
					</button>
					<button class="btn-refresh" @click="doRefreshGestureLogs">&#x1F504; 刷新日志</button>
				</view>

				<!-- 模式切换按键 -->
				<view class="key-title">&#x1F3AE; 模式切换 / 启停（键盘 R/1/2/3/4/5/Q）</view>
				<view class="key-grid">
					<button class="key-btn key-info" @click="doGestureKey('R')" :disabled="!gestureRunning">&#x25B6;/&#x23F8; R 启停识别</button>
					<button class="key-btn" @click="doGestureKey('1')" :disabled="!gestureRunning">1 手势控制</button>
					<button class="key-btn" @click="doGestureKey('2')" :disabled="!gestureRunning">2 跟随</button>
					<button class="key-btn" @click="doGestureKey('3')" :disabled="!gestureRunning">3 走近+握手</button>
					<button class="key-btn" @click="doGestureKey('4')" :disabled="!gestureRunning">4 手势导航</button>
					<button class="key-btn" @click="doGestureKey('5')" :disabled="!gestureRunning">5 人脸问候</button>
					<button class="key-btn key-danger" @click="doGestureKey('Q')" :disabled="!gestureRunning">&#x23F9; Q 退出</button>
				</view>

				<!-- 五种模式说明 -->
				<view class="modes-info">
					<view class="mode-card"><text class="mode-name">Mode 1</text><text class="mode-desc">&#x1F44D;握手 / &#x1F44C;释放手臂</text></view>
					<view class="mode-card"><text class="mode-name">Mode 2</text><text class="mode-desc">&#x270A;握拳&#x2192;跟随 (保持0.6m)</text></view>
					<view class="mode-card"><text class="mode-name">Mode 3</text><text class="mode-desc">&#x270A;握拳&#x2192;走到0.5-0.6m&#x2192;握手</text></view>
					<view class="mode-card"><text class="mode-name">Mode 4</text><text class="mode-desc">&#x1F448;左转 / &#x1F449;右转 / &#x270A;前进 / &#x1F590;后退</text></view>
					<view class="mode-card"><text class="mode-name">Mode 5</text><text class="mode-desc">&#x1F464;检测人脸&#x2192;走近0.5m+居中&#x2192;握手+你好</text></view>
				</view>

				<view class="warn-box" :class="{ 'warn-block': faceRunning }">
					<text class="warn-text">{{ faceRunning ? '&#x26A0; 人脸识别占用相机中，请先停止人脸识别' : '&#x26A0; 与"人脸识别"共用 RealSense 相机，二者不可同时运行。' }}</text>
				</view>

				<view class="log-title">&#x270B; 手势识别日志</view>
				<view class="log-area">
					<scroll-view scroll-y class="log-scroll" :scroll-top="gestureScrollTop">
						<view v-if="gestureLogs.length === 0" class="log-empty">点击"启动"开始</view>
						<view v-for="(log, idx) in gestureLogs" :key="idx" class="log-item" :class="'log-' + log.type">
							<text class="log-time">{{ log.time }}</text>
							<text class="log-msg">{{ log.msg }}</text>
						</view>
					</scroll-view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
	import Vue from 'vue';
	import * as g1Api from '../../api/g1';
	import * as visionSocket from '../../api/visionSocket';

	// 日志行分类（对齐 web_arm_control/templates/index.html:2182 _classifyLogLine）：
	// 按后端 stdout 行里出现的 emoji / 关键词着色，识别成功为绿、失败为红、警告为黄。
	function classifyLog(text) {
		var t = (text || '').toString();
		if (t.indexOf('❌') >= 0 || t.indexOf('失败') >= 0 || t.indexOf('错误') >= 0 || t.indexOf('ERROR') >= 0) return 'error';
		if (t.indexOf('✅') >= 0 || t.indexOf('成功') >= 0 || t.indexOf('识别成功') >= 0 || t.indexOf('🎉') >= 0) return 'success';
		if (t.indexOf('⚠️') >= 0 || t.indexOf('警告') >= 0 || t.indexOf('QPS') >= 0) return 'warn';
		return 'info';
	}

	var MAX_LOGS = 200;

	export default Vue.extend({
		data: function() {
			return {
				// 连接状态
				socketConnected: false,
				// 人脸识别
				faceRunning: false,
				faceLoading: false,
				faceLogs: [],
				faceScrollTop: 0,
				// 手势识别
				gestureRunning: false,
				gestureLoading: false,
				gestureLogs: [],
				gestureScrollTop: 0,
			}
		},

		onLoad: function() {
			this.fetchInitialStatus();
		},
		onShow: function() {
			this.ensureSocket();
		},
		onHide: function() {
			visionSocket.disconnectVisionSocket();
			this.socketConnected = false;
		},
		onUnload: function() {
			visionSocket.disconnectVisionSocket();
			this.socketConnected = false;
		},

		methods: {
			goBack: function() {
				var pages = getCurrentPages();
				if (pages.length > 1) { uni.navigateBack(); }
				else { uni.reLaunch({ url: '/pages/index/index' }); }
			},

			/* ---------- Socket ---------- */
			ensureSocket: function() {
				var self = this;
				if (visionSocket.isVisionConnected()) {
					this.socketConnected = true;
					return;
				}
				visionSocket.connectVisionSocket(function(name, data) {
					self.onSocketEvent(name, data);
				}).then(function() {
					self.socketConnected = true;
					// 连上后同步一次状态：started 事件可能发生在连接建立之前。
					self.fetchInitialStatus();
				}).catch(function() {
					self.socketConnected = false;
				});
			},

			onSocketEvent: function(name, data) {
				if (name === 'face_greet_status') {
					this.faceRunning = data.status === 'started';
					if (data.status === 'stopped' && data.message) this.addFaceLog(data.message, 'warn');
				} else if (name === 'face_greet_log') {
					this.addFaceLog(data.line);
				} else if (name === 'gesture_control_status') {
					this.gestureRunning = data.status === 'started';
					if (data.status === 'stopped' && data.message) this.addGestureLog(data.message, 'warn');
				} else if (name === 'gesture_control_log') {
					this.addGestureLog(data.line);
				}
			},

			fetchInitialStatus: function() {
				var self = this;
				g1Api.getFaceGreetStatus().then(function(r) {
					if (!r) return;
					self.faceRunning = !!r.running;
					if (r.logs && r.logs.length) {
						self.faceLogs = r.logs.map(function(l) { return self.makeLog(l); });
						self.scrollFaceToBottom();
					}
				}).catch(function() {});
				g1Api.getGestureControlStatus().then(function(r) {
					if (!r) return;
					self.gestureRunning = !!r.running;
					if (r.logs && r.logs.length) {
						self.gestureLogs = r.logs.map(function(l) { return self.makeLog(l); });
						self.scrollGestureToBottom();
					}
				}).catch(function() {});
			},

			/* ---------- 日志工具 ---------- */
			nowStr: function() {
				var now = new Date();
				var h = String(now.getHours()).padStart(2, '0');
				var m = String(now.getMinutes()).padStart(2, '0');
				var s = String(now.getSeconds()).padStart(2, '0');
				return h + ':' + m + ':' + s;
			},
			makeLog: function(line) {
				return { time: this.nowStr(), type: classifyLog(line), msg: String(line || '') };
			},
			addFaceLog: function(line, type) {
				this.faceLogs.push({ time: this.nowStr(), type: type || classifyLog(line), msg: String(line || '') });
				if (this.faceLogs.length > MAX_LOGS) this.faceLogs.shift();
				this.scrollFaceToBottom();
			},
			addGestureLog: function(line, type) {
				this.gestureLogs.push({ time: this.nowStr(), type: type || classifyLog(line), msg: String(line || '') });
				if (this.gestureLogs.length > MAX_LOGS) this.gestureLogs.shift();
				this.scrollGestureToBottom();
			},
			// scroll-view 的 scroll-top 必须变化才会触发滚动；两个大值来回切换，
			// 都会被夹到容器底部（max scroll），从而实现"新日志自动滚到底"。
			scrollFaceToBottom: function() {
				var self = this;
				this.$nextTick(function() { self.faceScrollTop = self.faceScrollTop >= 99999 ? 100000 : 99999; });
			},
			scrollGestureToBottom: function() {
				var self = this;
				this.$nextTick(function() { self.gestureScrollTop = self.gestureScrollTop >= 99999 ? 100000 : 99999; });
			},

			/* ---------- 人脸识别 ---------- */
			doStartFace: function() {
				var self = this;
				if (this.gestureRunning) {
					uni.showToast({ title: '手势识别占用相机中', icon: 'none' });
					return;
				}
				this.faceLoading = true;
				this.addFaceLog('正在启动人脸识别...', 'info');
				g1Api.startFaceGreet('eth0').then(function(r) {
					self.faceLoading = false;
					if (r && r.success) {
						self.faceRunning = true;
						self.faceLogs = [];
						if (r.logs && r.logs.length) r.logs.forEach(function(l) { self.addFaceLog(l); });
						self.addFaceLog(r.message || '人脸识别已启动', 'success');
						uni.showToast({ title: '已启动', icon: 'success' });
					} else {
						self.addFaceLog((r && r.message) || '启动失败', 'error');
						uni.showToast({ title: (r && r.message) || '启动失败', icon: 'none' });
					}
				}).catch(function(err) {
					self.faceLoading = false;
					self.addFaceLog('网络错误：' + ((err && err.message) || err), 'error');
					uni.showToast({ title: '启动失败', icon: 'none' });
				});
			},
			doStopFace: function() {
				var self = this;
				this.faceLoading = true;
				this.addFaceLog('正在停止人脸识别...', 'info');
				g1Api.stopFaceGreet().then(function(r) {
					self.faceLoading = false;
					if (r && r.success) {
						self.faceRunning = false;
						self.addFaceLog(r.message || '人脸识别已停止', 'success');
						uni.showToast({ title: '已停止', icon: 'success' });
					} else {
						self.addFaceLog((r && r.message) || '停止失败', 'error');
						uni.showToast({ title: (r && r.message) || '停止失败', icon: 'none' });
					}
				}).catch(function(err) {
					self.faceLoading = false;
					self.addFaceLog('网络错误：' + ((err && err.message) || err), 'error');
					uni.showToast({ title: '停止失败', icon: 'none' });
				});
			},
			doRefreshFaceLogs: function() {
				var self = this;
				g1Api.getFaceGreetStatus().then(function(r) {
					if (!r) return;
					self.faceRunning = !!r.running;
					self.faceLogs = [];
					if (r.logs && r.logs.length) r.logs.forEach(function(l) { self.addFaceLog(l); });
					else self.addFaceLog('暂无日志', 'info');
					uni.showToast({ title: '已刷新', icon: 'none' });
				}).catch(function(err) {
					self.addFaceLog('刷新失败：' + ((err && err.message) || err), 'error');
				});
			},

			/* ---------- 手势识别 ---------- */
			doStartGesture: function() {
				var self = this;
				if (this.faceRunning) {
					uni.showToast({ title: '人脸识别占用相机中', icon: 'none' });
					return;
				}
				this.gestureLoading = true;
				this.addGestureLog('正在启动手势识别...', 'info');
				g1Api.startGestureControl('eth0').then(function(r) {
					self.gestureLoading = false;
					if (r && r.success) {
						self.gestureRunning = true;
						self.gestureLogs = [];
						if (r.logs && r.logs.length) r.logs.forEach(function(l) { self.addGestureLog(l); });
						self.addGestureLog(r.message || '手势识别已启动', 'success');
						uni.showToast({ title: '已启动', icon: 'success' });
					} else {
						self.addGestureLog((r && r.message) || '启动失败', 'error');
						uni.showToast({ title: (r && r.message) || '启动失败', icon: 'none' });
					}
				}).catch(function(err) {
					self.gestureLoading = false;
					self.addGestureLog('网络错误：' + ((err && err.message) || err), 'error');
					uni.showToast({ title: '启动失败', icon: 'none' });
				});
			},
			doStopGesture: function() {
				var self = this;
				this.gestureLoading = true;
				this.addGestureLog('正在停止手势识别...', 'info');
				g1Api.stopGestureControl().then(function(r) {
					self.gestureLoading = false;
					if (r && r.success) {
						// 后端 stop 会释放相机并广播 gesture_control_status stopped，这里也乐观置位。
						self.gestureRunning = false;
						self.addGestureLog(r.message || '手势识别已停止', 'success');
						uni.showToast({ title: '已停止', icon: 'success' });
					} else {
						self.addGestureLog((r && r.message) || '停止失败', 'error');
						uni.showToast({ title: (r && r.message) || '停止失败', icon: 'none' });
					}
				}).catch(function(err) {
					self.gestureLoading = false;
					self.addGestureLog('网络错误：' + ((err && err.message) || err), 'error');
					uni.showToast({ title: '停止失败', icon: 'none' });
				});
			},
			doRefreshGestureLogs: function() {
				var self = this;
				g1Api.getGestureControlStatus().then(function(r) {
					if (!r) return;
					self.gestureRunning = !!r.running;
					self.gestureLogs = [];
					if (r.logs && r.logs.length) r.logs.forEach(function(l) { self.addGestureLog(l); });
					else self.addGestureLog('暂无日志', 'info');
					uni.showToast({ title: '已刷新', icon: 'none' });
				}).catch(function(err) {
					self.addGestureLog('刷新失败：' + ((err && err.message) || err), 'error');
				});
			},
			doGestureKey: function(key) {
				var self = this;
				g1Api.gestureSendKey(key).then(function(r) {
					if (r && r.success) {
						self.addGestureLog('已发送按键: ' + key, 'info');
						// 发送 Q 后后端会退出并广播 stopped，状态由 onSocketEvent 更新。
					} else {
						self.addGestureLog('按键失败: ' + ((r && r.message) || ''), 'error');
						uni.showToast({ title: (r && r.message) || '按键失败', icon: 'none' });
					}
				}).catch(function(err) {
					// err.message 现在透传后端真实原因（如 "发送按键失败: ..."），便于定位。
					var msg = (err && err.message) ? err.message : String(err);
					self.addGestureLog('按键失败：' + msg, 'error');
					uni.showToast({ title: msg, icon: 'none' });
				});
			},
		}
	});
</script>

<style scoped>
	.vision-page{min-height:100vh;background:#1a1a2e;color:#eee;display:flex;flex-direction:column;padding:12px;box-sizing:border-box}

	/* 顶栏 */
	.top-bar{display:flex;align-items:center;justify-content:space-between;height:44px;margin-bottom:16px;padding:0 8px}
	.btn-back{position:fixed;top:20px;left:20px;z-index:10;background:#333;color:#fff;border:none;border-radius:8px;font-size:14px;padding:6px 14px;line-height:1}
	.status-mini{padding:3px 10px;border-radius:10px;font-size:11px;background:#555;color:#aaa}
	.status-mini.online{background:#1a5f2a;color:#5fda5f}

	/* 卡片 */
	.card{background:#222;border-radius:12px;margin-bottom:16px;overflow:hidden;border:1px solid #333}
	.card-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid #333}
	.card-title{font-size:15px;font-weight:600;color:#fff}
	.card-body{padding:16px}

	/* 运行状态徽标 */
	.run-status{padding:4px 12px;border-radius:12px;font-size:12px;background:#444;color:#888}
	.run-status.on{background:#1a5f2a;color:#5fda5f}

	.desc{display:block;font-size:13px;color:#aaa;line-height:1.6;margin-bottom:16px}

	/* 按钮行 */
	.btn-row{display:flex;align-items:center;gap:10px;margin-bottom:16px}
	.btn-start,.btn-stop{flex:1;border:none;border-radius:10px;font-size:15px;padding:12px 0;font-weight:600}
	.btn-start{background:linear-gradient(135deg,#1a7f37,#28a745);color:#fff}
	.btn-start[disabled]{opacity:.45}
	.btn-stop{background:linear-gradient(135deg,#b71c1c,#d32f2f);color:#fff}
	.btn-stop[disabled]{opacity:.45}
	.btn-refresh{border:1px solid #444;background:#2a2a3e;color:#ccc;font-size:13px;padding:12px 16px;border-radius:10px;white-space:nowrap}

	/* 警告条 */
	.warn-box{background:#2a2118;border:1px solid #4a3a1a;border-radius:8px;padding:8px 12px;margin-bottom:14px}
	.warn-box.warn-block{background:#3a1818;border-color:#5a2a2a}
	.warn-text{font-size:12px;color:#ffd93d;line-height:1.5}
	.warn-box.warn-block .warn-text{color:#ff8b8b}

	/* 日志 */
	.log-title{font-size:13px;font-weight:600;color:#88c;margin-bottom:8px}
	.log-area{height:220px;background:#11121c;border:1px solid #2a2a3e;border-radius:8px;overflow:hidden}
	.log-scroll{height:100%}
	.log-empty{color:#666;font-size:12px;text-align:center;padding:24px 0}
	.log-item{display:flex;padding:5px 10px;border-bottom:1px solid #1f2030;font-size:12px;align-items:flex-start}
	.log-time{color:#555;width:64px;flex-shrink:0}
	.log-msg{color:#ccc;word-break:break-all;flex:1}
	.log-success .log-msg{color:#5fda5f}
	.log-error .log-msg{color:#ff6b6b}
	.log-warn .log-msg{color:#ffd93d}
	.log-info .log-msg{color:#74c0fc}

	/* 模式按键 */
	.key-title{font-size:13px;font-weight:600;color:#88c;margin:4px 0 10px}
	.key-grid{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
	.key-btn{flex:1 1 30%;min-width:90px;border:1px solid #2f4a6a;background:#1b2a3e;color:#cfe3ff;font-size:13px;padding:11px 6px;border-radius:8px;line-height:1.3}
	.key-btn[disabled]{opacity:.4}
	.key-btn.key-info{background:#1b3a2e;border-color:#2f6a4a;color:#9fe}
	.key-btn.key-danger{background:#3a1818;border-color:#5a2a2a;color:#ffb0b0}

	/* 模式说明 */
	.modes-info{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
	.mode-card{display:flex;align-items:center;gap:10px;background:#1a1a2e;border:1px solid #2a2a3e;border-radius:8px;padding:8px 12px}
	.mode-name{flex-shrink:0;width:64px;font-size:12px;font-weight:600;color:#9af}
	.mode-desc{font-size:12px;color:#aaa;flex:1}
</style>
