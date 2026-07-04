<template>
	<view class="voice-page">
		<view class="top-bar">
			<button class="btn-back" @click="goBack">&#x25C0; 返回</button>
			<text class="page-title">语音动作输出</text>
			<view class="status-dot-wrap">
				<view class="status-dot" :class="{ ready: vaReady && socketReady, executing: vaExecuting }"></view>
				<text class="status-text">{{ statusLabel }}</text>
			</view>
		</view>

		<view class="card" v-if="!vaReady && !loadingInit">
			<text class="warn-text">&#x26A0; 系统未就绪，请确认机器人已初始化</text>
		</view>

		<view class="card" v-if="!socketReady && socketError">
			<text class="warn-text">&#x26A0; {{ socketError }}</text>
		</view>

		<view class="card">
			<view class="card-header"><text class="card-title">&#x1F3AC; 选择动作</text></view>
			<view class="action-grid">
				<view v-for="(a, id) in actions" :key="id"
					class="action-btn" :class="{ selected: selectedActionId === Number(id) }"
					@click="selectAction(Number(id))">
					<text class="action-name">{{ a.name }}</text>
					<text class="action-desc">{{ a.desc }}</text>
				</view>
			</view>
		</view>

		<view class="card card-input">
			<view class="card-header"><text class="card-title">&#x270F; 输入文本</text></view>
			<textarea class="va-textarea" v-model="inputText"
				placeholder="请输入要播放的语音内容..." :maxlength="200"></textarea>
			<view class="preset-row">
				<view class="preset-cat">
					<text class="preset-cat-label">&#x1F4DD; 预设文本</text>
					<view class="preset-items">
						<text v-for="(cat, catKey) in presets" :key="catKey" class="preset-cat-btn" @click="showPresets(cat)">
							{{ cat.label }}
						</text>
					</view>
				</view>
			</view>
			<view class="preset-list" v-if="showPresetList">
				<text v-for="(v, vi) in currentPresetVoices" :key="vi" class="preset-item"
					@click="usePreset(v)">{{ v }}</text>
			</view>
		</view>

		<view class="card card-btns">
			<view class="btn-row-main">
				<button class="btn-combo" :disabled="buttonsDisabled || (!inputText.trim() && selectedActionId === null)" @click="doExecute">
					&#x1F399; 语音+动作
				</button>
				<button class="btn-speak" :disabled="buttonsDisabled || !inputText.trim()" @click="doSpeakOnly">
					&#x1F50A; 播放语音
				</button>
			</view>
			<view class="btn-row-main">
				<button class="btn-action" :disabled="buttonsDisabled || selectedActionId === null" @click="doActionOnly">
					&#x1F3AC; 执行动作
				</button>
				<button class="btn-reset" :disabled="buttonsDisabled" @click="doResetArm">
					&#x1F504; 释放手臂
				</button>
			</view>
		</view>

		<view class="card card-result" v-if="resultVisible">
			<view class="card-header">
				<text class="card-title">&#x1F4CB; 执行结果</text>
				<button class="btn-close-result" @click="resultVisible = false">&#x2715;</button>
			</view>
			<view class="result-content" :class="'result-' + resultType">
				<text class="result-tag">[{{ resultTypeUpper }}]</text>
				<text class="result-msg">{{ resultMsg }}</text>
			</view>
		</view>
	</view>
</template>

