# PrintBuddy — Bildpfad-Dokumentation (PROD-verifiziert)

## Problem: "Bilder werden nicht angezeigt"

**Root Cause:** Bilder werden auf dem **NAS-Homeserver** gespeichert (Speicherplatz!), nicht lokal auf VPS.  
Nginx serviert diese über `/nas/jobs/` Route.

---

## ✅ PROD NGINX-KONFIGURATION

```nginx
# Lokale Django-Uploads (Referenzbilder, Face Swap Portraits)
location /media/ {
    alias /opt/printbuddy/media/;
    expires 7d;
}

# NAS Jobs (GPU-generierte Bilder, Quick Adjust)
location /media/jobs/ {
    alias /mnt/agency_nas/jobs/;   # ← LEGACY Route (funktioniert aber)
    expires 7d;
}

# NAS Root (komplettes NAS)
location /nas/ {
    alias /mnt/agency_nas/;         # ← BEVORZUGTE Route
    expires 30d;
}

# Protected Bundles (nur für Partner via Django Auth)
location /protected-bundles/ {
    internal;
    alias /mnt/agency_nas/bundles/;
}
```

**Datei:** `/etc/nginx/sites-enabled/printbuddy`  
**URLs funktionieren BEIDE:** `/media/jobs/...` UND `/nas/jobs/...` → **verwende einheitlich `/nas/jobs/`**

---

## 📂 ECHTE PROD-STRUKTUR (NAS Homeserver)

### Physischer Pfad: `/mnt/agency_nas/`

```
/mnt/agency_nas/
├── jobs/                    ← GPU-generierte Bilder (JOB-basiert)
│   └── {job_id}/            ← UUID des Jobs
│       ├── original/        ← GPU-Roh-Output (PNG, vollaufgelöst)
│       │   └── {asset_uuid}.png
│       ├── adjusted/        ← DEPRECATED (Quick Adjust nutzt exports/preview/)
│       └── exports/         ← Finale Exports für Produktion
│           ├── preview/     ← JPG 72dpi (Studio + Gallery)
│           │   ├── {asset_uuid}_preview.jpg
│           │   └── {asset_uuid}_adjusted_{timestamp}.jpg
│           ├── pod/         ← PNG 300dpi sRGB (Printful Print-on-Demand)
│           ├── offset/      ← CMYK TIFF + PDF/X-4 (Offsetdruck)
│           └── vector/      ← SVG (Vektorisierung)
│
├── raw/                     ← DEPRECATED (alte GPU-Outputs ohne Job-Struktur)
├── exports/                 ← DEPRECATED (alte flache Struktur)
├── gallery/                 ← DEPRECATED (galerie/{full|thumbs}/)
├── bundles/                 ← ZIP-Druckdateien für Partner-Download
└── backups/                 ← Postgres Dumps + Media Backups

```

**URL-Zugriff:**
- Preview: `https://printbuddy.datemyhobby.com/nas/jobs/{job_id}/exports/preview/{asset_uuid}_preview.jpg`
- POD: `https://printbuddy.datemyhobby.com/nas/jobs/{job_id}/exports/pod/{asset_uuid}_pod.png`

---

## 📁 LOKALE VPS-STRUKTUR

### Physischer Pfad: `/opt/printbuddy/media/`

```
/opt/printbuddy/media/
└── jobs/
    └── refs/                ← Referenzbilder für Img2Img (User-Uploads)
        └── {uuid}.png
```

**URL-Zugriff:**
- Referenzbild: `https://printbuddy.datemyhobby.com/media/jobs/refs/{uuid}.png`

---

## ✅ RICHTIGE TEMPLATE-LOGIK

### Studio job_results.html (Generated Assets)
```django
<!-- GPU-generierte Previews: IMMER /nas/jobs/ -->
<img src="/nas/jobs/{{ job.id }}/exports/preview/{{ asset.filename }}">
```

### Gallery list.html & detail.html
```django
{% if 'exports/' in image.file_path.name %}
  <!-- NAS Export -->
  <img src="/nas/{{ image.file_path.name }}">
{% else %}
  <!-- Lokaler Upload -->
  <img src="{{ image.file_path.url }}">
{% endif %}
```

### Product Wizard (Image Selection)
```python
# studio/views.py
assets.append({
    "url": f"/nas/jobs/{job.id}/exports/preview/{filename}",
})
```

---

## 🐛 DEBUGGING CHECKLISTE

Wenn Bilder nicht angezeigt werden:

### 1. Nginx-Routes prüfen
```bash
ssh datemyhobby "grep -E 'location.*/media|location.*/nas' /etc/nginx/sites-enabled/printbuddy -A 3"
```
**Erwartung:** `/media/`, `/media/jobs/`, `/nas/` Locations vorhanden

### 2. Dateien auf NAS prüfen
```bash
# Beispiel-Job prüfen
ssh datemyhobby "ls -lh /mnt/agency_nas/jobs/ | head -5"
# Preview-Dateien eines Jobs
ssh datemyhobby "find /mnt/agency_nas/jobs/{JOB_UUID}/exports/preview/ -type f"
```
**Erwartung:** `.jpg` Dateien vorhanden, Rechte `-rw-r--r--` (644)

