#!/usr/bin/env python3
"""Poll yorkregionisl.com (YRISL indoor league, powered by e2esoccer) for
Girls U8 (2019) games of THPFC Red GU8 / THPFC White GU8 and write
index.html + schedule.ics. Standard library only."""
import datetime as dt, html, re, sys, urllib.request
from html.parser import HTMLParser

BASE = "https://yorkregionisl.com/schedule/"
DIVISION_ID = 10                       # Girls U8 (2019)
TEAMS = {651: "THPFC Red GU8", 652: "THPFC White GU8"}
GAME_MINUTES = 60
TZ = "America/Toronto"

class Rows(HTMLParser):
    def __init__(s):
        super().__init__(); s.rows=[]; s.row=None; s.cell=None; s.href=None; s.skip=False
    def handle_starttag(s, t, a):
        a = dict(a)
        if t == "tr": s.row = []
        elif t == "td" and s.row is not None:
            s.skip = "d-md-none" in (a.get("class") or "")
            s.cell = {"text": "", "href": None, "skip": s.skip}
        elif t == "a" and s.cell is not None: s.cell["href"] = a.get("href")
    def handle_data(s, d):
        if s.cell is not None: s.cell["text"] += d
    def handle_endtag(s, t):
        if t == "td" and s.cell is not None:
            s.row.append(s.cell); s.cell = None
        elif t == "tr" and s.row is not None:
            s.rows.append(s.row); s.row = None

def fetch(team_id):
    cookie = (f"e2elc_gamesdivisionid={DIVISION_ID}; e2elc_futureonly=false; "
              f"e2e-teamid={team_id}; e2e-filter=")
    req = urllib.request.Request(BASE, headers={"Cookie": cookie, "User-Agent": "yrisl-calendar/1.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

def parse_games(page, team):
    p = Rows(); p.feed(page); out = []
    today = dt.date.today()
    for r in p.rows:
        c = [x for x in r if not x["skip"]]
        if len(c) < 8 or not (c[0]["href"] or "").startswith("/game-details"): continue
        num, _, _, date, ko, field, home, away = [x["text"].strip() for x in c[:8]]
        if team not in (home, away): continue
        m = re.match(r"([A-Za-z]{3}) (\d+)$", date); t = re.match(r"(\d+):(\d+)(am|pm)$", ko)
        if not (m and t): continue
        mon = dt.datetime.strptime(m.group(1), "%b").month; day = int(m.group(2))
        year = today.year
        d = dt.date(year, mon, day)
        if (today - d).days > 180: d = dt.date(year + 1, mon, day)   # season spans New Year
        h = int(t.group(1)) % 12 + (12 if t.group(3) == "pm" else 0)
        start = dt.datetime.combine(d, dt.time(h, int(t.group(2))))
        out.append(dict(num=num, start=start, field=field, map=c[5]["href"], home=home, away=away, team=team))
    return out

def esc(s): return s.replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n")

def ics(games):
    L = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//yrisl-calendar//EN","CALSCALE:GREGORIAN",
         "X-WR-CALNAME:THPFC Girls U8 (YRISL Indoor)", f"X-WR-TIMEZONE:{TZ}",
         "REFRESH-INTERVAL;VALUE=DURATION:PT6H","X-PUBLISHED-TTL:PT6H",
         "BEGIN:VTIMEZONE",f"TZID:{TZ}",
         "BEGIN:DAYLIGHT","DTSTART:19700308T020000","RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU",
         "TZOFFSETFROM:-0500","TZOFFSETTO:-0400","TZNAME:EDT","END:DAYLIGHT",
         "BEGIN:STANDARD","DTSTART:19701101T020000","RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU",
         "TZOFFSETFROM:-0400","TZOFFSETTO:-0500","TZNAME:EST","END:STANDARD","END:VTIMEZONE"]
    for g in games:
        end = g["start"] + dt.timedelta(minutes=GAME_MINUTES); f = "%Y%m%dT%H%M%S"
        L += ["BEGIN:VEVENT", f"UID:yrisl-game{g['num']}-{g['team'].split()[1].lower()}@yrisl-calendar",
              f"DTSTAMP:{dt.datetime.utcnow().strftime(f)}Z",
              f"DTSTART;TZID={TZ}:{g['start'].strftime(f)}", f"DTEND;TZID={TZ}:{end.strftime(f)}",
              f"SUMMARY:{esc(g['home'] + ' vs ' + g['away'])}", f"LOCATION:{esc(g['field'])}",
              f"DESCRIPTION:{esc('Game #' + g['num'] + ' - YRISL Girls U8 (2019)' + (chr(10) + 'Map: ' + g['map'] if g['map'] else ''))}",
              "END:VEVENT"]
    return "\r\n".join(L + ["END:VCALENDAR"]) + "\r\n"

def page(games):
    rows = "".join(
        f"<tr><td>{g['start']:%a %b %-d}</td><td>{g['start']:%-I:%M %p}</td>"
        f"<td><span class='tag {'red' if 'Red' in g['team'] else 'white'}'>{html.escape(g['team'].replace(' GU8',''))}</span></td>"
        f"<td>{html.escape(g['home'])} vs {html.escape(g['away'])}</td>"
        f"<td>{'<a href=\"'+html.escape(g['map'])+'\">' if g['map'] else ''}{html.escape(g['field'])}{'</a>' if g['map'] else ''}</td></tr>"
        for g in games) or "<tr><td colspan=5>No upcoming games listed.</td></tr>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>THPFC Girls U8 Schedule</title><style>
:root{{--bg:#fff;--fg:#1d2330;--mut:#667085;--line:#e4e7ec;--acc:#1f6feb}}
@media(prefers-color-scheme:dark){{:root{{--bg:#12151c;--fg:#e8ebf2;--mut:#98a2b3;--line:#2a3140;--acc:#6ea8ff}}}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:820px;margin:auto}}h1{{font-size:1.5rem;margin:0}}p{{color:var(--mut)}}a{{color:var(--acc)}}
table{{width:100%;border-collapse:collapse;margin-top:16px}}th,td{{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}}
.tag{{padding:2px 8px;border-radius:99px;font-size:.8rem;border:1px solid var(--line)}}.red{{background:#fde4e4;color:#8a1f1f}}.white{{background:#eef0f4;color:#333}}
.wrap{{overflow-x:auto}}</style></head><body><main>
<h1>THPFC Girls U8 (2019) - Indoor Schedule</h1>
<p>THPFC Red GU8 and THPFC White GU8, York Region Indoor Soccer League. Updated {dt.datetime.utcnow():%b %-d, %Y %H:%M} UTC.
Subscribe in your calendar app: <a href="schedule.ics">schedule.ics</a> (copy this link's address into Google/Apple/Outlook "add by URL").</p>
<div class="wrap"><table><thead><tr><th>Date</th><th>Kickoff</th><th>Team</th><th>Game</th><th>Field</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Source: <a href="https://yorkregionisl.com/schedule/">yorkregionisl.com</a>. Always confirm times with the league.</p>
</main></body></html>"""

def main():
    games = []
    for tid, name in TEAMS.items():
        games += parse_games(fetch(tid), name)
    games.sort(key=lambda g: (g["start"], g["team"]))
    if not games: sys.exit("no games parsed - site layout may have changed")
    open("schedule.ics", "w", newline="").write(ics(games))
    open("index.html", "w").write(page(games))
    print(f"wrote {len(games)} games")

if __name__ == "__main__": main()
