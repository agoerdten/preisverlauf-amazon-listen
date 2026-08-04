# Preisverlauf-Tracker für Amazon.de Listen

Verfolgt täglich automatisch den Preis von Produkten aus Amazon.de-Listen ("Meine Listen")
und/oder einzelnen Produktlinks — unabhängig davon, ob dein PC läuft. Ein GitHub-Actions-Job
ruft die Seiten täglich ab, speichert die Preise als JSON-Dateien im Repo, und ein kleines
Dashboard (GitHub Pages) zeigt den Verlauf als Diagramm.

## Einrichtung

1. **Amazon-Liste teilen** (falls du eine Liste tracken willst): Öffne deine Liste unter
   "Meine Listen" bei Amazon.de, stelle sie über die Teilen-Funktion auf "öffentlich/über Link
   sichtbar" und kopiere den Link.
2. **`config/tracking.json` befüllen**: Trage die Listen-URL(s) unter `"lists"` und/oder
   einzelne Produktlinks unter `"products"` ein, z. B.:
   ```json
   {
     "lists": ["https://www.amazon.de/hz/wishlist/ls/DEIN-LINK"],
     "products": ["https://www.amazon.de/dp/B0XXXXXXXX"]
   }
   ```
3. **GitHub-Repository anlegen** und diesen Ordner hineinpushen (siehe unten).
4. **GitHub Pages aktivieren**: Repo-Einstellungen → Pages → Branch `main`, Ordner `/docs`.
5. **Actions-Schreibrechte aktivieren**: Repo-Einstellungen → Actions → General →
   Workflow permissions → "Read and write permissions".
6. Den Workflow einmal manuell auslösen (Tab "Actions" → "Preise abrufen" → "Run workflow"),
   um den ersten Datenpunkt zu erzeugen.

## Lokal testen

```
cd scraper
pip install -r requirements.txt
python scrape.py
```

Danach in `docs/data/products/` prüfen, ob die erwarteten JSON-Dateien mit plausiblen
Preisen entstanden sind.

## Bekannte offene Punkte

- Die Selektoren für das Auslesen von Amazon-**Listen**-Seiten (`extract_products_from_list_page`
  in `scraper/scrape.py`) sind ein erster Versuch und noch nicht gegen eine echte, öffentlich
  geteilte Liste geprüft — vor dem produktiven Einsatz einmal lokal gegen die eigene Liste testen.
- Falls Amazon Cloud-IPs (GitHub-Runner) blockiert: siehe Plan-Dokument, Abschnitt
  "Anti-Bot-Risiko" für Gegenmaßnahmen.
