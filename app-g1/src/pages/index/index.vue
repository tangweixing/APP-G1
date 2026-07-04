<template>
	<view class="home">
		<view class="bg-glow bg-glow-1"></view>
		<view class="bg-glow bg-glow-2"></view>

		<view class="top-bar">
			<view class="brand">
				<text class="brand-icon">&#x1F916;</text>
				<text class="brand-name">G1 机器人</text>
			</view>
			<view class="conn-dot" :class="{ online: initialized }">
				{{ initialized ? '已连接' : '未连接' }}
			</view>
		</view>

		<view class="hero">
			<text class="hero-title">机器人控制中心</text>
			<text class="hero-sub">Unitree G1 二次开发版</text>
		</view>

		<!-- 连接设置 -->
		<view class="settings-card">
			<view class="settings-row">
				<input class="ip-input" type="text" v-model="inputIp"
					placeholder="IP地址 (留空走代理)" :disabled="initialized" />
				<button class="btn-save" :class="{ disabled: initialized }" @click="handleSaveAddress">
					{{ initialized ? '锁定' : '保存' }}
				</button>
				<button v-if="!initialized" class="btn-connect" @click="handleInit" :loading="initLoading">连接</button>
			</view>
		</view>

		<!-- 运动控制入口（大卡片） -->
		<view class="main-entry" @click="goMotion">
			<view class="entry-icon-wrap">
				<text class="entry-icon">&#x1F3CD;</text>
			</view>
			<view class="entry-info">
				<text class="entry-title">运动控制</text>
				<text class="entry-desc">双虚拟摇杆 · 档位切换 · 手部动作 · 模式切换</text>
			</view>
			<view class="entry-right">
				<text class="entry-go" v-if="initialized">进入 &#x25B6;</text>
				<text class="entry-lock" v-else>&#128274; 请先连接</text>
			</view>
		</view>

		<!-- AI控制入口 -->
		<view class="main-entry entry-ai" @click="goAI">
			<view class="entry-icon-wrap icon-ai">
				<text class="entry-icon">&#x1F916;</text>
			</view>
			<view class="entry-info">
				<text class="entry-title">AI 控制</text>
				<text class="entry-desc">小野AI语音助手 · 唤醒词交互 · 语音指令控制</text>
			</view>
			<view class="entry-right">
				<text class="entry-go" v-if="initialized">进入 &#x25B6;</text>
				<text class="entry-lock" v-else>&#128274; 请先连接</text>
			</view>
		</view>

		<!-- 语音动作输出入口 -->
		<view class="main-entry entry-voice" @click="goVoice">
			<view class="entry-icon-wrap icon-voice">
				<text class="entry-icon">&#x1F3A4;</text>
			</view>
			<view class="entry-info">
				<text class="entry-title">语音动作输出</text>
				<text class="entry-desc">输入文本 + 选择动作 &#x22C5; 语音播放 + 机械臂执行</text>
			</view>
			<view class="entry-right">
				<text class="entry-go" v-if="initialized">进入 &#x25B6;</text>
				<text class="entry-lock" v-else>&#128274; 请先连接</text>
			</view>
		</view>

		<!-- 视觉识别入口 -->
		<view class="main-entry entry-vision" @click="goVision">
			<view class="entry-icon-wrap icon-vision">
				<text class="entry-icon">&#x1F441;</text>
			</view>
			<view class="entry-info">
				<text class="entry-title">视觉识别模块</text>
				<text class="entry-desc">人脸识别 &#x22C5; 手势识别 &#x22C5; 实时日志</text>
			</view>
			<view class="entry-right">
				<text class="entry-go" v-if="initialized">进入 &#x25B6;</text>
				<text class="entry-lock" v-else>&#128274; 请先连接</text>
			</view>
		</view>

		<!-- 底部状态 -->
		<view class="footer-status" v-if="initialized">
			<text class="fi">Vx: {{ velocity.vx }}</text>
			<text class="fd">|</text>
			<text class="fi">Vy: {{ velocity.vy }}</text>
			<text class="fd">|</text>
			<text class="fi">Wz: {{ velocity.wz }}</text>
			<text class="fd">|</text>
			<text class="fi">{{ currentGear }}档</text>
		</view>

		<view class="hint-bar"><text>点击上方卡片进入运动控制面板</text></view>
	</view>
