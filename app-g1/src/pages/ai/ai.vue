<template>
	<view class="ai-page">
		<!-- 顶部栏 -->
		<view class="top-bar">
			<button class="btn-back" @click="goBack">&#x25C0; 返回</button>
			<view class="status-mini" :class="{ online: xiaoyeRunning }">
				{{ xiaoyeRunning ? 'AI运行中' : 'AI待机' }}
			</view>
		</view>

		<!-- 小野AI控制 -->
		<view class="card">
			<view class="card-header">
				<text class="card-title">&#x1F916; 小野AI 语音助手</text>
				<view class="ai-status" :class="{ on: xiaoyeRunning }">
					{{ xiaoyeRunning ? '&#x25CF; 运行中' : '&#x25CB; 未启动' }}
				</view>
			</view>
			<view class="card-body">
				<text class="desc">通过语音唤醒词与小野AI交互，支持自然语言对话控制机器人动作。</text>

				<view class="btn-row">
					<button v-if="!xiaoyeRunning" class="btn-start" @click="doStartXiaoye" :disabled="loading">
						{{ loading ? '启动中...' : '&#x25B6; 启动小野AI' }}
					</button>
					<button v-else class="btn-stop" @click="doStopXiaoye" :disabled="loading">
						{{ loading ? '停止中...' : '&#x23F9; 停止小野AI' }}
					</button>
				</view>

				<!-- 使用说明 -->
				<view class="tips-box">
					<text class="tips-title">&#x2139; 使用说明</text>
					<view class="tips-list">
						<text class="tip-item">1. 点击「启动小野AI」等待服务就绪</text>
						<text class="tip-item">2. 对着机器人说出唤醒词唤醒AI</text>
						<text class="tip-item">3. 通过语音指令控制机器人动作</text>
					</view>
				</view>
			</view>
		</view>

		<!-- 日志区域 -->
		<view class="card" v-if="logs.length > 0">
			<view class="card-header">
				<text class="card-title">&#x1F4DD; 操作日志</text>
				<button class="btn-clear" @click="logs = []">清空</button>
			</view>
			<view class="log-area">
				<scroll-view scroll-y class="log-scroll">
					<view v-for="(log, idx) in logs" :key="idx" class="log-item" :class="'log-' + log.type">
						<text class="log-time">{{ log.time }}</text>
						<text class="log-msg">{{ log.msg }}</text>
					</view>
				</scroll-view>
			</view>
		</view>
	</view>
</template>

<script>
	import Vue from 'vue';
	import * as g1Api from '../../api/g1';

	export default Vue.extend({
		data: function() {
			return {
				xiaoyeRunning: false,
				loading: false,
				logs: [],
				pollTimer: null,
			}
		},
		onLoad: function() { this.checkStatus() },
		onShow: function() {
			var self = this;
			if (!this.pollTimer) {
				this.pollTimer = setInterval(function() { self.checkStatus() }, 3000);
			}
		},
		onHide: function() {
			if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
		},
		onUnload: function() {
			if (this.pollTimer) clearInterval(this.pollTimer);
		},

		methods: {
			goBack: function() {
				var pages = getCurrentPages();
				if (pages.length > 1) { uni.navigateBack(); }
				else { uni.reLaunch({ url: '/pages/index/index' }); }
			},

			checkStatus: function() {
				var self = this;
				g1Api.getStatus().then(function(r) {
					self.xiaoyeRunning = r.xiaoye_running || false;
				}).catch(function() {});
			},

			doStartXiaoye: function() {
				var self = this;
				this.loading = true;
				this.addLog('info', '正在启动小野AI...');
				g1Api.startXiaoye().then(function(r) {
					self.loading = false;
					if (r.success) {
						self.xiaoyeRunning = true;
						self.addLog('success', r.message || '小野AI已启动');
					} else {
						self.addLog('error', r.message || '启动失败');
					}
					uni.showToast({ title: r.message || '', icon: r.success ? 'success' : 'none' });
				}).catch(function(err) {
					self.loading = false;
					self.addLog('error', '网络错误：' + (err && err.message || err));
					uni.showToast({ title: '启动失败', icon: 'none' });
				});
			},

			doStopXiaoye: function() {
				var self = this;
				this.loading = true;
				this.addLog('info', '正在停止小野AI...');
				g1Api.stopXiaoye().then(function(r) {
					self.loading = false;
					if (r.success) {
						self.xiaoyeRunning = false;
						self.addLog('success', r.message || '小野AI已停止');
					} else {
						self.addLog('warn', r.message || '停止失败');
					}
					uni.showToast({ title: r.message || '', icon: r.success ? 'success' : 'none' });
				}).catch(function(err) {
					self.loading = false;
					self.addLog('error', '网络错误：' + (err && err.message || err));
					uni.showToast({ title: '停止失败', icon: 'none' });
				});
			},

			addLog: function(type, msg) {
				var now = new Date();
				var h = String(now.getHours()).padStart(2, '0');
				var m = String(now.getMinutes()).padStart(2, '0');
				var s = String(now.getSeconds()).padStart(2, '0');
				this.logs.push({ type: type, msg: msg, time: h + ':' + m + ':' + s });
				if (this.logs.length > 50) this.logs.shift();
			},
		}
	});
