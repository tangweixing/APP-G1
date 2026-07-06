<template>
	<view class="kb-page">
		<!-- 顶部栏 -->
		<view class="top-bar">
			<button class="btn-back" @click="goBack">&#x25C0; 返回</button>
			<text class="page-title">知识库管理</text>
			<button class="btn-add" @click="openCreate">+ 新建</button>
		</view>

		<!-- 知识库列表 -->
		<view class="card" v-for="(kb, idx) in list" :key="idx">
			<view class="card-header" @click="toggleExpand(idx)">
				<view class="kb-info">
					<text class="kb-name">{{ kb.name }}</text>
					<text class="kb-meta">{{ kb.document_count || 0 }} 个文档 · {{ kb.knowledge_base_type || 'user' }}</text>
				</view>
				<text class="expand-icon">{{ expandIdx === idx ? '▼' : '▶' }}</text>
			</view>
			<view class="card-actions" v-if="expandIdx === idx">
				<view class="kb-desc">{{ kb.description || '（无描述）' }}</view>
				<view class="action-row">
					<button class="btn-action btn-rename" @click="openRename(kb)">改名</button>
					<button class="btn-action btn-delete" @click="doDelete(kb)">删除</button>
				</view>
			</view>
		</view>

		<!-- 空状态 -->
		<view class="empty" v-if="list.length === 0 && !loading">
			<text class="empty-text">暂无知识库，点右上角「+ 新建」创建</text>
		</view>

		<!-- 新建/改名 弹窗 -->
		<view class="modal-mask" v-if="modal.show" @click="closeModal">
			<view class="modal" @click.stop>
				<text class="modal-title">{{ modal.mode === 'create' ? '新建知识库' : '改名' }}</text>
				<view class="form-row">
					<text class="label">名称</text>
					<input class="input" v-model="modal.name" placeholder="知识库名称" />
				</view>
				<view class="form-row form-col">
					<text class="label">描述</text>
					<textarea class="textarea" v-model="modal.description" placeholder="描述（可选）" :maxlength="-1" auto-height></textarea>
				</view>
				<view class="modal-actions">
					<button class="btn-cancel" @click="closeModal">取消</button>
					<button class="btn-confirm" @click="doSubmit" :disabled="submitting">{{ submitting ? '提交中...' : '确定' }}</button>
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
			list: [],
			loading: false,
			expandIdx: -1,
			modal: { show: false, mode: 'create', id: null, name: '', description: '' },
			submitting: false,
		}
	},
	onLoad: function() { this.loadList(); },
	onShow: function() { if (this.list.length === 0) this.loadList(); },
	methods: {
		goBack: function() {
			var pages = getCurrentPages();
			if (pages.length > 1) { uni.navigateBack(); }
			else { uni.reLaunch({ url: '/pages/index/index' }); }
		},

		loadList: function() {
			var self = this;
			this.loading = true;
			g1Api.kbList(1, 50).then(function(r) {
				self.loading = false;
				if (r.success && r.data) {
					self.list = r.data.list || [];
				} else {
					uni.showToast({ title: r.message || '加载失败', icon: 'none' });
				}
			}).catch(function() {
				self.loading = false;
				uni.showToast({ title: '网络错误', icon: 'none' });
			});
		},

		toggleExpand: function(idx) {
			this.expandIdx = this.expandIdx === idx ? -1 : idx;
		},

		openCreate: function() {
			this.modal = { show: true, mode: 'create', id: null, name: '', description: '' };
		},

		openRename: function(kb) {
			this.modal = { show: true, mode: 'rename', id: kb.id, name: kb.name, description: kb.description || '' };
		},

		closeModal: function() {
			this.modal.show = false;
		},

		doSubmit: function() {
			var self = this;
			if (!this.modal.name) {
				uni.showToast({ title: '请填名称', icon: 'none' });
				return;
			}
			this.submitting = true;
			var p;
			if (this.modal.mode === 'create') {
				p = g1Api.kbCreate(this.modal.name, this.modal.description);
			} else {
				p = g1Api.kbUpdate(this.modal.id, this.modal.name, this.modal.description);
			}
			p.then(function(r) {
				self.submitting = false;
				if (r.success) {
					uni.showToast({ title: self.modal.mode === 'create' ? '已创建' : '已更新', icon: 'success' });
					self.closeModal();
					self.loadList();
				} else {
					uni.showToast({ title: r.message || '操作失败', icon: 'none' });
				}
			}).catch(function() {
				self.submitting = false;
				uni.showToast({ title: '网络错误', icon: 'none' });
			});
		},

		doDelete: function(kb) {
			var self = this;
			uni.showModal({
				title: '确认删除',
				content: '删除知识库「' + kb.name + '」？此操作不可恢复。',
				confirmColor: '#d32f2f',
				success: function(res) {
					if (!res.confirm) return;
					g1Api.kbDelete(kb.id).then(function(r) {
						if (r.success) {
							uni.showToast({ title: '已删除', icon: 'success' });
							self.loadList();
						} else {
							uni.showToast({ title: r.message || '删除失败', icon: 'none' });
						}
					}).catch(function() {
						uni.showToast({ title: '网络错误', icon: 'none' });
					});
				}
			});
		},
	}
});
</script>