</template>

<script lang="ts">
	import Vue from 'vue';
	import * as g1Api from '../../api/g1';

	export default Vue.extend({
		data() {
			return {
				initialized: false,
				initLoading: false,
				currentGear: 1,
				velocity: { vx: '0.000', vy: '0.000', wz: '0.000' },
				inputIp: '',
				velocityTimer: null as number | null,
			}
		},
		onLoad() {
			this.loadSavedIp()
		},
		onUnload() {
			if (this.velocityTimer) clearInterval(this.velocityTimer)
		},
		methods: {
			loadSavedIp() {
				try { const s = uni.getStorageSync('g1_server_ip'); if (s) this.inputIp = s } catch (e) {}
			},
			handleSaveAddress() {
				const ip = this.inputIp.trim()
				if (ip) {
					g1Api.setServerAddress(ip)
					try { uni.setStorageSync('g1_server_ip', ip) } catch (e) {}
					uni.showToast({ title: '已保存', icon: 'success' })
				} else {
					g1Api.setServerAddress('')
					try { uni.removeStorageSync('g1_server_ip') } catch (e) {}
					uni.showToast({ title: '代理模式', icon: 'none' })
				}
			},
			async handleInit() {
				this.initLoading = true
				try {
					const res = await g1Api.initApi('eth0')
					if (res.success) {
						this.initialized = true
						uni.showToast({ title: '连接成功', icon: 'success' })
						this.startPoll(); this.fetchStatus()
					} else {
						uni.showToast({ title: res.message || '失败', icon: 'none' })
					}
				} catch (e: any) {
					uni.showToast({ title: '连接失败', icon: 'none' })
				} finally { this.initLoading = false }
			},
			async fetchStatus() {
				try {
					const r = await g1Api.getStatus()
					if (r.current_velocity) this.velocity = {
						vx: r.current_velocity.vx.toFixed(3),
						vy: r.current_velocity.vy.toFixed(3),
						wz: r.current_velocity.wz.toFixed(3)
					}
					this.currentGear = r.current_gear || 1
				} catch (e) {}
			},
			startPoll() {
				if (this.velocityTimer) return
				this.velocityTimer = setInterval(() => this.fetchStatus(), 500) as unknown as number
			},
			lockLandscape() {
				// #ifdef APP-PLUS
				plus.screen.lockOrientation('landscape-primary')
				// #endif
			},
			goMotion() {
				if (!this.initialized) { uni.showToast({ title: '请先连接机器人', icon: 'none' }); return }
				this.lockLandscape()
				uni.navigateTo({ url: '/pages/motion/motion' })
			},
			goAI() {
				if (!this.initialized) { uni.showToast({ title: '请先连接机器人', icon: 'none' }); return }
				this.lockLandscape()
				uni.navigateTo({ url: '/pages/ai/ai' })
			},
			goVoice() {
				if (!this.initialized) { uni.showToast({ title: '请先连接机器人', icon: 'none' }); return }
				this.lockLandscape()
				uni.navigateTo({ url: '/pages/voice/voice' })
			},
			goVision() {
				if (!this.initialized) { uni.showToast({ title: '请先连接机器人', icon: 'none' }); return }
				this.lockLandscape()
				uni.navigateTo({ url: '/pages/vision/vision' })
			},
		}
	});
</script>

