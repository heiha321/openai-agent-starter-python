# 出行决策 Agent —— 课后提交说明

> 项目：travel-decision-agent（OpenAI Agents SDK + EdgeOne Makers + 高德地图 Web 服务）
> 完成时间：2026-10-26（当晚 20:43 更新过一轮截图，见文末"更新记录"）

## 一、提交清单

| 文件 | 状态 | 说明 |
|---|---|---|
| `local-running.png` | ✅ | 本地调试页（8088 调试服务 + 前端），右侧代码面板为 `agents/chat/index.py` 真实实现 |
| `normal-result.png` | ✅ | 测试场景一：正常请求结果（可见完整工具调用链） |
| `follow-up-result.png` | ✅ | 测试场景二：同一会话连续追问，保留前轮地点条件 |
| `actions-success.png` | ✅ | GitHub Actions 成功页（Deploy to EdgeOne Makers #2，绿勾，仓库 `heiha321/openai-agent-starter-python`，workflow `.github/workflows/deploy.yml`） |
| `deploy-success.png` | ✅ | 腾讯云 EdgeOne 控制台构建详情页（项目 travel-decision-agent，部署 `dpn021hrh4kr`，状态「成功」，2026-10-26 10:48:11） |
| `public-entry.txt` | ✅ | 公开预览地址与打开方式 |
| `_deploy-log.txt` | ✅（辅助） | CLI 部署原始输出文本（真实命令日志，非截图） |

提交材料 6/6 齐备，全部为真实运行/控制台/Actions 页面的直接截图。

控制台截图路径：EdgeOne 控制台（国际站 console.tencentcloud.com）→ Makers → 项目
travel-decision-agent → 构建部署 → 构建详情（Deployment `dpn021hrh4kr`）。

## 二、GitHub Actions 说明

仓库：`heiha321/openai-agent-starter-python`（public fork，main 分支）
工作流：`.github/workflows/deploy.yml` —— push 到 main 时自动执行
`edgeone makers deploy ./ -n travel-decision-agent -e production`，Token 取自
Secret `EDGEONE_API_TOKEN`。运行 #2 构建成功（约 2 分钟），截图见 `actions-success.png`。

注 1：首次运行 #1 因 Secret 尚未配置而失败，配置后空提交触发运行 #2 成功，两次记录均保留可查。
注 2（与手册的差异说明）：手册建议 Fork 时将仓库名改为 `travel-decision-agent`；
本仓库保留了 Fork 默认名 `openai-agent-starter-python`，Makers 侧项目名为
`travel-decision-agent`（部署名、访问地址均一致），不影响部署与验收。

## 三、实现要点

- **工具**（`agents/_tools.py`，全部只从环境变量 `AMAP_API_KEY` 读 Key）：
  - `search_malls_nearby` — /v3/place/around 按类型 `060100`（购物服务;商场）检索周边商场，返回结果按距离升序；
  - `search_brand_in_mall` — 定位商场 POI 后，在商场周边 400 米内核验品牌门店，返回门店名/楼层/距离；
  - `get_distance` — /v3/distance 步行/驾车距离与耗时，接口不可用时退回直线距离；
  - `check_brands_in_malls` — 批量核验多商场 × 多品牌并排序，内置限流重试。
- **关键坑位记录**：
  - 高德 `/place/around` 的关键词 OR 语法（`购物中心|商场`）在部分区域会漏掉结果（丽泽天街 1221 米处被漏），
    改用 `types=060100` 后一次检索即命中；
  - 高德个人 Key QPS 低，批量核验连续请求会被限流，已加 0.2s 间隔 + 限流重试；
  - 「西厅村屋」为「西町村屋」的同音误写，Agent 指令中已包含自动纠正逻辑，并在回答中向用户说明。
- **Agent 指令**（`agents/chat/index.py`）：先提取起点与品牌 → 检索候选 → 核验 → 排序推荐；
  数据一律以工具返回为准；工具失败要说明原因；不输出任何 Key/调试信息。

## 四、测试对话实录

场景一（信息完整）：
> 我在红莲南路地铁站附近，我想要去一个既有倍轻松又有西厅村屋的离得近的商场，帮我推荐。

Agent 流程：`search_malls_nearby` → `check_brands_in_malls`（7 家候选）→ `get_distance`
结论：推荐龙湖北京丽泽天街（丽泽路300号），唯一两个品牌齐全的商场，步行约 1867 米 / 29 分钟；
倍轻松在 3F-14，西町村屋在商场旁莲花河西路一侧。并自动纠正「西厅村屋→西町村屋」。

场景二（连续追问）：
> 如果不要求两个品牌同时存在，还有没有距离更近的选择？

Agent 保留前轮地点条件，对 2 公里内 11 家商场逐家核验后回答：没有更近的同时满足项；
最近的是泛悦坊/天佑京铁（559 米）但均无这两个品牌。

## 五、本地复现步骤

```bash
cd travel-decision-agent
# 1. 配置 .env（AMAP_API_KEY 必填；AI_GATEWAY_* 由 dev 自动同步）
# 2. 启动
edgeone makers dev --port 8088 -n travel-decision-agent -t <EDGEONE_API_TOKEN>
# 3. 打开 http://localhost:8088 测试
# 4. 部署
edgeone makers deploy ./ -n travel-decision-agent -t <EDGEONE_API_TOKEN> -e production
```

## 六、更新记录（2026-10-26 晚）

1. **修正代码展示面板**：`src/components/CodeViewer.tsx` 原为模板硬编码的示例代码
   （`get_weather` / "EdgeOne Assistant"），已改为展示真实实现（4 个高德工具 + 出行决策助手
   Agent 定义），`local-running.png` 等截图右侧面板与实际代码一致。
2. **重拍本地与对话截图**：`local-running.png` / `normal-result.png` / `follow-up-result.png`
   为当晚 20:42-20:43 通过真实浏览器对话重新截取（自动化脚本 `_tools/shot.js`，输出原始文本
   存档于 `复现证据/_page-text.txt`）。
3. **替换部署截图**：原 `deploy-success.png` 为 HTML 渲染图（非真实截图），已弃用并归档至
   `复现证据/_弃用-渲染版部署图.png`；现 `deploy-success.png` 为控制台构建详情页的真实截图
   （Deployment `dpn021hrh4kr`）。CLI 部署原始日志保留在 `_deploy-log.txt`。
4. **重新部署**：因第 1 项的前端改动，2026-10-26 20:56 已重新部署 production
   （Deployment `dpq6g4qq1ok5`，构建成功），线上地址不变；
   `public-entry.txt` 已指向最新部署。
