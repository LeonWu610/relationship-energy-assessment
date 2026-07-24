# 当前状态

## 当前工作单元

把内容验证版升级为可售卖的网页产品。页面视觉、兑换码架构、内部模拟结果隔离和 Cloudflare 部署骨架已完成；下一步是用户验收视觉，并在用户准备好 Cloudflare 账号与域名后执行真实部署。

## 当前状态

- `quiz.html` 已完成移动端优先的视觉重设计：暖调纸张质感、原创内联 SVG 主视觉、宋体标题、玻璃卡片与更清晰的信息层级；首页 3 个 emoji 已全部移除，不需要图片生成 API 或 S3。
- 新增商品解锁屏。生产环境使用每单唯一随机兑换码；每枚码默认最多绑定 2 台设备，使用 HttpOnly 会话 Cookie，不把兑换码或长期 token 放进 URL。
- 新增 `worker.js`：提供兑换码核销、会话恢复、受保护题库接口、内部预览会话和管理员批量生成兑换码接口。
- 新增 `schema.sql` 和 `wrangler.toml`：目标架构为 Cloudflare Worker + 静态 Assets + D1；静态发布目录 `public/` 只包含 `index.html`、`quiz.html`，题库 JSON、测试脚本和项目文档不会作为公开静态文件发布。
- 普通买家页面不渲染模拟结果；线上内部预览需使用 `?preview=<PREVIEW_KEY>` 建立受保护会话，随后地址会自动清除 query。该方案比“随便放一个随机 query”更安全，因为密钥由 Worker 验证。
- 本地开发自动跳过兑换码：普通地址不显示模拟结果；仅 `?preview=local-preview` 显示内部预设。
- GitHub Pages 不用于正式售卖。正式建议 Cloudflare + 自定义域名；专业感主要来自域名和产品视觉，而不是代码仓库托管位置。

## 验证证据

- `python3 test_stage_a_scoring.py`：19 项全部通过。
- `python3 _scenario_check.py`：16 组生活画像、6 种展示组合全部通过。
- 编辑文件 lint：无错误。
- Wrangler 4.113.0 干运行打包成功：仅发现并上传 `public/` 中 2 个静态文件，Worker 正确识别 D1 与 Assets 绑定。
- 真实浏览器已在 iPhone 14 尺寸检查首页；普通地址的可访问树不含任何内部模拟结果，`?preview=local-preview` 才显示 12 个预设。
- 首页到答题页的原生点击流程已验证，第一题与全部交互按钮正常显示。

## 阻塞或风险

- 尚未真实部署：`wrangler.toml` 中 D1 `database_id` 仍是占位值，生产 secrets `SESSION_SECRET`、`ADMIN_SECRET`、`PREVIEW_KEY` 尚未设置。
- 设备绑定只能降低普通转发，无法做到数字版权 DRM；买家仍可分享截图或在已绑定设备上给别人使用。对低客单价首版而言，2 台设备限制是安全性与售后成本的折中。
- Cloudflare 在中国大陆没有免费层 SLA；正式售卖前应从目标用户网络做移动、电信、联通实测。若实际影响转化，再迁移至备案后的大陆云。
- Node.js 24 已通过现有 nvm 安装；CatPaw Desk 重启后新 shell 才会默认获取更新后的 PATH。

## 下一步

1. 用户打开 `http://localhost:8765/quiz.html` 验收新版视觉；内部预设地址为 `http://localhost:8765/quiz.html?preview=local-preview`。
2. 视觉通过后，准备一个自定义域名和 Cloudflare 账号，再创建 D1、写入真实 database ID、设置 3 个 secrets 并部署。
3. 部署后通过管理员接口批量生成兑换码；每笔订单人工发送一个码。订单增长后再接支付回调自动发码。
4. 正式上线前用至少三种大陆网络实测首屏、兑换和题库加载。

## Changelog

- 本轮：完成商品化视觉重设计、每单一码/两设备访问控制、内部预设隔离及 Cloudflare 部署骨架。
- 上轮：关系报告恢复上一版主体，只保留用户明确要求的小范围措辞修正。
- 早期：建立关系结论、来源解释和跨题洞察规则。
