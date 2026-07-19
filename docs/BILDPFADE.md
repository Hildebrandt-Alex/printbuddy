# PrintBuddy — Bildpfad-Dokumentation

## Problem: "Bilder werden nicht angezeigt"

**Root Cause:** Django speichert Bilder an 2 verschiedenen Orten:
1. **Lokal** (`/opt/printbuddy/media/`) → für Uploads (Referenzbilder)
2. **NAS** (`/mnt/agency_nas/`) → für generierte Bilder (GPU-Output)

Nginx muss BEIDE Pfade servieren!

---

## ✅ RICHTIGE NGINX-KONFIGURATION

```nginx
location /media/ {
    alias /opt/printbuddy/media/;   # Lokale Uploads
    expires 7d;
}

location /nas/ {
    alias /mnt/agency_nas/;         # Generierte Bilder
    expires 30d;
}
```

**Datei:** `/etc/nginx/sites-enabled/printbuddy`

---

## ✅ RICHTIGE TEMPLATE-LOGIK

### Regel:
- **Pfad enthält `exports/`** → kommt vom NAS → `/nas/{{ path }}`
- **Sonst** → lokaler Upload → `{{ ImageField.url }}`

### Studio job_results.html
```django
<!-- IMMER NAS (Preview-Exports liegen immer auf NAS) -->
<img src="/nas/exports/preview/{{ asset.filename }}">
```

### Gallery list.html & detail.html
```django
{% if 'exports/' in image.file_path.name %}
  <img src="/nas/{{ image.file_path.name }}">  <!-- NAS -->
{% else %}
  <img src="{{ image.file_path.url }}">        <!-- /media/ -->
{% endif %}
```

---

## 📂 DATEI-STRUKTUREN

### NAS (`/mnt/agency_nas/`)
```
raw/                      ← GPU-Roh-Outputs (vollaufgelöst)
exports/
  preview/                ← JPG 72dpi für Studio/Gallery
  pod/                    ← PNG 300dpi sRGB (Printful-ready)
  offset/                 ← CMYK TIFF + PDF/X-4
  vector/                 ← SVG
gallery/                  ← (deprecated - nicht mehr nutzen)
bundles/                  ← ZIP-Druckdatei-Bundles
```

### Lokal (`/opt/printbuddy/media/`)
```
jobs/refs/                ← Referenzbilder für Img2Img
gallery/full/             ← (deprecated - nicht mehr nutzen)
gallery/thumbs/           ← (deprecated - nicht mehr nutzen)
```

---

## 🐛 DEBUGGING CHECKLISTE

Wenn Bilder nicht angezeigt werden:

### 1. Nginx-Routes prüfen
```bash
ssh datemyhobby "cat /etc/nginx/sites-enabled/printbuddy | grep -A 3 'location /'"
```
**Erwartung:** Beide `/media/` und `/nas/` Locations vorhanden

### 2. Nginx-Reload nach Config-Änderung
```bash
ssh datemyhobby "sudo nginx -t && sudo systemctl reload nginx"
```

### 3. Dateiberechtigungen prüfen
```bash
# NAS-Dateien müssen von www-data lesbar sein
ssh datemyhobby "ls -lh /mnt/agency_nas/exports/preview/ | tail -5"

# Erwartung: -rw-r--r-- (644) oder besser
```

### 4. URL manuell testen
```bash
# NAS-Bild (Preview)
curl -I https://printbuddy.datemyhobby.com/nas/exports/preview/<uuid>_preview.jpg

# Lokales Bild (Referenz)
curl -I https://printbuddy.datemyhobby.com/media/jobs/refs/<uuid>.png

# Erwartung: HTTP/1.1 200 OK
```

### 5. Django Template Variablen debuggen
Im Template hinzufügen:
```django
<!-- DEBUG: {{ image.file_path.name }} -->
```
Browser → Quelltext anzeigen → Pfad prüfen

---

## 🔄 TYPISCHE FEHLERQUELLEN

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| Alle Bilder schwarz/nicht sichtbar | Nginx `/nas/` Route fehlt | Nginx-Config ergänzen + reload |
| Gallery-Bilder fehlen, Studio OK | Template verwendet `.url` statt `/nas/` | Template-Logik korrigieren |
| Einzelne Bilder fehlen | Datei existiert nicht auf NAS | Job neu laufen lassen |
| 404 Not Found | MEDIA_URL_EXTERNAL falsch | Muss `printbuddy.datemyhobby.com` sein |
| 500 Server Error beim Vormerken | `job.project` ist None | `getattr(job, 'project', None)` verwenden |

---

## 📝 NACH JEDER ÄNDERUNG TESTEN

```bash
# 1. Lokal committen
git add .
git commit -m "fix: [Beschreibung]"
git push

# 2. Auf VPS deployen
ssh datemyhobby 'bash /opt/printbuddy/deploy.sh'

# 3. Celery neu starten (wenn gpu/tasks.py geändert)
ssh datemyhobby 'sudo systemctl restart celery-printbuddy-gpu celery-printbuddy-cpu'

# 4. Im Browser testen:
- Studio Job Results: https://printbuddy.datemyhobby.com/studio/jobs/
- Gallery: https://printbuddy.datemyhobby.com/gallery/
- Bild mit F12 inspizieren → Network Tab → ist Request 200 oder 404?
```

---

## ⚠️ NIEMALS ÄNDERN OHNE TEST

**Diese Dateien niemals editieren ohne sofort zu testen:**

1. `/etc/nginx/sites-enabled/printbuddy` - Nginx-Config
2. `templates/studio/job_results.html` - Studio Bildanzeige
3. `templates/gallery/list.html` - Gallery Grid
4. `templates/gallery/detail.html` - Gallery Detail
5. `studio/views.py`: `asset_select()` - Gallery-Vormerken
6. `.env` auf VPS - MEDIA_URL_EXTERNAL

**Test-Reihenfolge:**
1. Job erstellen → Results anzeigen (Studio)
2. Für Galerie vormerken
3. Gallery öffnen (öffentlich + Admin-Login)
4. Browser DevTools → Network Tab → alle img Requests 200 OK?

---

## 🎯 QUICK REFERENCE

| Was | Wo | Nginx-Route | Template-Syntax |
|-----|-----|-------------|-----------------|
| GPU-generierte Previews | NAS `/mnt/agency_nas/exports/preview/` | `/nas/` | `/nas/exports/preview/{{ filename }}` |
| Img2Img Referenzbilder | Lokal `/opt/printbuddy/media/jobs/refs/` | `/media/` | `{{ reference_image.url }}` |
| Gallery-Bilder (alt) | Lokal `/opt/printbuddy/media/gallery/` | `/media/` | `{{ file_path.url }}` |
| Gallery-Bilder (neu) | NAS `/mnt/agency_nas/exports/preview/` | `/nas/` | `/nas/{{ file_path.name }}` |

---

**Erstellt:** 2026-07-19
**Letztes Update:** Nach Bugfix Session (Bildpfade Studio + Gallery)
