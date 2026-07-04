<template>
	<view class="motion-page">
		<!-- 顶部栏 -->
		<view class="top-bar">
			<button class="btn-back" @click="goBack">&#x25C0; 返回</button>
			<text class="page-title">G1 运动控制</text>
			<view class="status-mini" :class="{ online: locoActive }">
				{{ locoActive ? '运动中' : '待机' }}
			</view>
		</view>

		<!-- ====== 第一行：速度 + 档位 + 急停 + 启停 ====== -->
		<view class="row-top">
			<view class="speed-bar">
				<view class="speed-item"><text class="sl">Vx</text><text class="sv">{{ vx.toFixed(3) }}</text></view>
				<view class="speed-item"><text class="sl">Vy</text><text class="sv">{{ vy.toFixed(3) }}</text></view>
				<view class="speed-item"><text class="sl">Wz</text><text class="sv">{{ wz.toFixed(3) }}</text></view>
				<view class="speed-item"><text class="sl">档位</text><text class="sv gv">{{ currentGear }}</text></view>
				<view class="gear-row">
					<button v-for="g in [1,2,3]" :key="g"
						class="gb" :class="{ ga: currentGear===g }" @click="setGear(g)">{{ g }}档</button>
				</view>
			</view>
		</view>

		<!-- ====== 双摇杆区域 ====== -->
		<view class="joystick-area">
			<view class="jc">
				<text class="jl">XY 移动 (前后左右)</text>
				<view class="jpw">
					<view class="jch"></view>
					<view class="jp" id="xyPad"
							@touchstart.stop.prevent="startJoy('xy', $event)"
							@touchmove.stop.prevent="moveJoy('xy', $event)"
							@touchend.stop.prevent="endJoy('xy')"
							@touchcancel.stop.prevent="endJoy('xy')"
							@mousedown.stop.prevent="startJoy('xy', $event)"
							@mousemove.stop.prevent="moveJoy('xy', $event)"
							@mouseup.stop.prevent="endJoy('xy')"
							@mouseleave.stop.prevent="endJoy('xy')">
						<view class="jk jkb" id="xyKnob" :style="xyKnobStyle"></view>
					</view>
				</view>
			</view>
			<view class="jc">
				<text class="jl">Z 旋转 (左右转向)</text>
				<view class="jpw">
					<view class="jch"></view>
					<view class="jp" id="zPad"
							@touchstart.stop.prevent="startJoy('z', $event)"
							@touchmove.stop.prevent="moveJoy('z', $event)"
							@touchend.stop.prevent="endJoy('z')"
							@touchcancel.stop.prevent="endJoy('z')"
							@mousedown.stop.prevent="startJoy('z', $event)"
							@mousemove.stop.prevent="moveJoy('z', $event)"
							@mouseup.stop.prevent="endJoy('z')"
							@mouseleave.stop.prevent="endJoy('z')">
						<view class="jk jko" id="zKnob" :style="zKnobStyle"></view>
					</view>
				</view>
			</view>
		</view>

		<!-- ====== 扩展栏：手部动作 ====== -->
		<view class="expand-card">
			<view class="eh" @click="showActions = !showActions">
				<text class="et">&#x1F44B; 手部动作</text>
				<text class="ea">{{ showActions ? '&#x25BC;' : '&#x25B6;' }}</text>
			</view>
			<view v-show="showActions" class="eb">
				<view class="ag">
					<button v-for="a in actions" :key="a.id" class="ab" @click.stop="doAction(a.id)">{{ a.name }}</button>
				</view>
			</view>
		</view>

		<!-- ====== 扩展栏：模式切换 ====== -->
		<view class="expand-card">
			<view class="eh" @click="showFsm = !showFsm">
				<text class="et">&#x2699; 模式切换 (FSM)</text>
				<text class="ea">{{ showFsm ? '&#x25BC;' : '&#x25B6;' }}</text>
			</view>
			<view v-show="showFsm" class="eb">
				<view class="fg">
					<button v-for="(m,id) in fsmModes" :key="id" class="fb" @click.stop="doSetFsm(Number(id))">{{ m.desc }}</button>
				</view>
			</view>
		</view>

		<!-- ====== 扩展栏：舞蹈动作 ====== -->
		<view class="expand-card">
			<view class="eh" @click="showDance = !showDance">
				<text class="et">&#x1F483; 舞蹈动作</text>
				<text class="ea">{{ showDance ? '&#x25BC;' : '&#x25B6;' }}</text>
			</view>
			<view v-show="showDance" class="eb">
				<view class="dance-hint">先在上方"模式切换"点击"舞蹈模式"进入舞蹈，再点下列动作</view>
				<view class="dg">
					<button v-for="(d,i) in danceActions" :key="'d'+i" class="db" @click.stop="doDanceAction(d)">{{ d.name }}</button>
				</view>
				<view class="dg dance-emg">
					<button class="db db-emg" @click.stop="doDanceAction(danceEmergency, true)">{{ danceEmergency.name }}</button>
				</view>
			</view>
		</view>

		<view class="hint-bar"><text>拖动摇杆控制机器人 · 松开自动回中 · 点击标题展开/收起面板</text></view>
	</view>
