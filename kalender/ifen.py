#!/usr/bin/env python3
"""Baut aus kalender/ifen.yaml die Kalenderdatei kalender/out/ifen.ics.

Aufruf:  python3 kalender/ifen.py [ifen.yaml] [ausgabe.ics]

Die UID jedes Termins hängt nur von Titel, Kurs und Datum ab. So bleibt
ein Termin in abonnierten Kalendern derselbe, wenn sich z. B. nur die
Uhrzeit oder der Ort ändert.
"""
import hashlib
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent

# Europe/Luxembourg: MEZ/MESZ, Umstellung letzter Sonntag im März/Oktober.
VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Luxembourg
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


def text(wert):
    """Escaping nach RFC 5545 für TEXT-Werte."""
    return (str(wert).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def falten(zeile):
    """Zeilen über 75 Bytes umbrechen (RFC 5545, 3.1)."""
    roh = zeile.encode("utf-8")
    if len(roh) <= 75:
        return zeile
    teile, start = [], 0
    grenze = 75
    while start < len(roh):
        ende = min(start + grenze, len(roh))
        # nicht mitten in einem UTF-8-Zeichen trennen
        while ende < len(roh) and (roh[ende] & 0xC0) == 0x80:
            ende -= 1
        teile.append(roh[start:ende].decode("utf-8"))
        start, grenze = ende, 74  # Folgezeilen beginnen mit Leerzeichen
    return "\r\n ".join(teile)


def als_datum(wert):
    return wert if isinstance(wert, date) else date.fromisoformat(str(wert))


def als_zeit(tag, hhmm):
    h, m = str(hhmm).split(":")
    return datetime(tag.year, tag.month, tag.day, int(h), int(m))


def termin_ics(t, tz, stempel):
    for feld in ("titel", "datum"):
        if not t.get(feld):
            raise ValueError(f"Termin ohne '{feld}': {t}")
    tag = als_datum(t["datum"])
    status = t.get("status", "bestaetigt")
    vorlaeufig = status in ("vorschlag", "offen")

    titel = t["titel"]
    if t.get("kurs"):
        titel = f"{titel} – {t['kurs']}"
    titel = f"IFEN: {titel}"
    if vorlaeufig:
        titel = f"? {titel}"

    uid_quelle = f"{t['titel']}|{t.get('kurs', '')}|{tag.isoformat()}"
    uid = hashlib.sha1(uid_quelle.encode("utf-8")).hexdigest()[:16]

    z = ["BEGIN:VEVENT",
         f"UID:{uid}@lernwerkstatt-kalender",
         f"DTSTAMP:{stempel}",
         f"SUMMARY:{text(titel)}"]
    if t.get("beginn"):
        beginn = als_zeit(tag, t["beginn"])
        ende = als_zeit(tag, t["ende"]) if t.get("ende") else beginn + timedelta(hours=1)
        z.append(f"DTSTART;TZID={tz}:{beginn:%Y%m%dT%H%M%S}")
        z.append(f"DTEND;TZID={tz}:{ende:%Y%m%dT%H%M%S}")
    else:
        z.append(f"DTSTART;VALUE=DATE:{tag:%Y%m%d}")
        z.append(f"DTEND;VALUE=DATE:{tag + timedelta(days=1):%Y%m%d}")
    if t.get("ort"):
        z.append(f"LOCATION:{text(t['ort'])}")

    beschreibung = []
    if t.get("kurs"):
        beschreibung.append(f"Kurs: {t['kurs']}")
    if vorlaeufig:
        beschreibung.append("Status: " + ("Vorschlag, noch nicht bestätigt"
                                          if status == "vorschlag" else "Termin noch offen"))
    if t.get("notiz"):
        beschreibung.append(str(t["notiz"]))
    if beschreibung:
        z.append(f"DESCRIPTION:{text(chr(10).join(beschreibung))}")
    z.append("STATUS:TENTATIVE" if vorlaeufig else "STATUS:CONFIRMED")
    z.append("TRANSP:OPAQUE")
    z.append("END:VEVENT")
    return z


def bauen(daten):
    tz = daten.get("zeitzone", "Europe/Luxembourg")
    if tz != "Europe/Luxembourg":
        raise ValueError("Nur Europe/Luxembourg wird unterstützt.")
    name = daten.get("kalendername", "IFEN Weiterbildungen")
    stempel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    zeilen = ["BEGIN:VCALENDAR",
              "VERSION:2.0",
              "PRODID:-//lernwerkstatt//IFEN-Kalender//DE",
              "CALSCALE:GREGORIAN",
              "METHOD:PUBLISH",
              f"X-WR-CALNAME:{text(name)}",
              f"X-WR-TIMEZONE:{tz}",
              "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
              "X-PUBLISHED-TTL:PT12H"]
    zeilen += VTIMEZONE.splitlines()
    termine = sorted(daten.get("termine") or [],
                     key=lambda t: (str(t.get("datum")), str(t.get("beginn", ""))))
    for t in termine:
        zeilen += termin_ics(t, tz, stempel)
    zeilen.append("END:VCALENDAR")
    return "\r\n".join(falten(z) for z in zeilen) + "\r\n", len(termine)


def main():
    quelle = Path(sys.argv[1]) if len(sys.argv) > 1 else HIER / "ifen.yaml"
    ziel = Path(sys.argv[2]) if len(sys.argv) > 2 else HIER / "out" / "ifen.ics"
    daten = yaml.safe_load(quelle.read_text(encoding="utf-8")) or {}
    inhalt, anzahl = bauen(daten)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(inhalt.encode("utf-8"))
    print(f"{anzahl} Termine -> {ziel}")


if __name__ == "__main__":
    main()
