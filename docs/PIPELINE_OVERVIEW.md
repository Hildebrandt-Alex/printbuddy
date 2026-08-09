# PrintBuddy Pipeline-Übersicht (Stand: August 2026)

## 🔧 Verfügbare GPU-Tasks (RunPod)

### 1. **generate_image** (GPU Queue)
- **Status:** ✅ Implementiert und funktionsfähig
- **Modelle:**
  - FLUX Schnell (primary) - Apache 2.0 ✅ kommerziell
  - FLUX Dev - NICHT für Verkauf ❌
  - SDXL - kommerziell OK ✅
- **Endpoint:** `RUNPOD_ENDPOINT_ID` (FLUX) / `RUNPOD_SDXL_ENDPOINT_ID` (SDXL)
- **Output:** PNG in `/mnt/agency_nas/raw/{uuid}.png`
- **Fallback:** Vast.ai (wenn RunPod fehlschlägt)
- **Mock-Modus:** `MOCK_GPU=true` für lokale Tests

### 2. **upscale_image** (GPU Queue)
- **Status:** ✅ Implementiert (Real-ESRGAN 4x)
- **Endpoint:** `RUNPOD_UPSCALE_ENDPOINT`
- **Skalierung:** 4x (1024x1024 → 4096x4096)
- **Output:** PNG in `/mnt/agency_nas/raw/{uuid}_4x.png`
- **Methode:** Real-ESRGAN via RunPod

### 3. **face_swap_image** (GPU Queue)
- **Status:** ✅ Implementiert aber DEAKTIVIERT
- **Funktion:** InsightFace - Gesichtsübertragung
- **Benötigt:** `job.reference_image` (Referenzgesicht)
- **Output:** PNG in `/mnt/agency_nas/raw/{uuid}_faceswap.png`
- **Hinweis:** Im aktuellen MVP nicht in Pipeline aktiv

---

## 🖥️ CPU Post-Processing Tasks

### 4. **pod_export** (CPU Queue)
- **Status:** ✅ Aktiv in Standard-Pipeline
- **Funktion:** PNG 300dpi sRGB für Print-on-Demand
- **Output:** `/mnt/agency_nas/exports/pod/{uuid}_pod.png`
- **Verwendung:** Printful, Merch-Production

### 5. **preview_export** (CPU Queue)
- **Status:** ✅ Aktiv in Standard-Pipeline (PFLICHT)
- **Funktion:** JPG 72dpi max 1200px für Web-Galerie
- **Output:** `/mnt/agency_nas/exports/preview/{uuid}_preview.jpg`
- **Verwendung:** Galerie Landing Page, Studio-Preview

### 6. **cmyk_export** (CPU Queue)
- **Status:** ✅ Implementiert, OPTIONAL
- **Funktion:** CMYK TIFF + PDF/X-4 für Offset-Druck
- **Output:** `/mnt/agency_nas/exports/offset/{uuid}_cmyk.tif` + `.pdf`
- **Tools:** Pillow + Ghostscript
- **Verwendung:** Professioneller Druck (große Auflagen)

### 7. **vectorize_image** (CPU Queue)
- **Status:** ✅ Implementiert, OPTIONAL
- **Funktion:** Bitmap → Vektor (SVG)
- **Output:** `/mnt/agency_nas/exports/vector/{uuid}_vector.svg`
- **Tools:** Inkscape CLI + Potrace
- **Verwendung:** Logos, Icon-Design

### 8. **mockup_gen** (CPU Queue)
- **Status:** ✅ Implementiert, OPTIONAL
- **Funktion:** Printful Mockup API (Produktvorschau)
- **Output:** Mockup-Bilder für Shop
- **Verwendung:** E-Commerce Produktbilder

### 9. **auto_qa** (CPU Queue)
- **Status:** ✅ Implementiert, OPTIONAL
- **Funktion:** CLIP-Score + Blur-Detection
- **Output:** Quality-Score in DB
- **Verwendung:** Automatische Qualitätsprüfung

