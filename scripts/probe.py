# -*- coding: utf-8 -*-
"""探测 tvbox-api-list.txt 中全部接口，输出 probe.json（仓库根目录）"""
import json, ssl, time, re, sys
import urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tvbox-api-list.txt"
OUT = ROOT / "probe.json"

UA = "okhttp/3.12.0"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def norm(u):
    p = urllib.parse.urlsplit(u)
    path = urllib.parse.quote(p.path, safe="/%:@&=+$,~-._!*'()")
    q = urllib.parse.quote(p.query, safe="=&%:@+,/?~-._!*'()")
    netloc = p.netloc
    try:
        netloc.encode("ascii")
    except UnicodeEncodeError:
        host, _, port = netloc.partition(":")
        netloc = host.encode("idna").decode() + ((":" + port) if port else "")
    return urllib.parse.urlunsplit((p.scheme, netloc, path, q, ""))


def strip_comments(t):
    """去掉 BOM、// 与 /* */ 注释、尾逗号，兼容源站不规范写法"""
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
    t = "\n".join(out)
    return re.sub(r",\s*([}\]])", r"\1", t).strip()


def try_json(txt):
    for f in (lambda s: s, strip_comments):
        s = f(txt)
        if not s or s[0] not in "{[":
            continue
        try:
            return json.loads(s)
        except Exception:
            pass
    return None


def probe(item):
    name, url = item
    r = {"name": name, "url": url, "status": None, "ms": None, "ctype": "",
         "kind": "fail", "detail": "", "sites": 0, "subs": 0, "spider": ""}
    for attempt in range(2):
        t0 = time.time()
        try:
            req = urllib.request.Request(norm(url), headers={
                "User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=20, context=CTX) as resp:
                body = resp.read(2_000_000)
                r["status"] = resp.status
                r["ctype"] = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
            r["ms"] = int((time.time() - t0) * 1000)
            txt = body.decode("utf-8", "ignore")
            data = try_json(txt)
            if isinstance(data, dict):
                if "urls" in data:
                    r["kind"], r["subs"] = "multi", len(data.get("urls") or [])
                    r["detail"] = f"多仓 {r['subs']} 子仓"
                elif "sites" in data:
                    r["kind"], r["sites"] = "single", len(data.get("sites") or [])
                    r["detail"] = f"单仓 {r['sites']} 站点"
                elif "storeHouse" in data:
                    r["kind"], r["subs"] = "multi", len(data.get("storeHouse") or [])
                    r["detail"] = f"多仓(storeHouse) {r['subs']} 子仓"
                elif "lives" in data:
                    r["kind"], r["detail"] = "live", f"live {len(data.get('lives') or [])}"
                else:
                    r["kind"], r["detail"] = "json?", "JSON 无关键字段"
                sp = data.get("spider")
                if isinstance(sp, str):
                    r["spider"] = sp.split(";")[0]
            elif isinstance(data, list):
                r["kind"], r["detail"] = "json-list", f"数组 {len(data)}"
            elif body[:3] == b"\xff\xd8\xff" or body[:6] in (b"GIF89a", b"GIF87a"):
                r["kind"], r["detail"] = "image", f"返回图片 {len(body)}B"
            elif "#EXTM3U" in txt:
                r["kind"], r["detail"] = "m3u", "M3U 列表"
            elif "#genre#" in txt:
                r["kind"], r["detail"] = "livesrc", "TXT 直播源"
            elif "<html" in txt.lower():
                r["kind"], r["detail"] = "html", "网页"
            else:
                r["kind"], r["detail"] = "unknown", "非 JSON"
            if r["kind"] != "fail":
                return r
        except urllib.error.HTTPError as e:
            r["status"], r["ms"] = e.code, int((time.time() - t0) * 1000)
            r["detail"] = f"HTTP {e.code}"
        except Exception as e:
            r["ms"] = int((time.time() - t0) * 1000)
            r["detail"] = type(e).__name__ + ": " + str(e)[:80]
        time.sleep(1.5 * (attempt + 1))
    return r


def main():
    rows = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "\t" in line:
            n, u = line.split("\t", 1)
            rows.append((n.strip(), u.strip()))
    print(f"待测 {len(rows)} 条")
    out = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(probe, rows):
            out.append(r)
            print(f'{str(r["status"]):>4} {str(r["ms"]):>6} {r["kind"]:<9} {r["name"]:<8} {r["detail"][:30]}')
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(Counter(r["kind"] for r in out))


if __name__ == "__main__":
    main()
