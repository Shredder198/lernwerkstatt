# Kalender

Termine als Kalender-Abo für iPhone, Mac, Outlook und Google. Die Daten
stehen in einfachen YAML-Dateien, daraus baut GitHub automatisch
`.ics`-Dateien. Ein abonnierter Kalender aktualisiert sich von selbst.

| Kalender | Daten | Abo-Link |
|---|---|---|
| IFEN-Weiterbildungen 2026/27 | [`ifen.yaml`](ifen.yaml) | `https://shredder198.github.io/lernwerkstatt/kalender/out/ifen.ics` |

Falls der Link oben nicht lädt (GitHub Pages aus), geht auch:
`https://raw.githubusercontent.com/Shredder198/lernwerkstatt/main/kalender/out/ifen.ics`

## Abonnieren

Wichtig: **abonnieren**, nicht importieren. Nur ein Abo holt sich spätere
Änderungen.

### iPhone / iPad
1. Einstellungen → Kalender → Accounts → Account hinzufügen → Andere
2. „Kalenderabo hinzufügen“ → Abo-Link einfügen → Weiter → Sichern

Oder den Link mit `webcal://` statt `https://` in Safari öffnen.

### Mac (Kalender-App)
1. Ablage → Neues Kalenderabonnement …
2. Abo-Link einfügen → Abonnieren
3. „Aktualisieren“ auf „Jede Stunde“ oder „Jeden Tag“ stellen, Ort „iCloud“
   wählen, damit es auch auf dem iPhone erscheint.

### Outlook
- **Outlook im Web / neues Outlook:** Kalender → Kalender hinzufügen →
  Aus dem Internet abonnieren → Link einfügen → Importieren.
- **Klassisches Outlook (Windows):** Kalender → Kalender hinzufügen →
  Aus dem Internet … → Link einfügen → OK.
- **Outlook für Mac:** am einfachsten über Outlook im Web abonnieren; der
  Kalender erscheint dann auch in der App.

Outlook aktualisiert Abos nur alle paar Stunden.

### Google Kalender
1. Am Computer [calendar.google.com](https://calendar.google.com) öffnen
2. Links bei „Weitere Kalender“ auf **+** → „Per URL“
3. Abo-Link einfügen → Kalender hinzufügen

Google aktualisiert Abos nur etwa alle 12–24 Stunden. Am Handy erscheint
der Kalender danach in der Google-Kalender-App (ggf. unter Einstellungen
einblenden).

## Termine ändern

1. `ifen.yaml` bearbeiten (geht auch direkt auf github.com über den Stift).
2. Speichern / committen auf `main`.
3. Die Action „Kalender bauen“ erzeugt `out/ifen.ics` neu. Fertig.

Termine mit `status: vorschlag` oder `status: offen` erscheinen mit „?“
im Titel und als vorläufig. Ist ein Termin bestätigt, `status` löschen
oder auf `bestaetigt` setzen.

Lokal testen: `pip install pyyaml && python3 kalender/ifen.py`

## Technik

- Zeitzone aller Termine: Europe/Luxembourg.
- Jedes Skript `kalender/*.py` wird von der Action ohne Argumente aus dem
  Repo-Wurzelordner aufgerufen und schreibt nach `kalender/out/`.
- Die UID eines Termins hängt an Titel, Kurs und Datum. Ändert sich nur
  Uhrzeit oder Ort, bleibt es im Kalender derselbe Termin.