---

## 📋 Definierte Pipeline-Templates (PipelineTemplate Model)

### A. **Standard FLUX Schnell** (aktuell auf Production)
```
Pipeline:
  generate_image (FLUX Schnell, 1024x1024, 4 Steps)
  → pod_export
  → preview_export (PFLICHT)

Steps aktiviert:
  ✅ step_generate
  ✅ step_pod_export
  ✅ step_preview
  ❌ step_upscale (deaktiviert für MVP)
  ❌ alle anderen

Verwendung: Basis-Workflow für kommerzielle AI-Art
Lizenz: Apache 2.0 ✅
```

### B. **High-Quality Print** (konfigurierbar)
```
Pipeline:
  generate_image
  → upscale_image (4x)
  → pod_export
  → cmyk_export
  → preview_export

Steps:
  ✅ step_generate
  ✅ step_upscale
  ✅ step_pod_export
  ✅ step_cmyk
  ✅ step_preview

Verwendung: Große Poster, professioneller Druck
Kosten: Höher (Upscaling)
```

### C. **Vector Art Pipeline** (konfigurierbar)
```
Pipeline:
  generate_image
  → vectorize_image
  → preview_export

Steps:
  ✅ step_generate
  ✅ step_vectorize
  ✅ step_preview

Verwendung: Logos, Icons, Vektorgrafiken
Limitierung: Funktioniert besser mit einfachen Motiven
```

### D. **E-Commerce Complete** (konfigurierbar)
```
Pipeline:
  generate_image
  → upscale_image
  → pod_export
  → mockup_gen
  → preview_export

Steps:
  ✅ step_generate
  ✅ step_upscale
  ✅ step_pod_export
  ✅ step_mockup
  ✅ step_preview

Verwendung: Shop-ready mit Mockups
Benötigt: Printful API Integration
```

### E. **Face Swap Portrait** (implementiert aber inaktiv)
```
Pipeline:
  generate_image
  → face_swap_image
  → upscale_image
  → pod_export
  → preview_export

Steps:
  ✅ step_generate
  ✅ step_face_swap
  ✅ step_upscale
  ✅ step_pod_export
  ✅ step_preview

Verwendung: Portrait-Art mit Gesichtsübertragung
Status: Deaktiviert im aktuellen MVP
```

---

## 🎯 Frontend-Integration: Zwei Optionen

### **Option 1: Pipeline-Typen (Empfohlen für MVP)**
**Nutzer wählt Verwendungszweck → Pipeline automatisch zugewiesen**

```
Frontend-Flow:
1. "Wofür brauchst du das Bild?"
   → [ ] Merchandise (T-Shirts, Tassen)
   → [ ] Poster (hochaufgelöst)
   → [ ] Web-Galerie
   → [ ] Professioneller Druck
   → [ ] Logo/Vektor

2. Backend ordnet automatisch Pipeline zu:
   - Merchandise    → Standard FLUX (kein Upscale)
   - Poster         → High-Quality Print (mit Upscale)
   - Web            → Standard FLUX
   - Profi-Druck    → High-Quality + CMYK
   - Logo           → Vector Art Pipeline
```

**Vorteile:**
- ✅ Einfach für Nutzer (keine technischen Details)
- ✅ Backend optimiert automatisch (Kosten/Qualität)
- ✅ Leichter zu erweitern

**Nachteile:**
- ⚠️ Weniger Kontrolle für Power-User

---

### **Option 2: Detaillierte Pipeline-Optionen**
**Nutzer konfiguriert Pipeline-Steps selbst**

```
Frontend-Flow:
1. Basis-Generation
   Modell: [FLUX Schnell ▼] [SDXL] [FLUX Dev]
   Größe: 1024x1024
   Steps: 4 (FLUX) / 30 (SDXL)

2. Post-Processing (Checkboxen):
   □ Hochskalieren auf 4096x4096 (+GPU Zeit, +Kosten)
   □ Professioneller Druck (CMYK Export)
   □ Als Vektor exportieren (SVG)
   □ Produkt-Mockups erstellen

3. Preview
   ☑ Galerie-Preview (IMMER aktiv)
```