<script>
	import Vue from 'vue';
	import * as g1Api from '../../api/g1';
	import {
		connectVoiceSocket,
		disconnectVoiceSocket,
		emitVoiceExecute,
		emitVoiceSpeakOnly,
		emitVoiceActionOnly
	} from '../../api/voiceSocket';

	export default Vue.extend({
		data: function() {
			return {
				actions: {},
				presets: {},
				selectedActionId: null,
				inputText: '',
				vaReady: false,
				vaExecuting: false,
				loadingInit: true,
				socketReady: false,
				socketError: '',

				resultVisible: false,
				resultType: '',
				resultMsg: '',

				showPresetList: false,
				currentPresetVoices: [],
				operationTimer: null
			}
		},
		computed: {
			statusLabel: function() {
				if (this.vaExecuting) return '执行中...';
				if (!this.socketReady) return '连接中...';
				if (this.vaReady) return '系统就绪';
				if (!this.loadingInit) return '系统未就绪';
				return '加载中...';
			},
			resultTypeUpper: function() { return (this.resultType || '').toUpperCase(); },
			buttonsDisabled: function() { return this.vaExecuting; }
		},

		onLoad: function() {
			g1Api.loadSavedAddress();
			this.loadVoiceData();
		},
		onShow: function() {
			this.resetPageExecutingState();
			this.loadVoiceData();
			if (!this.socketReady) this.initVoiceSocket();
		},
		onHide: function() {
			this.resetPageExecutingState();
		},
		onUnload: function() {
			this.resetPageExecutingState();
			disconnectVoiceSocket(false);
		},

		methods: {
			goBack: function() {
				var pages = getCurrentPages();
				if (pages.length > 1) { uni.navigateBack(); }
				else { uni.reLaunch({ url: '/pages/index/index' }); }
			},

			loadVoiceData: function() {
				var self = this;
				self.loadingInit = true;
				g1Api.getVoiceActions().then(function(r) {
					self.actions = r.actions || {};
					self.presets = r.preset_voices || {};
					self.vaReady = true;
					self.vaExecuting = !!r.executing;
					if (self.vaExecuting) self.startOperationTimeout('上一次任务应已完成', 5000);
					self.loadingInit = false;
				}).catch(function(err) {
					self.loadingInit = false;
					console.error('加载语音动作数据失败', err);
				});
			},

			initVoiceSocket: function() {
				var self = this;
				this.socketReady = false;
				this.socketError = '';
				return connectVoiceSocket(function(data) { self.handleVoiceStatus(data || {}); }).then(function() {
					self.socketReady = true;
					self.socketError = '';
				}).catch(function(err) {
					self.socketReady = false;
					self.socketError = (err && err.message) ? err.message : 'Socket.IO连接失败';
				});
			},

			handleVoiceStatus: function(data) {
				if (data.status === 'executing') {
					this.vaExecuting = true;
					this.showResult('executing', data.message || '正在执行...');
					return;
				}

				this.finishOperation(data.status || 'completed', this.formatResult(data, data.message || '执行完成'));
			},

			clearOperationTimer: function() {
				if (this.operationTimer) {
					clearTimeout(this.operationTimer);
					this.operationTimer = null;
				}
			},

			startOperationTimeout: function(message, timeoutMs) {
				var self = this;
				this.clearOperationTimer();
				this.operationTimer = setTimeout(function() {
					if (!self.vaExecuting) return;
					self.finishOperation('completed', message || '执行已发送，机器人应已完成。如未完成请稍后再试。');
				}, timeoutMs || 15000);
			},

			finishOperation: function(type, msg) {
				this.clearOperationTimer();
				this.vaExecuting = false;
				this.showResult(type, msg);
				this.loadVoiceData();
			},

			resetPageExecutingState: function() {
				this.clearOperationTimer();
				this.vaExecuting = false;
			},

			selectAction: function(id) {
				this.selectedActionId = this.selectedActionId === id ? null : id;
			},

			showPresets: function(cat) {
				this.currentPresetVoices = cat.voices || [];
				this.showPresetList = !this.showPresetList;
			},

			usePreset: function(text) {
				this.inputText = text;
				this.showPresetList = false;
			},

			showResult: function(type, msg) {
				this.resultType = type;
				this.resultMsg = msg;
				this.resultVisible = true;
			},

			formatResult: function(r, fallback) {
				if (r.results && r.results.length) {
					return r.results.map(function(item) {
						var icon = item.success ? '✓' : '✗';
						return icon + ' ' + item.message;
					}).join('\n');
				}
				return r.message || fallback;
			},

			ensureSocket: function() {
				if (this.socketReady) return Promise.resolve();
				return this.initVoiceSocket();
			},

				doExecute: function() {
					if (!this.inputText.trim() && this.selectedActionId === null) {
						uni.showToast({ title: '请输入语音或选择动作', icon: 'none' });
						return;
					}
					var self = this;
					this.ensureSocket().then(function() {
						self.vaExecuting = true;
						self.showResult('executing', '正在执行语音+动作...');
						emitVoiceExecute(self.inputText.trim(), self.selectedActionId, true);
						var duration = Math.max(12000, self.inputText.trim().length * 220 + 7000);
						self.startOperationTimeout('语音+动作执行完成', duration);
					}).catch(function(err) {
						self.clearOperationTimer();
						self.vaExecuting = false;
						self.showResult('error', (err && err.message) ? err.message : 'Socket.IO连接失败');
					});
				},

				doSpeakOnly: function() {
					var text = this.inputText.trim();
					if (!text) { uni.showToast({ title: '请输入语音内容', icon: 'none' }); return; }
					var self = this;
					this.ensureSocket().then(function() {
						self.vaExecuting = true;
						self.showResult('executing', '正在播放语音...');
						emitVoiceSpeakOnly(text);
						var duration = Math.max(3000, text.length * 220 + 1500);
						self.startOperationTimeout('语音播放完成', duration);
					}).catch(function(err) {
						self.clearOperationTimer();
						self.vaExecuting = false;
						self.showResult('error', (err && err.message) ? err.message : 'Socket.IO连接失败');
					});
				},

				doActionOnly: function() {
					if (this.selectedActionId === null) { uni.showToast({ title: '请先选择动作', icon: 'none' }); return; }
					var self = this;
					this.ensureSocket().then(function() {
						self.vaExecuting = true;
						self.showResult('executing', '正在执行动作...');
						emitVoiceActionOnly(self.selectedActionId);
						self.startOperationTimeout('动作执行完成', 5000);
					}).catch(function(err) {
						self.clearOperationTimer();
						self.vaExecuting = false;
						self.showResult('error', (err && err.message) ? err.message : 'Socket.IO连接失败');
					});
				},

				doResetArm: function() {
					var self = this;
					this.ensureSocket().then(function() {
						self.vaExecuting = true;
						self.showResult('executing', '正在释放手臂...');
						emitVoiceActionOnly(0);
						self.startOperationTimeout('释放手臂完成', 5000);
					}).catch(function(err) {
						self.clearOperationTimer();
						self.vaExecuting = false;
						self.showResult('error', (err && err.message) ? err.message : 'Socket.IO连接失败');
					});
				}
		}
	});
