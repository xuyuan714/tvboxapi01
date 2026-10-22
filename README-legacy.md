# 原 README（2025-11-08 版本，备份）

> 本文件由 2026-10-22 的整理过程自动备份，内容为仓库原有说明。

---

部署到cloudflare关键说明：
路径配置：ROUTE_CONFIG 中的键直接使用 /yl、/tv 等无后缀路径，对应实际的数据源 URL。
访问方式：部署后，直接通过 https://你的域名/yl 或 https://你的域名/tv 访问，无需添加任何后缀。
类型标识：响应头中强制设置 Content-Type: application/json，确保客户端（如浏览器、TVBox 等）能正确识别返回的数据是 JSON 格式，即使路径没有 .json 后缀。
扩展性：如需添加更多路径（如 /sports、/anime），直接在 ROUTE_CONFIG 中添加键值对即可。
部署后测试示例：
访问 https://你的域名/yl → 返回 ylkjhbty.json 的数据
访问 https://你的域名/tv → 返回 tv.json 的数据
访问未配置的路径（如 https://你的域名/test）→ 返回 404 错误提示
这种方式更符合 “简洁路径” 的需求，适合直接在应用中配置接口地址使用