</template>

<script>
	import Vue from 'vue';
	import * as g1Api from '../../api/g1';
	import { connectVrSocket, disconnectVrSocket, vrPressCombo, vrPressDblClick } from '../../api/vrSocket';

	// 档位速度（与web_arm_control一致）
	var GEAR_SPEEDS = {
		1: { vx: 0.3, vy: 0.2, wz: 0.4 },
		2: { vx: 0.6, vy: 0.3, wz: 0.8 },
		3: { vx: 1.0, vy: 0.5, wz: 1.2 }
	};
	var MAX_DIST = 60; // 摇杆最大偏移像素（与参考实现一致）

	export default Vue.extend({
		data: function() {
			return {
				vx: 0,
				vy: 0,
				wz: 0,
				currentGear: 1,
				locoActive: false,
				pollTimer: null,
				showActions: false,
				showFsm: false,
				showDance: false,
				// 摇杆归一化坐标 (-1 ~ 1)，与web_arm_control一致
				xyState: { active: false, x: 0, y: 0 },
				zState: { active: false, x: 0, y: 0 },
					joyRects: {},
					joyRectReady: {},
				fsmModes: {
					'0': { name: 'ZeroTorque', desc: '零力矩', group: '基础' },
					'1': { name: 'Damp', desc: '阻尼模式', group: '基础' },
					'3': { name: 'Sit', desc: '坐下', group: '姿态' },
					'4': { name: 'Ready', desc: '预备模式', group: '姿态' },
					'200': { name: 'Start', desc: '启动运动', group: '运动' },
					'501': { name: 'Walk', desc: '常规走路', group: '运动' },
					'702': { name: 'Lie2StandUp', desc: '躺→站', group: '姿态' },
					'706': { name: 'Squat2Stand', desc: '蹲↔站', group: '姿态' },
					'802': { name: 'Run', desc: '走跑模式', group: '运动' },
					'503': { name: 'Dance', desc: '舞蹈模式', group: '运动' },
				},
				actions: [
					{ id: 0, name: '释放' }, { id: 1, name: '握手' }, { id: 2, name: '击掌' },
					{ id: 3, name: '拥抱' }, { id: 4, name: '挥手' }, { id: 5, name: '鼓掌' },
					{ id: 6, name: '面部挥手' }, { id: 7, name: '左吻' }, { id: 8, name: '比心' },
					{ id: 9, name: '右比心' }, { id: 10, name: '举手' }, { id: 11, name: 'X光' },
					{ id: 12, name: '右举手' }, { id: 13, name: '拒绝' }, { id: 14, name: '右吻' },
					{ id: 15, name: '双手吻' },
				],
				danceActions: [
					{ name: '功夫', combo: ['R1','Select'] },
					{ name: '舞蹈1', combo: ['R1','Up'] },
					{ name: '舞蹈2', combo: ['R1','Left'] },
					{ name: '舞蹈3', combo: ['R1','Right'] },
					{ name: '机械舞3', combo: ['R1','Down'] },
					{ name: '截拳道', combo: ['R2','Up'] },
					{ name: '扭扭舞', combo: ['R2','Left'] },
					{ name: '机械舞1', combo: ['L1','X'] },
					{ name: '机械舞4', combo: ['L1','Y'] },
					{ name: '芭蕾', combo: ['L1','A'] },
				],
				danceEmergency: { name: '舞蹈紧急中断', combo: ['Start'] },
			}
		},
		onLoad: function() { g1Api.loadSavedAddress(); this.fetchStatus() },
		onShow: function() {
			if (!this.pollTimer) {
				var self = this;
				this.pollTimer = setInterval(function() { self.fetchStatus() }, 500)
			}
		},
		onHide: function() {
			if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null }
			if (this._vrReady) { disconnectVrSocket(false); this._vrReady = false }
		},
		onUnload: function() {
			if (this.pollTimer) clearInterval(this.pollTimer);
			if (this._velocitySendTimer) { clearInterval(this._velocitySendTimer); this._velocitySendTimer = null; }
			disconnectVrSocket(false);
			this._vrReady = false;
			this.sendV(0, 0, 0)
		},

		computed: {
			// knob显示用的像素偏移
			xyKnobPx: function() { return this.xyState.x * MAX_DIST; },
			xyKnobPy: function() { return this.xyState.y * MAX_DIST; },
			zKnobPx: function() { return this.zState.x * MAX_DIST; },
			zKnobPy: function() { return this.zState.y * MAX_DIST; },
			xyKnobStyle: function() {
				return 'transform: translate(calc(-50% + ' + this.xyKnobPx + 'px), calc(-50% + ' + this.xyKnobPy + 'px))';
			},
			zKnobStyle: function() {
				return 'transform: translate(calc(-50% + ' + this.zKnobPx + 'px), calc(-50% + ' + this.zKnobPy + 'px))';
			}
		},

		methods: {
			goBack: function() {
				var pages = getCurrentPages();
				if (pages.length > 1) {
					uni.navigateBack();
				} else {
					uni.reLaunch({ url: '/pages/index/index' });
				}
			},

			fetchStatus: function() {
				var self = this;
				g1Api.getStatus().then(function(r) {
					if (r.current_velocity) {
						var idle = self.xyState.x === 0 && self.xyState.y === 0 && self.zState.x === 0;
						if (idle) {
							self.vx = r.current_velocity.vx || 0;
							self.vy = r.current_velocity.vy || 0;
							self.wz = r.current_velocity.wz || 0;
						}
					}
					self.currentGear = r.current_gear || 1;
				}).catch(function() {})
			},

			setGear: function(g) {
				var self = this;
				g1Api.setGear(g).then(function(r) {
					if (r.success) self.currentGear = g;
					uni.showToast({ title: r.message || '', icon: r.success ? 'success' : 'none' })
				}).catch(function() { uni.showToast({ title: '设置失败', icon: 'none' }) })
			},

			doEstop: function() {
				var self = this;
				g1Api.emergencyStop().then(function(r) {
					uni.showToast({ title: r.message || '急停', icon: r.success ? 'success' : 'none' });
					self.resetJoy()
				}).catch(function() { uni.showToast({ title: '急停失败', icon: 'none' }) })
			},

			toggleLoco: function() {
				var self = this;
				g1Api.toggleLoco().then(function(r) {
					if (r.success) self.locoActive = !self.locoActive;
					uni.showToast({ title: r.message || '', icon: 'success' })
				}).catch(function() { uni.showToast({ title: '操作失败', icon: 'none' }) })
			},

			// ========== 摇杆事件（App端使用模板事件，避免直接操作document）==========
			getEventPoint: function(e) {
				var touch = null;
				if (e && e.touches && e.touches.length > 0) touch = e.touches[0];
				else if (e && e.changedTouches && e.changedTouches.length > 0) touch = e.changedTouches[0];
				if (touch) {
					return {
						x: touch.clientX !== undefined ? touch.clientX : (touch.pageX !== undefined ? touch.pageX : (touch.x || 0)),
						y: touch.clientY !== undefined ? touch.clientY : (touch.pageY !== undefined ? touch.pageY : (touch.y || 0))
					};
				}
				return {
					x: e && e.clientX !== undefined ? e.clientX : 0,
					y: e && e.clientY !== undefined ? e.clientY : 0
				};
			},

			getJoyState: function(type) {
				return type === 'z' ? this.zState : this.xyState;
			},

			getPadRect: function(type, callback) {
				var selector = type === 'z' ? '#zPad' : '#xyPad';
				uni.createSelectorQuery().in(this).select(selector).boundingClientRect(function(rect) {
					callback(rect);
				}).exec();
			},

			clampJoy: function(x, y) {
				var dist = Math.sqrt(x * x + y * y);
				if (dist > MAX_DIST) {
					var scale = MAX_DIST / dist;
					return { x: x * scale, y: y * scale };
				}
				return { x: x, y: y };
			},

			startVelocityLoop: function() {
				var self = this;
				if (this._velocitySendTimer) return;
				this._velocitySendTimer = setInterval(function() {
					if (self.xyState.active || self.zState.active) {
						self.sendVelocityFromJoysticks();
					}
				}, 100);
			},

			stopVelocityLoopIfIdle: function() {
				if (this.xyState.active || this.zState.active) return;
				if (this._velocitySendTimer) {
					clearInterval(this._velocitySendTimer);
					this._velocitySendTimer = null;
				}
			},

			startJoy: function(type, e) {
				if (e && e.preventDefault) e.preventDefault();
				var self = this;
				var point = this.getEventPoint(e);
				var state = this.getJoyState(type);
				state.active = true;
				this.startVelocityLoop();
				this.getPadRect(type, function(rect) {
					if (!rect) return;
					self.$set(self.joyRects, type, rect);
					self.$set(self.joyRectReady, type, true);
					self.updateJoyByPoint(type, point);
				});
			},

			moveJoy: function(type, e) {
				var state = this.getJoyState(type);
				if (!state.active) return;
				if (e && e.preventDefault) e.preventDefault();
				this.updateJoyByPoint(type, this.getEventPoint(e));
			},

			updateJoyByPoint: function(type, point) {
				var state = this.getJoyState(type);
				var rect = this.joyRects[type];
				if (!state.active || !rect) return;
				var cx = rect.left + rect.width / 2;
				var cy = rect.top + rect.height / 2;
				var clamped = this.clampJoy(point.x - cx, point.y - cy);
				state.x = clamped.x / MAX_DIST;
				state.y = clamped.y / MAX_DIST;
				this.sendVelocityFromJoysticks();
			},

			endJoy: function(type) {
				var state = this.getJoyState(type);
				if (!state.active && state.x === 0 && state.y === 0) return;
				state.active = false;
				state.x = 0;
				state.y = 0;
				this.stopVelocityLoopIfIdle();
				this.sendVelocityFromJoysticks();
			},

			// ========== 发送速度（方向映射完全对齐web_arm_control）==========
			sendVelocityFromJoysticks: function() {
				var gear = GEAR_SPEEDS[this.currentGear] || GEAR_SPEEDS[1];
				// 与web_arm_control完全一致的映射：vx=-y, vy=-x, wz=-x
				var vx = -this.xyState.y * gear.vx;
				var vy = -this.xyState.x * gear.vy;
				var wz = -this.zState.x * gear.wz;
				this.vx = vx;
				this.vy = vy;
				this.wz = wz;
				this.sendV(vx, vy, wz);
			},

			resetJoy: function() {
				if (this._velocitySendTimer) { clearInterval(this._velocitySendTimer); this._velocitySendTimer = null; }
				this.xyState = { active: false, x: 0, y: 0 };
				this.zState = { active: false, x: 0, y: 0 };
				this.sendV(0, 0, 0);
			},

			sendV: function(vx, vy, wz) {
				g1Api.setVelocity(vx, vy, wz).catch(function() {});
			},

			doAction: function(id) {
				g1Api.armAction(id).then(function(r) {
					uni.showToast({ title: r.message || '完成', icon: r.success ? 'success' : 'none' })
				}).catch(function() { uni.showToast({ title: '执行失败', icon: 'none' }) })
			},

			doSetFsm: function(id) {
				g1Api.setFsm(id).then(function(r) {
					uni.showToast({ title: r.message || '', icon: r.success ? 'success' : 'none' })
				}).catch(function() { uni.showToast({ title: '切换失败', icon: 'none' }) })
			},

			ensureVrSocket: function() {
				if (this._vrReady) return Promise.resolve();
				var self = this;
				uni.showLoading({ title: '连接舞蹈控制器...', mask: true });
				return connectVrSocket().then(function() {
					self._vrReady = true;
					uni.hideLoading();
				}).catch(function(err) {
					uni.hideLoading();
					uni.showToast({ title: '舞蹈控制器连接失败', icon: 'none' });
					throw err;
				});
			},

			doDanceAction: function(action, isDblClick) {
				var self = this;
				// 防抖：上一次动作仍在发送（含保持/释放时序）时忽略连点，避免按键叠加。
				if (this._danceBusy) {
					uni.showToast({ title: '请稍候...', icon: 'none' });
					return;
				}
				this._danceBusy = true;
				this.ensureVrSocket().then(function() {
					var p = isDblClick ? vrPressDblClick(action.combo) : vrPressCombo(action.combo);
					uni.showToast({ title: action.name, icon: 'none' });
					return p;
				}).catch(function() {}).then(function() {
					// 组合键 down(逐键30ms)→保持300ms→up；留余量再解锁，防止两次动作按键重叠。
					setTimeout(function() { self._danceBusy = false; }, 500);
				});
			},
		}
	});