**Vorteile:**
- ✅ Volle Kontrolle für erfahrene Nutzer
- ✅ Transparent (User sieht was läuft)

**Nachteile:**
- ⚠️ Komplexer für Anfänger
- ⚠️ Mehr UI-Elemente

---

## 💰 Kosten-Übersicht (geschätzt)

| Task | GPU/CPU | Dauer | Kosten/Job | Wann verwenden? |
|------|---------|-------|------------|-----------------|
| generate_image (FLUX) | GPU | ~5-10s | $0.02 | IMMER |
| generate_image (SDXL) | GPU | ~20-30s | $0.05 | Bessere Qualität |
| upscale_image (4x) | GPU | ~15-25s | $0.08 | Große Drucke, Poster |
| face_swap | GPU | ~10-15s | $0.04 | Portrait-Art |
| pod_export | CPU | ~2s | $0.00 | IMMER (Merch) |
| preview_export | CPU | ~1s | $0.00 | IMMER (Web) |
| cmyk_export | CPU | ~5s | $0.00 | Offset-Druck |
| vectorize | CPU | ~8-12s | $0.00 | Logos/Icons |
| mockup_gen | API | ~5-10s | $0.01 | E-Commerce |

**MVP-Empfehlung:**
- Standard Pipeline: $0.02 (nur generate + exports)
- Mit Upscaling: $0.10 (generate + upscale + exports)

---

## 🚦 Empfehlung für MVP

### **Kombination aus Option 1 + vereinfachter Option 2:**

```python
# Frontend: Wizard mit 3 Schritten

# Schritt 1: Media Type (wie jetzt)
- Bild
- 3D-Objekt (später)

# Schritt 2: Qualitätsstufe (NEU)
○ Standard (schnell, günstig) 
  → FLUX Schnell, kein Upscale
  Dauer: ~10s | Kosten: ~$0.02
  
○ High Quality (langsamer, besser) 
  → FLUX Schnell + 4x Upscale
  Dauer: ~40s | Kosten: ~$0.10
  
○ Profi-Druck (CMYK + Upscale)
  → FLUX Schnell + Upscale + CMYK Export
  Dauer: ~50s | Kosten: ~$0.10

# Schritt 3: Details (wie jetzt)
- Prompt, Projekt, etc.
```

**Technische Umsetzung:**
- 3 PipelineTemplates im Admin anlegen
- Frontend schickt `pipeline_template_id` basierend auf Qualitätsstufe
- Keine einzelne Step-Konfiguration durch User

---

## 📦 Nächste Schritte

1. **PostgreSQL lokal installieren** (kommt gleich)
2. **3 Pipeline-Templates anlegen:**
   - Standard (MVP aktiv)
   - High Quality (mit Upscale)
   - Profi-Druck (mit Upscale + CMYK)
3. **Frontend erweitern:**
   - Quality-Selector im Wizard
   - Kosten-/Dauer-Anzeige
4. **Admin-Integration:**
   - Pipeline-Templates verwalten
   - Kosten-Monitoring

---

## ❓ Entscheidungsfragen

1. **Quality-Selector jetzt oder später?**
   - Jetzt: User kann High-Quality wählen (+ Upscale)
   - Später: Erst mal nur Standard-Pipeline testen

2. **Face Swap aktivieren?**
   - Nein: Im MVP weglassen (kompliziert)
   - Ja: Als "Portrait Art" Option

3. **Kosten transparent zeigen?**
   - Ja: "Standard (~$0.02) | High Quality (~$0.10)"
   - Nein: Intern tracken, User sieht nichts

**Meine Empfehlung: Quality-Selector jetzt implementieren, Face Swap später**