### 3. URL manuell testen
```bash
# NAS Preview (bevorzugte Route)
curl -I https://printbuddy.datemyhobby.com/nas/jobs/{job_id}/exports/preview/{uuid}_preview.jpg

# Legacy Route (funktioniert auch)
curl -I https://printbuddy.datemyhobby.com/media/jobs/{job_id}/exports/preview/{uuid}_preview.jpg

# Erwartung: HTTP/1.1 200 OK, Content-Type: image/jpeg
```

### 4. Browser DevTools
```
F12 → Network Tab → Reload
Filtern nach "jpg" oder "png"
Status-Code prüfen:
  - 200 OK ✅
  - 404 Not Found ❌ → Datei fehlt auf NAS
  - 403 Forbidden ❌ → Nginx-Rechte prüfen
```

### 5. Django Template debuggen
Im Template hinzufügen:
```django
<!-- DEBUG: {{ asset.url }} -->
<!-- DEBUG Physical Path: /mnt/agency_nas/jobs/{{ job.id }}/exports/preview/{{ asset.filename }} -->
```
Browser → Quelltext (Rechtsklick → View Source) → Pfad kontrollieren

---

## 🔄 TYPISCHE FEHLERQUELLEN

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| Alle Bilder 404 | Nginx `/nas/` Route fehlt | Nginx-Config hinzufügen + reload |
| Canvas schwarz (Quick Adjust) | JS-Selector falsch | `.card img[src*="/nas/jobs/"]` verwenden |
| Einzelne Bilder fehlen | Datei existiert nicht | Job neu generieren lassen |
| Bilder nach Deploy weg | Pfad inkonsistent | Alle URLs auf `/nas/jobs/` umstellen |
| 403 Forbidden | NAS-Mount nicht aktiv | `ls /mnt/agency_nas/` testen |

---

## 📝 DEPLOYMENT CHECKLIST

Nach Code-Änderungen die Bildpfade betreffen:

```bash
# 1. Lokal committen
git add .
git commit -m "fix: Bildpfade /nas/jobs/ vereinheitlicht"
git push

# 2. VPS Deploy
ssh datemyhobby 'cd /opt/printbuddy && git pull && sudo systemctl restart gunicorn.printbuddy'

# 3. Nginx-Config geändert? (nur bei Änderungen an nginx-printbuddy.conf)
scp nginx-printbuddy.conf datemyhobby:/tmp/
ssh datemyhobby 'sudo cp /tmp/nginx-printbuddy.conf /etc/nginx/sites-enabled/printbuddy && sudo nginx -t && sudo systemctl reload nginx'

# 4. Browser-Test (CTRL+F5 für Cache-Bypass)
- Studio Job Results öffnen
- Quick Adjust testen
- Gallery öffnen
- DevTools Network Tab: Alle Bild-Requests 200 OK?
```

**WICHTIG:** Celery restart nur bei Änderungen an `gpu/tasks.py` oder `postprocess/tasks.py`!

---

## 🎯 QUICK REFERENCE

| Was | Physischer Pfad | Nginx-Route | URL-Präfix | Template-Code |
|-----|----------------|-------------|------------|---------------|
| **GPU Preview** | `/mnt/agency_nas/jobs/{job_id}/exports/preview/` | `/nas/` | `/nas/jobs/...` | `/nas/jobs/{{ job.id }}/exports/preview/{{ filename }}` |
| **Quick Adjust** | `/mnt/agency_nas/jobs/{job_id}/exports/preview/` | `/nas/` | `/nas/jobs/...` | `/nas/jobs/{{ job.id }}/exports/preview/{{ filename }}` |
| **POD Export** | `/mnt/agency_nas/jobs/{job_id}/exports/pod/` | `/nas/` | `/nas/jobs/...` | `/nas/jobs/{{ job.id }}/exports/pod/{{ filename }}` |
| **Referenzbild** | `/opt/printbuddy/media/jobs/refs/` | `/media/` | `/media/jobs/refs/...` | `{{ reference_image.url }}` |
| **Bundle** | `/mnt/agency_nas/bundles/` | `/protected-bundles/` | (intern) | X-Accel-Redirect |

---

## ⚠️ MIGRATION VON ALT → NEU

### Alte (deprecated) Pfade:
- `/mnt/agency_nas/raw/` → jetzt `/mnt/agency_nas/jobs/{job_id}/original/`
- `/mnt/agency_nas/exports/preview/` → jetzt `/mnt/agency_nas/jobs/{job_id}/exports/preview/`
- `/mnt/agency_nas/jobs/{job_id}/adjusted/` → jetzt `/mnt/agency_nas/jobs/{job_id}/exports/preview/`

**Keine Migration nötig!** Neue Jobs verwenden automatisch neue Struktur.

---

**Erstellt:** 2026-07-19  
**Letztes Update:** 2026-08-18 (Prod-Pfade verifiziert, `/nas/jobs/` standardisiert)
