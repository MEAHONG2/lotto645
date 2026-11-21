#!/usr/bin/env python3
"""data/draws.json 에 아직 없는 로또 6/45 회차를 추가해요.

1순위: 동행복권 공식 API. 안 되면 공개 미러 여러 곳을 읽어서
번호 6개와 보너스가 두 곳 이상 일치할 때만 추가해요.
표준 라이브러리만 써요.
"""
import datetime as dt
import json
import pathlib
import sys
import urllib.request

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "draws.json"
KST = dt.timezone(dt.timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (lotto645 data updater)"}
RAW = "https://raw.githubusercontent.com"


def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def valid(nums, bonus):
    allv = list(nums) + [bonus]
    return len(nums) == 6 and len(set(allv)) == 7 and all(isinstance(n, int) and 1 <= n <= 45 for n in allv)


def from_official(n):
    d = get_json(f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={n}")
    if d.get("returnValue") != "success":
        return None
    return {
        "nums": sorted(d[f"drwtNo{i}"] for i in range(1, 7)),
        "bonus": d["bnusNo"],
        "date": d["drwNoDate"],
        "prize": d.get("firstWinamnt"),
        "winners": d.get("firstPrzwnerCo"),
    }


def from_utopia(n):
    folder = "1-1000" if n <= 1000 else "1001-2000"
    d = get_json(f"{RAW}/Utopia-ZEN/hotnumber/HEAD/lotto_data/{folder}/{n}.lotto")
    if d.get("round") != n:
        return None
    return {"nums": sorted(d["numbers"]), "bonus": d["bonus"], "date": None,
            "prize": d.get("amount_per_winner"), "winners": d.get("winners")}


def from_gurdung(n):
    d = get_json(f"{RAW}/gurdung-sys/Bokdeongi-lotto-data/HEAD/docs/rounds/{n}.json")
    if d.get("round") != n:
        return None
    return {"nums": sorted(d["numbers"]), "bonus": d["bonus"], "date": d.get("draw_date"), "prize": None, "winners": None}


def from_visionary(n):
    d = get_json(f"{RAW}/visionary153/lotto-api/HEAD/results/{n}.json")
    if d.get("round") != n:
        return None
    r1 = next((r for r in d.get("ranks") or [] if r.get("rank") == 1), {})
    return {"nums": sorted(d["numbers"]), "bonus": d["bonus"], "date": d.get("date"),
            "prize": r1.get("prize"), "winners": r1.get("winners")}


_uriseozz = None


def from_uriseozz(n):
    global _uriseozz
    if _uriseozz is None:
        _uriseozz = {r["id"]: r for r in get_json(f"{RAW}/uriseozz/lotto-data/HEAD/lotto.json", 60)["rounds"]}
    r = _uriseozz.get(n)
    if not r:
        return None
    return {"nums": sorted(r[f"n{i}"] for i in range(1, 7)), "bonus": r["bonus"], "date": r.get("draw_date"),
            "prize": r.get("first_prize_each"), "winners": r.get("first_winners")}


MIRRORS = [("Utopia-ZEN/hotnumber", from_utopia), ("gurdung-sys/Bokdeongi-lotto-data", from_gurdung),
           ("visionary153/lotto-api", from_visionary), ("uriseozz/lotto-data", from_uriseozz)]


def try_source(name, fn, n):
    try:
        r = fn(n)
    except Exception as e:  # 네트워크 오류, 아직 없는 회차(404) 등
        print(f"  {name}: 없음 ({type(e).__name__})")
        return None
    if r and valid(r["nums"], r["bonus"]):
        print(f"  {name}: {r['nums']} + {r['bonus']}")
        return r
    print(f"  {name}: 없음")
    return None


def fetch_round(n, expected_date):
    print(f"{n}회 ({expected_date}) 찾는 중")
    official = try_source("동행복권 공식", from_official, n)
    if official:
        return official, "동행복권 공식"
    found = [(name, r) for name, fn in MIRRORS if (r := try_source(name, fn, n))]
    groups = {}
    for name, r in found:
        groups.setdefault((tuple(r["nums"]), r["bonus"]), []).append((name, r))
    agree = max(groups.values(), key=len) if groups else []
    if len(agree) < 2:
        print("  두 곳 이상 일치하지 않아 건너뛰어요")
        return None, None
    dates = {r["date"] for _, r in agree if r["date"]}
    if dates and expected_date not in dates:
        print(f"  추첨일이 맞지 않아 건너뛰어요: {dates}")
        return None, None
    best = next((r for _, r in agree if r["prize"] is not None and r["winners"] is not None), agree[0][1])
    result = dict(agree[0][1], prize=best["prize"], winners=best["winners"], date=expected_date)
    return result, " + ".join(name for name, _ in agree)


def main():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    draws = doc["draws"]
    last_no, last_date = draws[-1][0], dt.date.fromisoformat(draws[-1][1])
    today = dt.datetime.now(KST).date()
    added = []
    n = last_no + 1
    while True:
        expected = last_date + dt.timedelta(days=7 * (n - last_no))
        if expected > today:
            break
        r, src = fetch_round(n, expected.isoformat())
        if not r:
            break
        draws.append([n, expected.isoformat(), *r["nums"], r["bonus"], int(r["prize"] or 0), int(r["winners"] or 0)])
        added.append(f"{n}회 {r['nums']} + {r['bonus']} ({src})")
        n += 1
    if not added:
        print("추가할 회차가 없어요")
        return 0
    doc["updated"] = today.isoformat()
    DATA.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("추가:", *added, sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