</script>

<style scoped>
	.voice-page{min-height:100vh;background:#1a1a2e;color:#eee;display:flex;flex-direction:column;padding:12px;box-sizing:border-box}

	.top-bar{display:flex;align-items:center;justify-content:center;height:44px;margin-bottom:12px;position:relative}
	.btn-back{position:absolute;top:0;left:12px;z-index:10;background:#333;color:#fff;border:none;border-radius:8px;font-size:14px;padding:6px 14px;line-height:1}
	.page-title{font-size:17px;font-weight:700;color:#fff}
	.status-dot-wrap{display:flex;align-items:center;gap:6px}
	.status-dot{width:10px;height:10px;border-radius:50%;background:#ef4444}
	.status-dot.ready{background:#4ade80}
	.status-dot.executing{background:#fbbf24;animation:pulse 1s infinite}
	@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
	.status-text{font-size:11px;color:#999}

	.card{background:#222;border-radius:12px;margin-bottom:12px;overflow:hidden;border:1px solid #333}
	.card-header{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid #333}
	.card-title{font-size:14px;font-weight:600;color:#fff}

	.warn-text{display:block;padding:12px 16px;font-size:13px;color:#fbbf24;text-align:center}

	.action-grid{padding:12px;display:flex;flex-wrap:wrap;gap:8px}
	.action-btn{width:calc(33.33% - 6px);min-width:100px;background:#2a2a3e;border-radius:10px;padding:10px 8px;border:2px solid transparent;box-sizing:border-box;text-align:center}
	.action-btn.selected{border-color:#007aff;background:rgba(0,122,255,.15)}
	.action-btn:active{opacity:.7}
	.action-name{display:block;font-size:13px;color:#fff;font-weight:600;margin-bottom:4px}
	.action-desc{display:block;font-size:10px;color:#888;line-height:1.3}

	.card-input{padding:12px}
	.va-textarea{width:100%;height:80px;padding:10px;background:#1a1a2e;color:#999;border:1px solid #333;border-radius:8px;font-size:13px;box-sizing:border-box;line-height:1.5;margin-bottom:10px}
	.preset-row{margin-bottom:8px}
	.preset-cat-label{display:block;font-size:12px;color:#d97706;font-weight:600;margin-bottom:6px}
	.preset-items{display:flex;flex-wrap:wrap;gap:6px}
	.preset-cat-btn{display:inline-block;padding:4px 10px;background:#2a2a3e;border-radius:6px;font-size:11px;color:#ccc;border:1px solid #444}
	.preset-cat-btn:active{background:#333}
	.preset-list{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;padding-top:8px;border-top:1px solid #333}
	.preset-item{display:inline-block;padding:4px 10px;background:#2a2a3e;border-radius:6px;font-size:11px;color:#ccc;border:1px solid #444}
	.preset-item:active{background:#333}

	.card-btns{padding:14px}
	.btn-row-main{display:flex;gap:10px;margin-bottom:12px}
	.btn-combo{flex:1;background:linear-gradient(135deg,#7c3aed,#a78bfa);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;padding:14px 0}
	.btn-combo[disabled]{opacity:.4}
	.btn-speak{flex:1;background:linear-gradient(135deg,#2563eb,#60a5fa);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;padding:14px 0}
	.btn-speak[disabled]{opacity:.4}
	.btn-action{flex:2;background:linear-gradient(135deg,#059669,#34d399);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;padding:14px 0}
	.btn-action[disabled]{opacity:.4}
	.btn-reset{flex:1;background:#333;color:#f59e0b;border:1px solid #f59e0b;border-radius:10px;font-size:14px;font-weight:600;padding:14px 0}
	.btn-reset[disabled]{opacity:.4}

	.btn-close-result{background:none;border:1px solid #555;color:#999;font-size:11px;padding:2px 10px;border-radius:6px}
	.result-content{padding:12px 14px;font-size:13px;line-height:1.6;white-space:pre-line}
	.result-tag{font-weight:700;margin-right:6px}
	.result-executing .result-tag{color:#fbbf24}
	.result-completed .result-tag{color:#4ade80}
	.result-error .result-tag{color:#f87171}
	.result-executing .result-msg{color:#ddd}
	.result-completed .result-msg{color:#cfe}
	.result-error .result-msg{color:#fcc}
</style>
