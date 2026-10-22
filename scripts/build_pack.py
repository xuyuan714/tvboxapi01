# -*- coding: utf-8 -*-
"""读取 probe.json，生成 config.json / config-lite.json / live.json / 测试报告.csv

同时把仓库根目录下已有的配置文件（lige.json、merged.json 等）一并收进入口，
这样「一个地址 = 本仓全部 + 外部实测」。
"""
import json, csv, os, re, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLUG = os.environ.get("GITHUB_REPOSITORY", "xuyuan714/tvboxapi01")
CDN = f"https://cdn.jsdelivr.net/gh/{SLUG}@main/"
rows = json.loads((ROOT / "probe.json").read_text(encoding="utf-8"))

# 探测受限但实测可用、或类型需要纠正的条目
OVERRIDE = {
    "https://jijietvbox.lol/jieluntan-wxe.json": ("single", 96),
    "https://jijietvbox.lol/jieluntan-ner.json": ("single", 63),
    "https://0.12yue.de5.net/tvbox/摸鱼.json": ("single", 97),
    "http://xhztv.top/4k.json": ("badjson", 0),
}

single, multi, live, dead = [], [], [], []
seen = set()
for r in rows:
    url = r["url"]
    if url in seen:
        continue
    seen.add(url)
    kind, sites = r["kind"], r.get("sites") or 0
    subs = r.get("subs") or 0
    if url in OVERRIDE:
        kind, sites = OVERRIDE[url]
    if kind == "single":
        single.append({"name": r["name"], "url": url, "sites": sites, "ms": r["ms"] or 9999})
    elif kind == "multi":
        multi.append({"name": r["name"], "url": url, "subs": subs, "ms": r["ms"] or 9999})
    elif kind in ("m3u", "livesrc"):
        live.append({"name": r["name"], "url": url})
    else:
        dead.append(r)

multi.sort(key=lambda x: -x["subs"])
single.sort(key=lambda x: (x["ms"], -x["sites"]))


# ---------- 扫描仓内已有配置 ----------
def strip_c(t):
    t = t.lstrip("\ufeff")
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    out = []
    for line in t.splitlines():
        q, cut, i = False, len(line), 0
        while i < len(line):
            c = line[i]
            if c == "\\" and q:
                i += 2
                continue
            if c == '"':
                q = not q
            elif not q and c == "/" and i + 1 < len(line) and line[i + 1] == "/":
                cut = i
                break
            i += 1
        out.append(line[:cut])
    return re.sub(r",\s*([}\]])", r"\1", "\n".join(out)).strip()


SKIP = {"config.json", "config-lite.json", "live.json", "probe.json"}
local_multi, local_single, local_live = [], [], []
for f in sorted(ROOT.iterdir()):
    if not f.is_file() or f.name in SKIP or f.suffix.lower() not in (".json", ".js", ".m3u", ".txt"):
        continue
    url = CDN + urllib.parse.quote(f.name)
    if f.suffix.lower() in (".m3u", ".txt"):
        if f.suffix.lower() == ".m3u" or "#EXTM3U" in f.read_text(encoding="utf-8", errors="ignore")[:200]:
            local_live.append({"name": f"本仓-{f.stem}", "url": url})
        continue
    try:
        d = json.loads(strip_c(f.read_text(encoding="utf-8", errors="ignore")))
    except Exception:
        continue
    if not isinstance(d, dict):
        continue
    if "urls" in d:
        local_multi.append({"name": f"本仓·{f.stem}", "url": url, "subs": len(d["urls"] or []), "ms": 0})
    elif "sites" in d:
        local_single.append({"name": f"本仓·{f.stem}", "url": url, "sites": len(d["sites"] or []), "ms": 0})
    elif "lives" in d:
        local_live.append({"name": f"本仓·{f.stem}", "url": url})

local_multi.sort(key=lambda x: -x["subs"])
local_single.sort(key=lambda x: -x["sites"])
print(f"仓内：多仓 {len(local_multi)} / 单仓 {len(local_single)} / 直播 {len(local_live)}")


def tag(d):
    return f'{d["name"]} · {d.get("subs", d.get("sites"))}{"子仓" if "subs" in d else "站"}'


# 同名接口自动加序号，避免客户端里出现一堆同名条目
_nm = {}
def uniq(n):
    if n not in _nm:
        _nm[n] = 1
        return n
    _nm[n] += 1
    return f"{n} ({_nm[n]})"


full = {"urls": [{"url": d["url"], "name": uniq(tag(d))}
                 for d in local_multi + multi + local_single + single]}
(ROOT / "config.json").write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")

light_urls = local_single[:3] + multi[:2]
names, picks = set(), []
for s in single:
    if s["sites"] < 30 or s["name"] in names:
        continue
    names.add(s["name"])
    picks.append(s)
light_urls += picks[:9]
(ROOT / "config-lite.json").write_text(
    json.dumps({"urls": [{"url": d["url"], "name": tag(d)} for d in light_urls]}, ensure_ascii=False, indent=1),
    encoding="utf-8")

def live_name(u):
    if "migu" in u:
        return "Migu 咪咕（gh 代理）"
    if "zb.php" in u:
        return "直播频道表 M3U"
    if "1288" in u:
        return "央视卫视 TXT"
    return "直播 " + (urllib.parse.urlsplit(u).hostname or "")


lives = {"lives": [{"name": d["name"], "type": 0, "url": d["url"], "playerType": 1}
                   for d in local_live] + [{"name": live_name(d["url"]), "type": 0, "url": d["url"], "playerType": 1}
                   for d in live]}
(ROOT / "live.json").write_text(json.dumps(lives, ensure_ascii=False, indent=1), encoding="utf-8")

VERDICT = {"single": "可用-点播", "multi": "可用-多仓", "m3u": "可用-直播", "livesrc": "可用-直播",
           "image": "失效-返回图片", "badjson": "失效-源站语法错误", "html": "非接口-网页",
           "unknown": "无效", "fail": "失效", "json?": "待确认", "json-list": "待确认", "live": "可用-直播"}
with open(ROOT / "测试报告.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["名称", "地址", "状态码", "耗时ms", "类型", "规模", "结论"])
    for r in rows:
        k = r["kind"]
        if r["url"] in OVERRIDE:
            k = OVERRIDE[r["url"]][0]
        scale = f'{r.get("sites")}站' if r["kind"] == "single" else (f'{r.get("subs")}子仓' if r["kind"] == "multi" else "")
        w.writerow([r["name"], r["url"], r.get("status") or "", r.get("ms") or "", k, scale, VERDICT.get(k, k)])

print(f"单仓 {len(single)} / 多仓 {len(multi)} / 直播 {len(live)} / 失效 {len(dead)} / 精简 {len(light_urls)}")
