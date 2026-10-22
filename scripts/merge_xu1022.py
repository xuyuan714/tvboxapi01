# -*- coding: utf-8 -*-
"""把仓库内已有的接口文件整理、测试、合并成 xu1022.json

规则：
- type 3/4 的站点依赖 spider jar，jar 拿不到（404/401/相对路径）就丢弃，否则客户端只会报错
- type 0/1 的站点不需要 jar，直接保留
- 站点按 (api, name) 去重，key 冲突自动改名
- 代理受限（Tunnel failed）的 jar 不算死，标 blocked 并单列
"""
import json, re, csv, ssl, time, urllib.request
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
SLUG = "xuyuan714/tvboxapi01"
CDN = f"https://cdn.jsdelivr.net/gh/{SLUG}@main/"
SKIP = {"config.json", "config-lite.json", "live.json", "probe.json",
        "xu1022.json", "xu1022-duo.json"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


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


def load(f):
    try:
        d = json.loads(strip_c(f.read_text(encoding="utf-8", errors="ignore")))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


# ---------- 1. 收集 ----------
sources, multis = [], []
for f in sorted(ROOT.iterdir()):
    if not f.is_file() or f.name in SKIP:
        continue
    if f.suffix.lower() not in (".json", ".js"):
        continue
    d = load(f)
    if not d:
        continue
    if "urls" in d:
        multis.append((f, d))
    elif "sites" in d:
        sources.append((f, d))

print(f"扫描到单仓 {len(sources)} 个、多仓 {len(multis)} 个")

# ---------- 2. 测 jar ----------
jars = set()
for f, d in sources:
    sp = (d.get("spider") or "").split(";")[0].strip()
    if sp:
        jars.add(sp)
    for s in d.get("sites") or []:
        sj = (s.get("jar") or "").split(";")[0].strip()
        if sj:
            jars.add(sj)


def check(j):
    """重试 2 次。只有明确的 404/401/502、相对路径才算死；
    超时/SSL 抖动算 unstable（保留站点，避免一次抖动误杀整批）"""
    r = {"url": j, "status": "", "ms": None, "size": 0, "verdict": "dead"}
    if not j:
        return r
    if not j.startswith("http"):
        r["status"] = "relative"
        return r
    for att in range(2):
        t0 = time.time()
        try:
            req = urllib.request.Request(j, headers={"User-Agent": "okhttp/3.12.0"})
            with urllib.request.urlopen(req, timeout=20, context=CTX) as resp:
                b = resp.read(65536)
                r["status"] = resp.status
                r["size"] = len(b)
                r["ms"] = int((time.time() - t0) * 1000)
                r["verdict"] = "ok" if b[:2] == b"PK" or b[:3] == b"dex" else "notjar"
                return r
        except urllib.error.HTTPError as e:
            r["status"], r["ms"] = str(e.code), int((time.time() - t0) * 1000)
            if e.code in (404, 401, 410, 403):
                r["verdict"] = "dead"
                return r
            r["verdict"] = "dead" if e.code == 502 else "unstable"
        except Exception as e:
            msg = str(e)
            r["status"], r["ms"] = type(e).__name__, int((time.time() - t0) * 1000)
            r["verdict"] = "blocked" if "Tunnel connection failed" in msg else "unstable"
        time.sleep(2)
    return r


JAR = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    for r in ex.map(check, sorted(jars)):
        JAR[r["url"]] = r
print(Counter(v["verdict"] for v in JAR.values()))

# ---------- 3. 合并 ----------
sites, parses, lives, seen_api, seen_key = [], [], [], set(), set()
stat = []

for f, d in sources:
    gjar = (d.get("spider") or "").split(";")[0].strip()
    keep = drop_jar = drop_dup = 0
    kept_keys = []
    for s in d.get("sites") or []:
        s = dict(s)
        t = s.get("type", 0)
        eff = (s.get("jar") or gjar or "").split(";")[0].strip()
        if t in (3, 4):
            v = JAR.get(eff, {}).get("verdict", "dead")
            if v != "ok":
                drop_jar += 1
                continue
            s["jar"] = eff
        sig = (str(s.get("api", ""))[:90], str(s.get("name", "")))
        if sig in seen_api:
            drop_dup += 1
            continue
        seen_api.add(sig)
        k = s.get("key") or f"{f.stem}_{len(sites)}"
        n = 1
        base = k
        while k in seen_key:
            n += 1
            k = f"{base}_{n}"
        seen_key.add(k)
        s["key"] = k
        sites.append(s)
        kept_keys.append(k)
        keep += 1
    for p in d.get("parses") or []:
        if p not in parses:
            parses.append(p)
    for l in d.get("lives") or []:
        u = l.get("url")
        if u and not any(x.get("url") == u for x in lives):
            lives.append(l)
    stat.append({"file": f.name, "sites": len(d.get("sites") or []),
                 "keep": keep, "drop_jar": drop_jar, "drop_dup": drop_dup,
                 "jar": gjar, "_keys": kept_keys})

# 直播：把 4Gtv.m3u 也挂上
m3u = ROOT / "4Gtv.m3u"
if m3u.exists():
    u = CDN + "4Gtv.m3u"
    if not any(x.get("url") == u for x in lives):
        lives.insert(0, {"name": "本仓-4Gtv", "type": 0, "url": u, "playerType": 1})

# ---------- 4. 剔除实测死亡的 api 站点 ----------
DEAD_API = ROOT / "_dead_api.json"
dead_keys = set(json.loads(DEAD_API.read_text(encoding="utf-8"))) if DEAD_API.exists() else set()
if dead_keys:
    before = len(sites)
    sites = [s for s in sites if s.get("key") not in dead_keys]
    for r in stat:
        r["final"] = len([k for k in r["_keys"] if k not in dead_keys])
    print(f"按 api 实测剔除 {before - len(sites)} 个站点")
else:
    for r in stat:
        r["final"] = r["keep"]

# ---------- 5. 输出 ----------
merged = {
    "spider": "",
    "sites": sites,
    "parses": parses,
    "lives": lives,
    "flags": ["youku", "qq", "iqiyi", "qiyi", "letv", "sohu", "tudou", "pptv",
              "mgtv", "wasu", "bilibili", "renrenmi", "xigua"],
}
(ROOT / "xu1022.json").write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")

duo = {"urls": [{"url": CDN + f.name, "name": f"本仓·{f.stem} · {len(d.get('sites') or [])}站"}
                for f, d in sources]
       + [{"url": CDN + f.name, "name": f"本仓·{f.stem} · 多仓{len(d.get('urls') or [])}"}
          for f, d in multis]}
(ROOT / "xu1022-duo.json").write_text(json.dumps(duo, ensure_ascii=False, indent=1), encoding="utf-8")

with open(ROOT / "xu1022-测试报告.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["源文件", "原站点数", "最终保留", "丢弃(缺jar)", "丢弃(重复)", "丢弃(api死链)", "全局jar"])
    for r in stat:
        w.writerow([r["file"], r["sites"], r.get("final", r["keep"]), r["drop_jar"], r["drop_dup"],
                    r["keep"] - r.get("final", r["keep"]), r["jar"][:70]])
    w.writerow([])
    w.writerow(["合计", sum(r["sites"] for r in stat), sum(r.get("final", r["keep"]) for r in stat),
                sum(r["drop_jar"] for r in stat), sum(r["drop_dup"] for r in stat),
                sum(r["keep"] - r.get("final", r["keep"]) for r in stat), ""])

print(f"\n合并结果：站点 {len(sites)}（唯一 key {len({x['key'] for x in sites})}），parses {len(parses)}，lives {len(lives)}")
print("类型分布", Counter(str(s.get("type", 0)) for s in sites))
print("\n各源：")
for r in stat:
    print(f"  {r['file']:<18} 原{r['sites']:>4} 留{r['keep']:>4} 缺jar{r['drop_jar']:>4} 重复{r['drop_dup']:>4}")
print("\njar 状态：")
for j, v in JAR.items():
    print(f"  {v['verdict']:<9} {v['status']:<14} {j[:66]}")
