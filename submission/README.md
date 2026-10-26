# 出行决策 Agent —— 课后提交说明

> 项目：travel-decision-agent（OpenAI Agents SDK + EdgeOne Makers + 高德地图 Web 服务）
> 完成时间：2026-10-26

## 一、提交清单

| 文件 | 状态 | 说明 |
|---|---|---|
| `local-running.png` | ✅ | 本地 8088 调试页（edgeone makers dev） |
| `normal-result.png` | ✅ | 测试场景一：正常请求结果（可见完整工具调用链） |
| `follow-up-result.png` | ✅ | 测试场景二：同一会话连续追问，保留前轮地点条件 |
| `deploy-success.png` | ✅ | CLI 部署成功输出（`_deploy-log.txt` 为原始记录） |
| `deploy-success-console.png` | ✅ | 腾讯云 EdgeOne 控制台构建详情页（项目 travel-decision-agent，部署 `dpn021hrh4kr`，状态「成功」，2026-10-26 10:48:11） |
| `public-entry.txt` | ✅ | 公开预览地址与打开方式 |
| `actions-success.png` | ❌ | 未能提供，原因见下 |

控制台截图路径：EdgeOne 控制台（国际站 console.tencentcloud.com）→ Makers → 项目
travel-decision-agent → 构建部署 → 构建详情（Deployment `dpn021hrh4kr`）。

## 二、actions-success.png 缺失原因

本机课程流程走的是 `edgeone makers deploy` CLI 直传部署，没有绑定 GitHub 仓库，
因此不存在 GitHub Actions 触发记录。本次曾尝试补做，受阻于环境：

- 本机网络访问 `github.com` 直连超时（`ERR_CONNECTION_TIMED_OUT`），校园网封锁 GitHub；
- 电脑无任何代理/VPN 软件，手机热点亦无法连接，故当日无法创建仓库与触发 Actions。

**部署真实性与成功状态由以下三重证据佐证**：`deploy-success.png`（CLI 输出）、
`deploy-success-console.png`（腾讯云 EdgeOne 控制台构建详情页，部署 `dpn021hrh4kr` 状态「成功」）、
`_deploy-log.txt`（原始部署日志）。

如后续网络可用，补做步骤（工作流文件已备好 `.github/workflows/deploy.yml`）：

1. 注册/登录 GitHub，新建空仓库 `travel-decision-agent`（不勾任何初始化选项）；
2. 推送本目录代码（`.env`、`.venv`、`node_modules` 均已在 .gitignore 排除）；
3. 仓库 Settings → Secrets and variables → Actions → 新建 `EDGEONE_API_TOKEN`（值为 Makers 控制台生成的 API Token）；
4. Push 自动触发 workflow（或手动 Run workflow），构建出现绿勾后截 Actions 页面。

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
