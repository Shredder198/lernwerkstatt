#!/usr/bin/env python3
"""Erzeugt aus stundenplan.yaml eine .ics-Datei mit wöchentlich wiederkehrenden
Terminen. Schulferien und schulfreie Tage werden als Ausnahmen (EXDATE)
eingetragen, damit dort keine Stunden im Kalender stehen.

Aufruf:
    python3 kalender/stundenplan.py [stundenplan.yaml] [-o ausgabe.ics]

Die .ics-Datei lässt sich in Apple Kalender, Google Kalender und Outlook
importieren oder abonnieren.
"""

import argparse
import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent

WOCHENTAGE = {
    "mo": 0, "montag": 0,
    "di": 1, "dienstag": 1,
    "mi": 2, "mittwoch": 2,
    "do": 3, "donnerstag": 3,
    "fr": 4, "freitag": 4,
    "sa": 5, "samstag": 5,
}

# Mitteleuropäische Zeit mit Sommerzeit (gilt für Europe/Luxembourg).
VTIMEZONE = """BEGIN:VTIMEZONE
TZID:{tz}
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def als_datum(wert):
    return wert if isinstance(wert, date) else date.fromisoformat(str(wert))


def als_zeit(wert):
    # YAML liest 08:00 ohne Anführungszeichen als Sexagesimalzahl (480).
    if isinstance(wert, int):
        return f"{wert // 60:02d}:{wert % 60:02d}"
    return str(wert)


def freie_tage(ferien):
    """Alle Tage, an denen kein Unterricht ist, mit Grund."""
    tage = {}
    for f in ferien.get("ferien", []):
        tag, bis = als_datum(f["von"]), als_datum(f["bis"])
        while tag <= bis:
            tage[tag] = f["name"]
            tag += timedelta(days=1)
    for f in ferien.get("freie_tage", []):
        tage[als_datum(f["datum"])] = f["name"]
    return tage


def ics_text(text):
    return (str(text).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def falten(zeile):
    """Zeilen nach RFC 5545 auf 75 Bytes umbrechen."""
    roh = zeile.encode("utf-8")
    if len(roh) <= 75:
        return zeile
    teile, aktuell = [], b""
    for zeichen in zeile:
        z = zeichen.encode("utf-8")
        if len(aktuell) + len(z) > (75 if not teile else 74):
            teile.append(aktuell.decode("utf-8"))
            aktuell = b""
        aktuell += z
    teile.append(aktuell.decode("utf-8"))
    return "\r\n ".join(teile)


def stunde_zu_vevent(stunde, schuljahr, frei, tz, stempel):
    wochentag = WOCHENTAGE[str(stunde["tag"]).strip().lower()]
    von = datetime.strptime(als_zeit(stunde["von"]), "%H:%M").time()
    bis = datetime.strptime(als_zeit(stunde["bis"]), "%H:%M").time()

    start = max(als_datum(schuljahr["beginn"]),
                als_datum(stunde.get("gueltig_ab", schuljahr["beginn"])))
    ende = min(als_datum(schuljahr["ende"]),
               als_datum(stunde.get("gueltig_bis", schuljahr["ende"])))
    start += timedelta(days=(wochentag - start.weekday()) % 7)
    if start > ende:
        return None

    # Erster Termin darf nicht selbst in den Ferien liegen.
    while start in frei and start <= ende:
        start += timedelta(days=7)
    if start > ende:
        return None

    ausnahmen = []
    tag = start
    while tag <= ende:
        if tag in frei:
            ausnahmen.append(tag)
        tag += timedelta(days=7)

    titel = f"{stunde['fach']} {stunde['klasse']}"
    beschreibung = f"Klasse: {stunde['klasse']}\nFach: {stunde['fach']}"
    if stunde.get("notiz"):
        beschreibung += f"\n{stunde['notiz']}"
    schluessel = f"{wochentag}|{von}|{stunde['klasse']}|{stunde['fach']}|{start}"
    uid = hashlib.sha1(schluessel.encode()).hexdigest()[:16]
    # UNTIL muss bei DTSTART mit TZID in UTC stehen; Tagesende reicht.
    until = datetime.combine(ende, datetime.max.time()) - timedelta(hours=2)

    zeilen = [
        "BEGIN:VEVENT",
        f"UID:stundenplan-{uid}@lernwerkstatt",
        f"DTSTAMP:{stempel}",
        f"DTSTART;TZID={tz}:{datetime.combine(start, von):%Y%m%dT%H%M%S}",
        f"DTEND;TZID={tz}:{datetime.combine(start, bis):%Y%m%dT%H%M%S}",
        f"RRULE:FREQ=WEEKLY;UNTIL={until:%Y%m%dT%H%M%S}Z",
        f"SUMMARY:{ics_text(titel)}",
        f"LOCATION:{ics_text(stunde.get('raum', ''))}",
        f"DESCRIPTION:{ics_text(beschreibung)}",
        "CATEGORIES:Unterricht",
    ]
    for tag in ausnahmen:
        zeilen.append(
            f"EXDATE;TZID={tz}:{datetime.combine(tag, von):%Y%m%dT%H%M%S}")
    zeilen.append("END:VEVENT")
    return zeilen


def erzeuge_ics(plan_pfad):
    plan = yaml.safe_load(Path(plan_pfad).read_text(encoding="utf-8"))
    ferien_pfad = Path(plan_pfad).parent / plan.get("ferien", "ferien_lu_2026_27.yaml")
    ferien = yaml.safe_load(ferien_pfad.read_text(encoding="utf-8"))
    tz = plan.get("zeitzone", "Europe/Luxembourg")
    frei = freie_tage(ferien)
    # Fester Zeitstempel, damit die Datei nur bei echten Änderungen anders aussieht.
    stempel = f"{als_datum(ferien['schuljahr']['beginn']):%Y%m%d}T000000Z"

    zeilen = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//lernwerkstatt//Stundenplan//DE",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Stundenplan",
        f"X-WR-TIMEZONE:{tz}",
        *VTIMEZONE.format(tz=tz).splitlines(),
    ]
    for stunde in plan.get("stunden", []):
        vevent = stunde_zu_vevent(stunde, ferien["schuljahr"], frei, tz, stempel)
        if vevent:
            zeilen.extend(vevent)
    zeilen.append("END:VCALENDAR")
    return "\r\n".join(falten(z) for z in zeilen) + "\r\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("plan", nargs="?", default=HIER / "stundenplan.yaml")
    parser.add_argument("-o", "--ausgabe", default=HIER / "out" / "stundenplan.ics")
    args = parser.parse_args()

    ausgabe = Path(args.ausgabe)
    ausgabe.parent.mkdir(parents=True, exist_ok=True)
    ausgabe.write_text(erzeuge_ics(args.plan), encoding="utf-8", newline="")
    print(f"Geschrieben: {ausgabe}")


if __name__ == "__main__":
    main()
