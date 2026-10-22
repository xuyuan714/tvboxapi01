# tvboxapi01

自用 TVBox 接口仓库。**一个地址 = 本仓已有配置 + 外部实测可用源**，全部经过状态码、内容解析、规模三重校验。

- 最近更新：2026-10-22
- 全量入口 **76** 条：本仓 17（1 多仓 + 16 单仓）+ 外部多仓 4 + 外部单仓 55
- 精简入口 **14** 条：只看站点数最多的，加载快
- 直播源 **4** 条
- 已剔除失效 **16** 个（返图 / 502 / 404 / 源站 JSON 语法错误）

## 导入地址

| 用途 | 地址 |
|---|---|
| **精简（推荐日常用）** | `https://cdn.jsdelivr.net/gh/xuyuan714/tvboxapi01@main/config-lite.json` |
| 全量（76 条，首载较慢） | `https://cdn.jsdelivr.net/gh/xuyuan714/tvboxapi01@main/config.json` |
| 直播源 | `https://cdn.jsdelivr.net/gh/xuyuan714/tvboxapi01@main/live.json` |
| 全量（ghproxy 备用） | `https://ghproxy.net/https://raw.githubusercontent.com/xuyuan714/tvboxapi01/main/config.json` |
| 全量（GitHub 原生，国内常不通） | `https://raw.githubusercontent.com/xuyuan714/tvboxapi01/main/config.json` |

> `raw.githubusercontent.com` 在国内实测被直接掐断（超时 / RemoteDisconnected），优先用 jsDelivr。
> jsDelivr 对 `@main` 有约 12 小时缓存，刚提交完可能要等一会儿才生效，急用就加 `?t=时间戳` 或换 ghproxy。

## 文件

| 文件 | 说明 |
|---|---|
| `config.json` | 全量多仓入口，76 条。顺序：本仓多仓 → 外部多仓 → 本仓单仓（按站点数）→ 外部单仓（按响应速度） |
| `config-lite.json` | 精选 14 条，日常用这个 |
| `live.json` | 直播源：本仓 4Gtv.m3u、频道表 M3U、咪咕、央视卫视 TXT |
| `tvbox-api-list.txt` | 外部源清单，格式 `名称<TAB>地址`；加新源就往这加一行 |
| `probe.json` | 最近一次探测原始结果（状态码、耗时、类型、站点数） |
| `测试报告.csv` | 同上，Excel 可直接打开 |
| `scripts/probe.py` | 探测 `tvbox-api-list.txt` 全部接口 |
| `scripts/build_pack.py` | 按探测结果重建配置，并自动把本仓根目录的 `*.json/*.js/*.m3u` 收进入口 |
| `README-legacy.md` | 原 README 备份（Cloudflare Worker 路由说明） |
| `4Gtv.m3u` `duocang.json` `lige.json` `merged.json` `tianwei.json` `毒盒.json` `巧记.json` `讴歌.json` `肥猫.js` `ok线路.js` … | 仓库原有配置，已被自动纳入 `config.json` |

## 关于原有的 Cloudflare Worker

仓库里的 `__works.js`、`ok线路.js` 是 Worker 脚本，通过 `ROUTE_CONFIG` 把 `/tv`、`/yl` 这类无后缀路径映射到具体的 json，并强制 `Content-Type: application/json`。用法原文见 `README-legacy.md`。

现在的 `config.json` 与 Worker 是两条并行路线：Worker 适合自定义域名 + 简洁路径，本仓库的 jsDelivr 地址适合直接填。

## 本地重测

```bash
python scripts/probe.py        # 探测 → probe.json
python scripts/build_pack.py   # 重建 → config*.json / live.json / 测试报告.csv
```

只依赖 Python 标准库，无需装包。要加新源，往 `tvbox-api-list.txt` 追加 `名称<TAB>地址` 后重跑即可。

## 自动刷新（可选）

`.github/workflows/refresh.yml` 计划每周一 04:00 重测并提交，但目前**没有生效**，两个前提：

1. 细粒度 token 需要额外勾选 **Workflows: Read and write** 才能写入该文件；
2. 本仓库是 fork，GitHub 默认不在 fork 上运行 Actions，需要在 Actions 标签页点一次「I understand my workflows, go ahead and enable them」。

不想折腾就手动跑上面两条命令，效果一样。

## 实测遇到的坑

1. **返回 200 不等于可用。** 「饭太硬」5 个域名全部返回 20KB 的 JPEG 占位图，只看状态码会全部误判为正常。
2. **`0.12yue.de5.net` 和 `jijietvbox.lol` 会限流。** 并发 20 路时集体超时、部分地址回 403；降到 6 路 + 重试就全通。客户端一次拉多仓集体报错，通常不是源挂了。
3. **`xhztv.top/4k.json` 是源站自己写坏的**：JSON 字符串里有裸换行，严格解析必失败。
4. **中文域名要转 Punycode**（`饭太硬.net` → `xn--sss604efuw.net`），直接填中文域名多数客户端解析不了。
5. **带 `spider` 指向 jar 的源有代码执行权限**，`http://` 明文源的内容可被链路篡改，别在主力设备上跑。
6. **同类条目会重名**，已自动加 `(2)(3)` 序号区分，它们其实是同一作者的不同镜像，留作备用。

## 免责

本仓库仅整理公开可访问的接口地址与探测结果，不托管、不分发任何音视频内容。各接口的内容与合法性由对应源站负责，请自行判断合规性，勿用于商业或违法用途。