<style>
	.home{min-height:100vh;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460);padding:30rpx 40rpx;position:relative;overflow:hidden}
	.bg-glow{position:absolute;border-radius:50%;filter:blur(80rpx);opacity:.15;z-index:0}
	.bg-glow-1{width:400rpx;height:400rpx;background:#007aff;top:-100rpx;right:-50rpx}
	.bg-glow-2{width:300rpx;height:300rpx;background:#ff9500;bottom:100rpx;left:-80rpx}

	.top-bar{display:flex;justify-content:space-between;align-items:center;position:relative;z-index:1;margin-bottom:20rpx}
	.brand{display:flex;align-items:center;gap:12rpx}
	.brand-icon{font-size:40rpx}
	.brand-name{font-size:32rpx;font-weight:bold;color:#fff}
	.conn-dot{padding:8rpx 24rpx;border-radius:24rpx;font-size:22rpx;color:#fff;background:rgba(255,59,48,.6)}
	.conn-dot.online{background:rgba(52,199,89,.7)}

	.hero{text-align:center;padding:40rpx 0 36rpx;position:relative;z-index:1}
	.hero-title{display:block;font-size:52rpx;font-weight:bold;color:#fff;letter-spacing:4rpx}
	.hero-sub{display:block;font-size:26rpx;color:rgba(255,255,255,.55);margin-top:10rpx}

	.settings-card{background:rgba(255,255,255,.08);border-radius:16rpx;padding:20rpx 28rpx;margin-bottom:32rpx;position:relative;z-index:1;backdrop-filter:blur(10px)}
	.settings-row{display:flex;align-items:center;gap:12rpx}
	.ip-input{flex:1;font-size:26rpx;padding:14rpx 22rpx;border:2rpx solid rgba(255,255,255,.2);border-radius:10rpx;background:rgba(0,0,0,.2);color:#fff}
	.btn-save{font-size:24rpx;padding:14rpx 28rpx;border-radius:10rpx;background:rgba(255,255,255,.15);color:#ccc;border:none;white-space:nowrap}
	.btn-save.disabled{opacity:.4}
	.btn-connect{font-size:24rpx;padding:14rpx 32rpx;border-radius:10rpx;background:linear-gradient(135deg,#007aff,#0055d4);color:#fff;border:none;white-space:nowrap;font-weight:bold}

	/* 大入口卡片 */
	.main-entry{
		display:flex;align-items:center;gap:24rpx;
		background:linear-gradient(135deg,rgba(0,122,255,.12),rgba(0,122,255,.04));
		border:2rpx solid rgba(0,122,255,.18);
		border-radius:24rpx;padding:36rpx 32rpx;
		position:relative;z-index:1;
		transition:transform .15s, background .15s;
	}
	.main-entry:active{transform:scale(.98);background:linear-gradient(135deg,rgba(0,122,255,.2),rgba(0,122,255,.08))}
	.entry-icon-wrap{width:100rpx;height:100rpx;border-radius:28rpx;background:rgba(0,122,255,.2);display:flex;align-items:center;justify-content:center;flex-shrink:0}
	.entry-icon{font-size:48rpx}
	.entry-info{flex:1}
	.entry-title{display:block;font-size:36rpx;font-weight:bold;color:#fff;margin-bottom:6rpx}
	.entry-desc{display:block;font-size:22rpx;color:rgba(255,255,255,.4)}
	.entry-right{text-align:center;flex-shrink:0}
	.entry-go{font-size:26rpx;color:#007aff;font-weight:bold}
	.entry-lock{font-size:22rpx;color:rgba(255,255,255,.25)}

	/* AI入口卡片 */
	.entry-ai{
		background:linear-gradient(135deg,rgba(138,43,226,.12),rgba(138,43,226,.04));
		border:2rpx solid rgba(138,43,226,.18);
	}
	.entry-ai:active{background:linear-gradient(135deg,rgba(138,43,226,.2),rgba(138,43,226,.08))}
	.icon-ai{background:rgba(138,43,226,.2)}

	/* 语音动作入口卡片 */
	.entry-voice{
		background:linear-gradient(135deg,rgba(220,38,38,.12),rgba(220,38,38,.04));
		border:2rpx solid rgba(220,38,38,.18);
	}
	.entry-voice:active{background:linear-gradient(135deg,rgba(220,38,38,.2),rgba(220,38,38,.08))}
	.icon-voice{background:rgba(220,38,38,.2)}

	/* 视觉识别入口卡片 */
	.entry-vision{
		background:linear-gradient(135deg,rgba(0,191,165,.12),rgba(0,191,165,.04));
		border:2rpx solid rgba(0,191,165,.18);
	}
	.entry-vision:active{background:linear-gradient(135deg,rgba(0,191,165,.2),rgba(0,191,165,.08))}
	.icon-vision{background:rgba(0,191,165,.2)}

	.footer-status{display:flex;justify-content:center;align-items:center;gap:12rpx;padding:20rpx;position:relative;z-index:1}
	.fi{font-size:22rpx;color:rgba(255,255,255,.45)}
	.fd{font-size:20rpx;color:rgba(255,255,255,.18)}
	.hint-bar{text-align:center;padding:20rpx;position:relative;z-index:1}
	.hint-bar text{font-size:22rpx;color:rgba(255,255,255,.22)}
</style>
