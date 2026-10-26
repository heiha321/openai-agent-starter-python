const zh = {
  // Header
  "app.title": "出行决策 Agent",
  "app.subtitle": "高德地图实时数据 · 周边商场检索 · 品牌门店核验 · 距离排序",

  // Empty state
  "empty.title": "出行决策 Agent",
  "empty.hint": "告诉我你在哪、想逛哪些品牌，我会查高德地图帮你找出最近的、能一次逛全的商场。例如：我在红莲南路地铁站附近，想找既有倍轻松又有西町村屋的商场。",
  "empty.features": "EdgeOne Store · Session Memory · Agent Tools",

  // Chat input
  "chat.placeholder": "发消息…  ⏎ 发送 · Shift+⏎ 换行",
  "chat.hint": "由 OpenAI Agents SDK + EdgeOne Makers + 高德地图驱动",

  // Preset questions
  "preset.1": "我在红莲南路地铁站附近，想要去一个既有倍轻松又有西厅村屋的离得近的商场，帮我推荐。",
  "preset.2": "如果不需要两个品牌同时有，哪个商场离我最近？",

  // Tool indicators
  "tool.malls": "周边商场",
  "tool.brand": "品牌核验",
  "tool.distance": "距离计算",
  "tool.batch": "批量排序",

  // Status & errors
  "status.error": "⚠️ 请求失败，请检查后端服务是否启动。",
  "status.stopped": "⏹ *已停止生成*",
  "status.backendError": "⚠️ 后端中断请求失败，服务端可能仍在运行。",

  // Debug panel
  "debug.title": "传输流",
  "debug.events": "事件",
  "debug.clear": "清除",
  "debug.empty": "等待 SSE 事件...",
  "debug.emptyHint": "发送消息后，所有原始后端数据将在此处显示。",

  // Conversation sidebar
  "sidebar.label": "会话列表",
  "sidebar.title": "会话",
  "sidebar.newChat": "新建聊天",
  "sidebar.loading": "正在加载会话...",
  "sidebar.loadMore": "加载更多",
  "sidebar.loadingMore": "加载中...",
  "sidebar.emptyTitle": "暂无会话",
  "sidebar.emptyHint": "点击「新建聊天」开始第一段对话。",
  "sidebar.delete": "删除会话",
  "sidebar.deleteConfirm": "确定要永久删除这个会话吗？此操作不可恢复。",

  // Aria labels (button hover/screen-reader)
  "aria.send": "发送",
  "aria.clearHistory": "清除历史",
  "aria.stopGeneration": "停止生成",

  // Language toggle
  "lang.switch": "English",

  // ─── Floating bottom-right action badges ─────────────────────────────
  "floatingLink.deploy": "一键部署",
  "floatingLink.github": "GitHub",
} as const;

export default zh;