</script>

<style>
	.motion-page{min-height:100vh;background:linear-gradient(135deg,#0d1117,#161b22 50%,#1c2128);padding:16rpx 28rpx;color:#fff;box-sizing:border-box}

	/* 顶部 */
	.top-bar{display:flex;align-items:center;gap:14rpx;margin-bottom:12rpx}
	.btn-back{font-size:22rpx;padding:8rpx 20rpx;background:rgba(255,255,255,.08);color:#ccc;border-radius:8rpx;border:none}
	.page-title{font-size:32rpx;font-weight:bold;flex:1;text-align:center}
	.status-mini{font-size:20rpx;padding:6rpx 16rpx;border-radius:14rpx;background:rgba(255,59,48,.5);color:#ffcccb}
	.status-mini.online{background:rgba(52,199,89,.5);color:#c6f6d5}

	/* 速度条 */
	.row-top{margin-bottom:12rpx}
	.speed-bar{display:flex;align-items:center;gap:10rpx;background:rgba(255,255,255,.06);border-radius:12rpx;padding:12rpx 18rpx}
	.speed-item{display:flex;flex-direction:column;align-items:center;min-width:80rpx}
	.sl{font-size:17rpx;color:rgba(255,255,255,.35)}
	.sv{font-size:24rpx;font-weight:bold;color:#007aff;font-family:monospace}
	.gv{color:#ff9500}
	.gear-row{margin-left:auto;display:flex;gap:6rpx}
	.gb{font-size:20rpx!important;padding:7rpx 18rpx!important;border-radius:8rpx!important;background:rgba(255,255,255,.08);color:#999;border:none}
	.gb.ga{background:#007aff;color:#fff}

	/* 按钮 */
	.row-btns{display:flex;gap:14rpx;margin-bottom:24rpx}
	.be{flex:1;padding:22rpx;font-size:30rpx;font-weight:bold;border-radius:12rpx;background:linear-gradient(135deg,#ff3b30,#d70015);color:#fff;border:none;letter-spacing:6rpx}
	.bl{flex:1;padding:22rpx;font-size:24rpx;font-weight:bold;border-radius:12rpx;background:rgba(255,255,255,.06);color:#aaa;border:2rpx solid rgba(255,255,255,.08)}
	.bl.on{background:rgba(52,199,89,.12);color:#4cd964;border-color:rgba(52,199,89,.25)}

	/* 双摇杆 */
	.joystick-area{display:flex;justify-content:space-between;gap:0;padding:16rpx 40rpx;margin-bottom:20rpx;box-sizing:border-box;width:100%}
	.jc{display:flex;flex-direction:column;align-items:center}
	.jl{font-size:22rpx;color:rgba(255,255,255,.45);margin-bottom:12rpx;font-weight:500}
	.jpw{position:relative}
	.jch{position:absolute;top:50%;left:50%;width:36px;height:36px;transform:translate(-50%,-50%)}
	.jch::before,.jch::after{content:'';position:absolute;background:rgba(255,255,255,.1)}
	.jch::before{width:1px;height:100%;left:50%;transform:translateX(-50%)}
	.jch::after{width:100%;height:1px;top:50%;transform:translateY(-50%)}
	.jp{width:200px;height:200px;border-radius:100px;background:radial-gradient(circle,rgba(255,255,255,.05),rgba(255,255,255,.02) 70%);border:2px solid rgba(255,255,255,.09);position:relative;touch-action:none;user-select:none;-webkit-user-select:none}
	.jk{width:60px;height:60px;border-radius:30px;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);will-change:transform}
	.jkb{background:radial-gradient(circle at 35% 35%,#4da6ff,#007aff 60%,#0055b3);box-shadow:0 4px 16px rgba(0,122,255,.4),inset 0 -2px 6px rgba(0,0,0,.2)}
	.jko{background:radial-gradient(circle at 35% 35%,#ffb340,#ff9500 60%,#cc7700);box-shadow:0 4px 16px rgba(255,149,0,.4),inset 0 -2px 6px rgba(0,0,0,.2)}

	/* 扩展栏 */
	.expand-card{background:rgba(255,255,255,.04);border-radius:14rpx;margin-bottom:14rpx;overflow:hidden;border:1px solid rgba(255,255,255,.05)}
	.eh{display:flex;justify-content:space-between;align-items:center;padding:20rpx 24rpx}
	.et{font-size:26rpx;font-weight:bold;color:rgba(255,255,255,.85)}
	.ea{font-size:22rpx;color:rgba(255,255,255,.3)}
	.eb{padding:0 24rpx 20rpx;border-top:1px solid rgba(255,255,255,.04)}
	.ag{display:flex;flex-wrap:wrap;gap:10rpx;padding-top:16rpx}
	.ab{font-size:22rpx;padding:10rpx 20rpx;background:rgba(175,82,222,.15);color:#ddd;border-radius:8rpx;border:none}
	.fg{display:flex;flex-wrap:wrap;gap:10rpx;padding-top:16rpx}
	.fb{font-size:22rpx;padding:10rpx 20rpx;background:rgba(52,199,89,.12);color:#ddd;border-radius:8rpx;border:none}
	.dance-hint{font-size:20rpx;color:rgba(255,255,255,.45);padding:12rpx 4rpx 4rpx;line-height:1.4}
	.dg{display:flex;flex-wrap:wrap;gap:10rpx;padding-top:10rpx}
	.db{font-size:22rpx;padding:10rpx 20rpx;background:rgba(255,69,147,.15);color:#ddd;border-radius:8rpx;border:none}
	.dance-emg{padding-top:14rpx}
	.db-emg{background:rgba(255,59,48,.18);color:#ffd2cf}

	.hint-bar{text-align:center;padding:16rpx}
	.hint-bar text{font-size:20rpx;color:rgba(255,255,255,.2)}
</style>
