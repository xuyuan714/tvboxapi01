# tvboxapi01

自用 TVBox 接口集合。所有地址都经过实测（状态码 + 内容解析 + 规模校验），只保留真正能返回配置的接口。

- 最近更新：2026-10-22
- 当前可用：点播单仓 **55** 个、多仓 **4** 个、直播源 **3** 个
- 已剔除：**16** 个失效（返图 / 502 / 404 / 源站 JSON 语法错误）

## 导入地址

任选一条填进客户端的「配置地址」：

| 用途 | 地址 |
|---|---|
| 全量（推荐） | `https://raw.githubusercontent.com/xuyuan714/tvboxapi01/main/config.json` |
| 全量（jsDelivr 加速） | `https://cdn.jsdelivr.net/gh/xuyuan714/tvboxapi01@main/config.json` |
| 全量（ghproxy 加速） | `https://ghproxy.net/https://raw.githubusercontent.com/xuyuan714/tvboxapi01/main/config.json` |
| 精简（14 条，加载快） | `https://raw.githubusercontent.com/xuyuan714/tvboxapi01/main/config-lite.json` |
| 直播源 | `https://raw.githubusercontent.com/xuyuan714/tvboxapi01/main/live.json` |

> 国内直连 `raw.githubusercontent.com` 经常超时，优先用 jsDelivr 或 ghproxy 那两条。

## 文件

| 文件 | 说明 |
|---|---|
| `config.json` | 多仓格式，59 条：4 个多仓 + 55 个单仓，按响应速度排序 |
| `config-lite.json` | 精选 14 条，同名源只保留最快的一个 |
| `live.json` | 3 个可用直播源（频道表 M3U / 咪咕 / 央视卫视 TXT） |
| `tvbox-api-list.txt` | 源清单，格式 `名称<TAB>地址`，加新源就往这加一行 |
| `probe.json` | 最近一次探测的原始结果（状态码、耗时、类型、站点数） |
| `测试报告.csv` | 同上，表格形式，可直接用 Excel 打开 |
| `scripts/probe.py` | 探测全部接口 |
| `scripts/build_pack.py` | 按探测结果重建上面几个配置文件 |
| `.github/workflows/refresh.yml` | 每周一 04:00 自动重测并提交 |

## 本地重测

```bash
python scripts/probe.py        # 探测 → probe.json
python scripts/build_pack.py   # 重建 → config*.json / live.json / 测试报告.csv
```

只依赖 Python 标准库，无需装包。

## 实测中遇到的几个坑

1. **返回 200 不等于可用。** 「饭太硬」5 个域名全部返回 20KB 的 JPEG 占位图，只看状态码会全部误判为正常。
2. **`0.12yue.de5.net` 和 `jijietvbox.lol` 会限流。** 并发 20 路时集体超时、部分地址回 403；降到 6 路 + 重试就全通。客户端一次拉多仓集体报错，通常不是源挂了。
3. **`xhztv.top/4k.json` 是源站自己写坏的**：JSON 字符串里有裸换行，严格解析必失败。
4. **中文域名要转 Punycode**（`饭太硬.net` → `xn--sss604efuw.net`），直接填中文域名多数客户端解析不了。
5. **带 `spider` 指向 jar 的源有代码执行权限**，`http://` 明文源的内容可被链路篡改，别在主力设备上跑。

## 免责

本仓库仅整理公开可访问的接口地址与探测结果，不托管、不分发任何音视频内容。各接口的内容与合法性由对应源站负责，请自行判断合规性，勿用于商业或违法用途。
