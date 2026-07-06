<template>
	<view class="agent-page">
		<!-- 顶部栏 -->
		<view class="top-bar">
			<button class="btn-back" @click="goBack">&#x25C0; 返回</button>
			<view class="status-mini" :class="{ online: loggedIn }">
				{{ loggedIn ? '已登录' : '未登录' }}
			</view>
		</view>

		<!-- 未登录：token 粘贴卡片 -->
		<view class="card" v-if="!loggedIn">
			<view class="card-header">
				<text class="card-title">&#x1F511; 登录小智控制台</text>
			</view>
			<view class="card-body">
				<text class="desc">粘贴小智控制台的 token 即可登录，配置修改后重启小野 AI 生效。token 只存在机器人本地，不会出现在 APP 里。</text>

				<view class="form-row form-col">
					<text class="label">控制台 Token</text>
					<textarea class="textarea" v-model="tokenInput" placeholder="粘贴 token（以 ghp_ 或 eyJ 开头）" :maxlength="-1" auto-height></textarea>
				</view>

				<button class="btn-start" @click="doSaveToken" :disabled="loggingIn">
					{{ loggingIn ? '验证中...' : '&#x1F511; 保存并验证' }}
				</button>

				<view class="tips-box">
					<text class="tips-title">&#x2139; 如何获取 token</text>
					<view class="tips-list">
						<text class="tip-item">1. 浏览器打开 https://xiaozhi.me/console/agents</text>
						<text class="tip-item">2. 登录控制台后按 F12 打开开发者工具</text>
						<text class="tip-item">3. 切到 Application → Local Storage → xiaozhi.me</text>
						<text class="tip-item">4. 复制 "token" 那一行的值粘到这里</text>
						<text class="tip-item">5. token 几周到几个月过期，过期后重新粘贴</text>
					</view>
				</view>
			</view>
		</view>

		<!-- 已登录：配置卡片 -->
		<view v-else>
			<!-- 智能体选择 -->
			<view class="card">
				<view class="card-header">
					<text class="card-title">&#x1F916; 智能体</text>
					<button class="btn-clear" @click="doLogout">退出</button>
				</view>
				<view class="card-body">
					<view class="form-row">
						<text class="label">当前智能体</text>
						<picker class="picker" :range="agentNames" :value="agentIndex" @change="onAgentChange">
							<view class="picker-text">{{ agentNames[agentIndex] || '未选择' }}</view>
						</picker>
					</view>
				</view>
			</view>

			<!-- 配置表单 -->
			<view class="card" v-if="config">
				<view class="card-header">
					<text class="card-title">&#x2699; 智能体配置</text>
					<text class="agent-id-tag">ID: {{ currentAgentId }}</text>
				</view>
				<view class="card-body">
					<view class="form-row">
						<text class="label">智能体名称</text>
						<input class="input" v-model="config.agent_name" placeholder="名称" />
					</view>
					<view class="form-row">
						<text class="label">助手称呼</text>
						<input class="input" v-model="config.assistant_name" placeholder="助手称呼" />
					</view>

					<view class="form-row">
						<text class="label">对话语言</text>
						<picker class="picker" :range="languageOptions" range-key="label" :value="languageIdx" @change="onLanguageChange">
							<view class="picker-text">{{ languageOptions[languageIdx].label || '请选择' }}</view>
						</picker>
					</view>

					<view class="form-row">
						<text class="label">LLM 模型</text>
						<picker class="picker" :range="modelOptions" range-key="label" :value="modelIdx" @change="onModelChange">
							<view class="picker-text">{{ modelOptions[modelIdx].label || '请选择' }}</view>
						</picker>
					</view>

					<view class="form-row">
						<text class="label">角色音色</text>
						<picker class="picker" :range="voiceOptions" range-key="label" :value="voiceIdx" @change="onVoiceChange">
							<view class="picker-text">{{ voiceOptions[voiceIdx].label || '请选择' }}</view>
						</picker>
					</view>

					<view class="form-row">
						<text class="label">音调 ({{ config.tts_pitch }})</text>
						<slider :min="-10" :max="10" :step="1" :value="config.tts_pitch" @changing="onPitchChanging" @change="onPitchChange" activeColor="#28a745" block-size="20" />
					</view>
					<view class="form-row">
						<text class="label">语速</text>
						<picker class="picker" :range="speedOptions" :value="speedIdx" @change="onSpeedChange">
							<view class="picker-text">{{ config.tts_speech_speed }}</view>
						</picker>
					</view>

					<view class="form-row">
						<text class="label">人设提示词</text>
						<input class="input" v-model="config.character" placeholder="智能体人设描述" />
					</view>

					<view class="form-row form-col">
						<text class="label">记忆</text>
						<textarea class="textarea" v-model="config.memory" placeholder="记忆内容" :maxlength="-1" auto-height></textarea>
					</view>

					<view class="btn-row">
						<button class="btn-optimize" @click="doOptimizeCharacter" :disabled="optimizing">
							{{ optimizing ? 'AI 优化中...' : '&#x2728; AI 优化人设' }}
						</button>
						<button class="btn-start" @click="doSave" :disabled="saving">
							{{ saving ? '保存中...' : '&#x1F4BE; 保存配置' }}
						</button>
					</view>
					<button class="btn-apply" @click="doApply" :disabled="applying">
						{{ applying ? '重启中...' : '&#x1F501; 保存并重启小野 AI 生效' }}
					</button>
				</view>
			</view>

			<!-- 日志 -->
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
	</view>