<style scoped>
.kb-page{min-height:100vh;background:#1a1a2e;color:#eee;display:flex;flex-direction:column;padding:12px;box-sizing:border-box}

.top-bar{display:flex;align-items:center;justify-content:space-between;height:44px;margin-bottom:16px;padding:0 8px}
.page-title{font-size:17px;font-weight:700;color:#fff;position:absolute;left:50%;transform:translateX(-50%)}
.btn-back{position:fixed;top:20px;left:20px;z-index:10;background:#333;color:#fff;border:none;border-radius:8px;font-size:14px;padding:6px 14px;line-height:1}
.btn-add{position:fixed;top:20px;right:20px;z-index:10;background:#1a7f37;color:#fff;border:none;border-radius:8px;font-size:14px;padding:6px 14px;line-height:1}

.card{background:#222;border-radius:12px;margin-bottom:12px;overflow:hidden;border:1px solid #333}
.card-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px}
.kb-info{display:flex;flex-direction:column}
.kb-name{font-size:15px;font-weight:600;color:#fff}
.kb-meta{font-size:11px;color:#888;margin-top:4px}
.expand-icon{color:#888;font-size:12px}
.card-actions{padding:0 16px 14px;border-top:1px solid #2a2a3e;padding-top:12px}
.kb-desc{font-size:12px;color:#aaa;margin-bottom:10px;word-break:break-all}
.action-row{display:flex;gap:8px}
.btn-action{flex:1;border:none;border-radius:8px;font-size:13px;padding:8px 0}
.btn-rename{background:#2a4a7a;color:#fff}
.btn-delete{background:#5a1a1a;color:#ff6b6b}

.empty{display:flex;justify-content:center;align-items:center;padding:80px 20px}
.empty-text{color:#666;font-size:13px;text-align:center}

/* 弹窗 */
.modal-mask{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:100;display:flex;align-items:center;justify-content:center;padding:20px}
.modal{background:#222;border-radius:12px;padding:20px;width:100%;max-width:400px;border:1px solid #444}
.modal-title{font-size:16px;font-weight:600;color:#fff;display:block;margin-bottom:16px}
.form-row{display:flex;align-items:center;margin-bottom:14px;min-height:40px}
.form-row.form-col{flex-direction:column;align-items:stretch}
.label{width:70px;flex-shrink:0;font-size:13px;color:#9af}
.input{flex:1;background:#1a1a2e;border:1px solid #444;border-radius:8px;padding:10px 12px;color:#eee;font-size:14px;height:40px;box-sizing:border-box}
.textarea{background:#1a1a2e;border:1px solid #444;border-radius:8px;padding:10px 12px;color:#eee;font-size:13px;min-height:80px;width:100%;box-sizing:border-box;margin-top:6px}
.modal-actions{display:flex;gap:10px;margin-top:8px}
.modal-actions button{flex:1;border:none;border-radius:8px;font-size:14px;padding:10px 0}
.btn-cancel{background:#444;color:#eee}
.btn-confirm{background:linear-gradient(135deg,#1a7f37,#28a745);color:#fff}
.btn-confirm[disabled]{opacity:.5}
</style>