</script>

<style scoped>
.ai-page{min-height:100vh;background:#1a1a2e;color:#eee;display:flex;flex-direction:column;padding:12px;box-sizing:border-box}

/* 顶栏 */
.top-bar{display:flex;align-items:center;justify-content:space-between;height:44px;margin-bottom:16px;padding:0 8px}
.btn-back{position:fixed;top:20px;left:20px;z-index:10;background:#333;color:#fff;border:none;border-radius:8px;font-size:14px;padding:6px 14px;line-height:1}
.page-title{font-size:18px;font-weight:700;color:#fff}
.status-mini{padding:3px 10px;border-radius:10px;font-size:11px;background:#555;color:#aaa}
.status-mini.online{background:#1a5f2a;color:#5fda5f}

/* 卡片 */
.card{background:#222;border-radius:12px;margin-bottom:16px;overflow:hidden;border:1px solid #333}
.card-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid #333}
.card-title{font-size:15px;font-weight:600;color:#fff}
.btn-clear{background:none;border:1px solid #555;color:#999;font-size:11px;padding:2px 10px;border-radius:6px}
.card-body{padding:16px}

/* AI状态 */
.ai-status{padding:4px 12px;border-radius:12px;font-size:12px;background:#444;color:#888}
.ai-status.on{background:#1a5f2a;color:#5fda5f}

.desc{font-size:13px;color:#aaa;line-height:1.6;margin-bottom:16px}

/* 按钮 */
.btn-row{display:flex;justify-content:center;margin-bottom:20px}
.btn-start,.btn-stop{border:none;border-radius:10px;font-size:16px;padding:14px 40px;font-weight:600;width:80%;max-width:300px}
.btn-start{background:linear-gradient(135deg,#1a7f37,#28a745);color:#fff}
.btn-start[disabled]{opacity:.5}
.btn-stop{background:linear-gradient(135deg,#b71c1c,#d32f2f);color:#fff}
.btn-stop[disabled]{opacity:.5}

/* 提示 */
.tips-box{background:#1a1a2e;border-radius:8px;padding:12px 14px;border:1px solid #333}
.tips-title{font-size:13px;font-weight:600;color:#88c;display:block;margin-bottom:8px}
.tip-item{display:block;font-size:12px;color:#99a;line-height:1.8}

/* 日志 */
.log-area{height:200px}
.log-scroll{height:100%}
.log-item{display:flex;padding:6px 12px;border-bottom:1px solid #2a2a3e;font-size:12px}
.log-time{color:#666;width:70px;flex-shrink:0}
.log-msg{color:#ccc;word-break:break-all}
.log-success .log-msg{color:#5fda5f}
.log-error .log-msg{color:#ff6b6b}
.log-warn .log-msg{color:#ffd93d}
.log-info .log-msg{color:#74c0fc}
</style>