</template>

<script>
import Vue from 'vue';
import * as g1Api from '../../api/g1';

export default Vue.extend({
	data: function() {
		return {
			// 登录态
			loggedIn: false,
			loggingIn: false,
			tokenInput: '',

			// 智能体列表
			agents: [],
			agentIndex: 0,

			// 配置
			config: null,
			saving: false,
			optimizing: false,
			applying: false,

			// 选项（动态拉取，跟控制台一致）
			languageOptions: [],  // [{label:'中文', value:'zh'}, ...]
			languageIdx: 0,
			modelOptions: [],     // [{label:'Qwen', value:'qwen'}, ...]
			modelIdx: 0,
			voiceOptions: [],     // [{label:'湾湾小何', value:'zh_female_...'}, ...] 随语言联动
			voiceIdx: 0,
			ttsVoices: {},        // {zh:[...], en:[...], ...} 全部音色，按语言分组
			speedOptions: ['slow', 'normal', 'fast'],
			speedIdx: 1,

			logs: [],
		}
	},

	computed: {
		agentNames: function() {
			return this.agents.map(function(a) {
				return a.agent_name || a.name || ('ID ' + (a.id || '?'));
			});
		},
		currentAgentId: function() {
			if (this.agents.length === 0) return '';
			var a = this.agents[this.agentIndex];
			return a.id || a.agent_id || '';
		},
	},

	onLoad: function() {
		this.init();
	},

	onShow: function() {
		// 已登录但还没拉配置时补拉
		if (this.loggedIn && !this.config) this.loadConfig();
	},

	methods: {
		goBack: function() {
			var pages = getCurrentPages();
			if (pages.length > 1) { uni.navigateBack(); }
			else { uni.reLaunch({ url: '/pages/index/index' }); }
		},

		init: function() {
			var self = this;
			g1Api.agentAuthStatus().then(function(r) {
				var d = r.data || {};
				if (d.logged_in) {
					self.loggedIn = true;
					self.addLog('success', '已登录控制台');
					// 先拉选项数据，再列智能体（loadConfig 时要用来匹配 picker）
					self.loadOptions().then(function() {
						self.loadAgents();
					}).catch(function() {
						self.loadAgents();
					});
				} else {
					self.loggedIn = false;
				}
			}).catch(function() {
				self.loggedIn = false;
			});
		},

		// 语言代码 → 中文显示名（全中文，跟控制台 i18n 一致）
		LANG_NAMES: {
			zh: '中文', en: '英语', ja: '日语', yue: '粤语', vi: '越南语',
			fr: '法语', ar: '阿拉伯语', es: '西班牙语', ru: '俄语', ko: '韩语',
			it: '意大利语', id: '印尼语', hi: '印地语', fi: '芬兰语', th: '泰语',
			de: '德语', pt: '葡萄牙语', uk: '乌克兰语', tr: '土耳其语', cs: '捷克语',
			pl: '波兰语', ro: '罗马尼亚语', ms: '马来语', sl: '斯洛文尼亚语', nl: '荷兰语',
			bg: '保加利亚语', da: '丹麦语', he: '希伯来语', sk: '斯洛伐克语', sv: '瑞典语',
			hr: '克罗地亚语', hu: '匈牙利语', ca: '加泰罗尼亚语', fa: '波斯语', el: '希腊语',
			no: '挪威语', fil: '菲律宾语',
		},

		// ===== 拉取选项（语言/模型/音色，跟控制台一致）=====
		loadOptions: function() {
			var self = this;
			// 并行拉模型和音色列表
			var p1 = g1Api.agentModels().then(function(r) {
				if (r.success && r.data && r.data.models) {
					self.modelOptions = r.data.models.map(function(m) {
						return { label: m.description || m.name, value: m.name };
					});
				}
			}).catch(function() {});

			var p2 = g1Api.agentTtsList().then(function(r) {
				if (r.success && r.data) {
					var langs = r.data.languages || [];
					self.languageOptions = langs.map(function(code) {
						return { label: self.LANG_NAMES[code] || code, value: code };
					});
					self.ttsVoices = r.data.tts_voices || {};
				}
			}).catch(function() {});

			return Promise.all([p1, p2]);
		},

		// 根据当前语言刷新音色下拉选项
		refreshVoices: function() {
			var lang = this.config.language || 'zh';
			var list = this.ttsVoices[lang] || [];
			// top=true 的排前面（跟控制台一致）
			list = list.slice().sort(function(a, b) {
				return (b.top ? 1 : 0) - (a.top ? 1 : 0);
			});
			this.voiceOptions = list.map(function(v) {
				return { label: v.voice_name + (v.top ? ' ★' : ''), value: v.voice_id };
			});
			// 匹配当前 tts_voice
			this.voiceIdx = 0;
			var cur = this.config.tts_voice || '';
			for (var i = 0; i < this.voiceOptions.length; i++) {
				if (this.voiceOptions[i].value === cur) { this.voiceIdx = i; break; }
			}
		},

		// ===== token 登录 =====
		doSaveToken: function() {
			var self = this;
			var token = (this.tokenInput || '').trim();
			if (!token) {
				uni.showToast({ title: '请粘贴 token', icon: 'none' });
				return;
			}
			this.loggingIn = true;
			this.addLog('info', '正在验证 token...');
			g1Api.agentSaveToken(token).then(function(r) {
				// token 已存后端，再调 auth_status 验证有效性
				return g1Api.agentAuthStatus();
			}).then(function(r) {
				self.loggingIn = false;
				var d = r.data || {};
				if (d.logged_in) {
					self.loggedIn = true;
					self.tokenInput = '';
					self.addLog('success', 'token 有效，登录成功');
					uni.showToast({ title: '登录成功', icon: 'success' });
					self.loadAgents();
				} else {
					self.addLog('error', d.reason || 'token 无效');
					uni.showToast({ title: d.reason || 'token 无效', icon: 'none' });
				}
			}).catch(function(err) {
				self.loggingIn = false;
				self.addLog('error', '网络错误：' + (err && err.message || err));
				uni.showToast({ title: '登录失败', icon: 'none' });
			});
		},

		doLogout: function() {
			var self = this;
			g1Api.agentLogout().then(function() {
				self.loggedIn = false;
				self.config = null;
				self.agents = [];
				self.addLog('info', '已退出登录');
			}).catch(function() {});
		},

		// ===== 智能体列表 =====
		loadAgents: function() {
			var self = this;
			g1Api.agentList().then(function(r) {
				if (r.success && r.data && r.data.items) {
					var items = r.data.items || [];
					self.agents = items;
					var curId = null;
					if (r.data.agent_id) curId = String(r.data.agent_id);
					var idx = 0;
					for (var i = 0; i < items.length; i++) {
						if (String(items[i].id || '') === curId) { idx = i; break; }
					}
					self.agentIndex = idx;
					self.loadConfig();
				} else {
					uni.showToast({ title: r.message || '拉取智能体失败', icon: 'none' });
				}
			}).catch(function() {
				uni.showToast({ title: '网络错误', icon: 'none' });
			});
		},

		onAgentChange: function(e) {
			var self = this;
			this.agentIndex = e.detail.value;
			var newId = this.currentAgentId;
			if (!newId) return;
			g1Api.agentSelect(newId).then(function() {
				self.config = null;
				self.loadConfig();
			}).catch(function() {});
		},

		// ===== 配置 =====
		loadConfig: function() {
			var self = this;
			if (!this.currentAgentId) return;
			this.addLog('info', '读取配置...');
			g1Api.agentGetConfig().then(function(r) {
				if (r.success && r.data) {
					var c = r.data;
					c.agent_name = c.agent_name || c.name || '';
					c.assistant_name = c.assistant_name || '';
					c.character = c.character || '';
					c.memory = c.memory || '';
					c.language = c.language || 'zh';
					c.llm_model = c.llm_model || '';
					c.tts_voice = c.tts_voice || c.voice_id || '';
					c.tts_pitch = c.tts_pitch || 0;
					c.tts_speech_speed = c.tts_speech_speed || 'normal';
					self.config = c;
					self.syncPickers();
					self.addLog('success', '配置已读取');
				} else {
					uni.showToast({ title: r.message || '读取配置失败', icon: 'none' });
				}
			}).catch(function() {
				uni.showToast({ title: '网络错误', icon: 'none' });
			});
		},

		syncPickers: function() {
			var self = this;
			// 语言
			this.languageIdx = 0;
			this.languageOptions.forEach(function(o, i) {
				if (o.value === self.config.language) self.languageIdx = i;
			});
			// 音色随语言联动
			this.refreshVoices();
			// 模型
			this.modelIdx = 0;
			this.modelOptions.forEach(function(o, i) {
				if (o.value === self.config.llm_model) self.modelIdx = i;
			});
			// 语速
			this.speedIdx = this.speedOptions.indexOf(this.config.tts_speech_speed);
			if (this.speedIdx < 0) this.speedIdx = 1;
		},

		onLanguageChange: function(e) {
			this.languageIdx = e.detail.value;
			this.config.language = this.languageOptions[this.languageIdx].value;
			// 语言变了，音色列表跟着变，默认选该语言第一个音色
			this.refreshVoices();
			if (this.voiceOptions.length > 0) {
				this.config.tts_voice = this.voiceOptions[0].value;
			}
		},
		onModelChange: function(e) {
			this.modelIdx = e.detail.value;
			this.config.llm_model = this.modelOptions[this.modelIdx].value;
		},
		onVoiceChange: function(e) {
			this.voiceIdx = e.detail.value;
			this.config.tts_voice = this.voiceOptions[this.voiceIdx].value;
		},
		onPitchChanging: function(e) {
			// 拖动过程中实时更新（让数字跟着动，避免滑块卡住的视觉错觉）
			this.config.tts_pitch = e.detail.value;
		},
		onPitchChange: function(e) {
			// 松手时最终确认
			this.config.tts_pitch = e.detail.value;
		},
		onSpeedChange: function(e) {
			this.speedIdx = e.detail.value;
			this.config.tts_speech_speed = this.speedOptions[this.speedIdx];
		},

		// ===== 保存 / 优化 / 生效 =====
		buildPayload: function() {
			var c = this.config;
			return {
				agent_name: c.agent_name,
				assistant_name: c.assistant_name,
				character: c.character,
				language: c.language,
				llm_model: c.llm_model,
				tts_voice: c.tts_voice,
				tts_pitch: Number(c.tts_pitch),
				tts_speech_speed: c.tts_speech_speed,
				memory: c.memory,
			};
		},

		doSave: function() {
			var self = this;
			this.saving = true;
			this.addLog('info', '保存配置...');
			g1Api.agentSaveConfig(this.buildPayload()).then(function(r) {
				self.saving = false;
				if (r.success) {
					self.addLog('success', '配置已保存到云端');
					uni.showToast({ title: '已保存', icon: 'success' });
				} else {
					self.addLog('error', r.message || '保存失败');
					uni.showToast({ title: r.message || '保存失败', icon: 'none' });
				}
			}).catch(function(err) {
				self.saving = false;
				self.addLog('error', '网络错误：' + (err && err.message || err));
				uni.showToast({ title: '保存失败', icon: 'none' });
			});
		},

		doApply: function() {
			var self = this;
			this.saving = true;
			this.addLog('info', '保存并重启小野 AI...');
			g1Api.agentSaveConfig(this.buildPayload()).then(function(r) {
				self.saving = false;
				if (!r.success) {
					self.addLog('error', r.message || '保存失败');
					uni.showToast({ title: r.message || '保存失败', icon: 'none' });
					return;
				}
				self.applying = true;
				return g1Api.agentApply();
			}).then(function(r) {
				self.applying = false;
				if (r && r.success) {
					self.addLog('success', '小野 AI 已重启，新配置生效');
					uni.showToast({ title: '已重启生效', icon: 'success' });
				} else if (r) {
					self.addLog('warn', r.message || '重启失败');
					uni.showToast({ title: r.message || '重启失败', icon: 'none' });
				}
			}).catch(function(err) {
				self.saving = false;
				self.applying = false;
				self.addLog('error', '网络错误：' + (err && err.message || err));
				uni.showToast({ title: '操作失败', icon: 'none' });
			});
		},

		doOptimizeCharacter: function() {
			var self = this;
			if (!this.config.character) {
				uni.showToast({ title: '请先填写人设', icon: 'none' });
				return;
			}
			this.optimizing = true;
			this.addLog('info', 'AI 优化人设中...');
			g1Api.agentOptimizeCharacter(this.config.character).then(function(r) {
				self.optimizing = false;
				if (r.success && r.data) {
					var newChar = r.data.character || r.data.optimized_character || r.data.text || '';
					if (newChar) {
						self.config.character = newChar;
						self.addLog('success', '人设已优化');
						uni.showToast({ title: '已优化', icon: 'success' });
					} else {
						self.addLog('warn', '优化响应无文本');
						uni.showToast({ title: '未返回优化结果', icon: 'none' });
					}
				} else {
					self.addLog('error', r.message || '优化失败');
					uni.showToast({ title: r.message || '优化失败', icon: 'none' });
				}
			}).catch(function(err) {
				self.optimizing = false;
				self.addLog('error', '网络错误：' + (err && err.message || err));
				uni.showToast({ title: '优化失败', icon: 'none' });
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
.agent-page{min-height:100vh;background:#1a1a2e;color:#eee;display:flex;flex-direction:column;padding:12px;box-sizing:border-box}

.top-bar{display:flex;align-items:center;justify-content:space-between;height:44px;margin-bottom:16px;padding:0 8px}
.btn-back{position:fixed;top:20px;left:20px;z-index:10;background:#333;color:#fff;border:none;border-radius:8px;font-size:14px;padding:6px 14px;line-height:1}
.status-mini{padding:3px 10px;border-radius:10px;font-size:11px;background:#555;color:#aaa}
.status-mini.online{background:#1a5f2a;color:#5fda5f}

.card{background:#222;border-radius:12px;margin-bottom:16px;overflow:hidden;border:1px solid #333}
.card-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid #333}
.card-title{font-size:15px;font-weight:600;color:#fff}
.agent-id-tag{font-size:11px;color:#888;background:#2a2a3e;padding:2px 8px;border-radius:6px}
.card-body{padding:16px}

.desc{font-size:13px;color:#aaa;line-height:1.6;margin-bottom:16px}

.form-row{display:flex;align-items:center;margin-bottom:14px;min-height:40px}
.form-row.form-col{flex-direction:column;align-items:stretch}
.label{width:90px;flex-shrink:0;font-size:13px;color:#9af;padding-right:8px}
.input{flex:1;background:#1a1a2e;border:1px solid #444;border-radius:8px;padding:10px 12px;color:#eee;font-size:14px;height:40px;box-sizing:border-box}
.textarea{background:#1a1a2e;border:1px solid #444;border-radius:8px;padding:10px 12px;color:#eee;font-size:13px;min-height:80px;width:100%;box-sizing:border-box;margin-top:6px}

.picker{flex:1;background:#1a1a2e;border:1px solid #444;border-radius:8px;height:40px;display:flex;align-items:center;padding:0 12px}
.picker-text{color:#eee;font-size:14px}

.btn-row{display:flex;justify-content:space-between;margin:8px 0}
.btn-row button{flex:1;margin:0 4px}
.btn-start{background:linear-gradient(135deg,#1a7f37,#28a745);color:#fff;border:none;border-radius:10px;font-size:15px;padding:12px 0;font-weight:600}
.btn-start[disabled]{opacity:.5}
.btn-optimize{background:linear-gradient(135deg,#1565c0,#1976d2);color:#fff;border:none;border-radius:10px;font-size:15px;padding:12px 0;font-weight:600}
.btn-optimize[disabled]{opacity:.5}
.btn-apply{width:100%;background:linear-gradient(135deg,#b71c1c,#d32f2f);color:#fff;border:none;border-radius:10px;font-size:15px;padding:12px 0;font-weight:600;margin-top:8px}
.btn-apply[disabled]{opacity:.5}

.btn-clear{background:none;border:1px solid #555;color:#999;font-size:11px;padding:2px 10px;border-radius:6px}

.tips-box{background:#1a1a2e;border-radius:8px;padding:12px 14px;border:1px solid #333;margin-top:16px}
.tips-title{font-size:13px;font-weight:600;color:#88c;display:block;margin-bottom:8px}
.tip-item{display:block;font-size:12px;color:#99a;line-height:1.8}

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
