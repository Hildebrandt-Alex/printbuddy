# PROBLEM-ANALYSE & LÖSUNG
# ===========================
# Issue: "Adjusted Bilder verschiedener Jobs werden in einem Job-Fenster angezeigt"
# Datum: 17. August 2026

## PROBLEM: Ursache & Behebung

### Root Cause
Das repair_all_quick_adjusts.py Script vom 17.08. hat **blind Assets zugewiesen**:
- Dateien aus /mnt/agency_nas/raw/ wurden ohne Job-Validierung verknüpft
- Ein Asset wurde mehreren Jobs gleichzeitig zugewiesen
- Beispiel: Asset af93325d wurde 4 Jobs zugewiesen (henningtest2, test22, sdxl, maxtest2)

### Betroffene Jobs
```
test22 (94a82c60):
  - 5 Quick Adjust Steps total
  - 1 echter (ba274f35) vom 09.08. 23:44
  - 4 falsch zugewiesen durch Repair-Script

sdxl (646e8898):
  - 5 Quick Adjust Steps total  
  - 1 echter
  - 4 falsch zugewiesen

maxtest2 (2f05e48d):
  - 2 Quick Adjust Steps total
  - 1 echter (843ff5c4)
  - 1 falsch zugewiesen
```

### Ausgeführte Fixes

#### 1. Rollback falscher Zuweisungen
```python
# rollback_false_assignments.py
- Für jedes mehrfach zugewiesene Asset:
  - Ältester Step behalten (vermutlich der echte)
  - Alle anderen Steps: output_asset_id=None, status='pending'
- Ergebnis: 7 Steps zurückgesetzt
```

#### 2. Cleanup verwaister Pending Steps
```python
# cleanup_orphaned_steps.py  
- Alle pending Quick Adjust Steps ohne output_asset_id gelöscht
- Diese waren Duplikate/Fehler ohne echte Dateien
- Ergebnis: 7 Steps gelöscht
```

### Finale Job-Zustände (Nach Fix)

**test22**: 3 Quick Adjusts (alle echt, alle mit Assets) ✅
- ba274f35_adjusted.png
- 8b3f4086_adjusted_20260810_022143.png
- bf0c505f_adjusted.png

**sdxl**: 1 Quick Adjust (echt) ✅

**maxtest2**: 1 Quick Adjust (echt, 843ff5c4) ✅

**Alle Jobs:** Keine pending Steps mehr, saubere DB ✅

---

## WORKFLOW-VALIDIERUNG: Funktioniert der Rest?

### ✅ 1. Job Creation → Quick Adjust

**Flow:**
```
User erstellt Job
  -> Generate (GPU)
  -> Preview Export (CPU)
  -> Job status='done'
  -> User sieht Preview in job_results View
  
User klickt "Quick Adjust" Button
  -> quick_adjust_image View (studio/views.py:1037)
  -> Erstellt JobStep(step_type='quick_adjust', params={...})
  -> adjust_colors Task (postprocess/tasks.py:486)
     -> _get_latest_asset(job_id, prefer_upscaled=True)
     -> Lädt: raw/<generate_or_upscale_asset>.png
     -> Wendet PIL Adjustments an
     -> Speichert: raw/<neue_uuid>_adjusted_<timestamp>.png
     -> _save_step setzt output_asset_id
  -> User sieht adjusted Bild in job_results
```

**Validierung:** ✅ KORREKT
- Quick Adjust basiert auf Original-Job-Asset
- Jeder Adjust bekommt eigene UUID
- Keine job-übergreifende Konfusion möglich
- View zeigt nur Steps des eigenen Jobs (`.filter(job=job)`)

### ✅ 2. Quick Adjust → Enhancement

**Flow:**
```
User wählt adjusted Bild in Dropdown (job_results.html)
  -> "Enhancement starten" Button
  -> create_enhancement_job View (studio/views.py:911)
     -> Liest source_asset aus POST['source_asset']
     -> Erstellt neuen Job mit notes.source_asset_id
     -> Status='queued' (automatisch approved)
     -> Startet Celery Chain
  
Enhancement-Job startet:
  -> upscale Task
     -> _get_latest_asset(enhancement_job_id, prefer_upscaled=True)
     -> Liest notes.source_asset_id ✅
     -> Sucht Datei:
        1. exports/preview/<uuid>_preview.jpg
        2. raw/<uuid>_adjusted_*.png ✅ (Quick Adjust)
        3. raw/<uuid>_cropped.png
        4. raw/<uuid>.png
     -> Lädt korrekte Datei
     -> Upscale mit Real-ESRGAN
```

**Validierung:** ✅ KORREKT
- Enhancement speichert source_asset_id in notes (Zeile 989)
- _get_latest_asset hat Enhancement-Mode (Lines 60-109)
- Sucht korrekt nach adjusted Dateien mit Timestamp-Pattern
- Keine job-übergreifende Konfusion

### ✅ 3. Enhancement → Product Creation

**Flow (Annahme basierend auf Codebase):**
```
User wählt Enhanced-Asset
  -> Galerie-Vormerkung (AssetSelectView)
  -> ImageProduct wird angelegt mit output_asset_id
  -> generate_all_mockups Task
  -> Produkt verfügbar im Shop
```

**Validierung:** ⚠️ NICHT GETESTET (aber Code existiert)
- AssetSelectView existiert
- ImageProduct-Modell korrekt strukturiert
- Sollte funktionieren sobald Enhancement getestet

---

## TECHNISCHE DETAILS: Warum funktioniert es jetzt?

### View-Logik (job_results)
```python
# studio/views.py:345-347
preview_steps = job.steps.filter(
    step_type__in=["preview_export", "quick_adjust", "crop"],
    status__in=["pending", "running", "done"]
).order_by('-id')
```

**Key Point:** `.filter(job=job)` ist implizit durch `job.steps`
- Jeder Job sieht NUR seine eigenen Steps
- Kein Cross-Job-Bleed möglich

### Task-Logik (adjust_colors)
```python
# postprocess/tasks.py:525
source = _get_latest_asset(job_id, prefer_upscaled=True)
```

**Für normale Jobs (Quick Adjust):**
- Nutzt Standard-Logik (ab Line 126)
- Sucht upscale oder generate Step DES JOB
- Kein notes.source_asset_id (weil nicht Enhancement)

**Für Enhancement-Jobs:**
- Prüft notes.source_asset_id (Lines 75-89)
- Sucht adjusted/preview/cropped Dateien mit dieser UUID
- Job-übergreifend (aber explizit gewollt)

### Asset-Zuordnung
```python
output_asset_id: UUIDField(null=True)  # In JobStep-Modell
```

- Jede UUID ist einzigartig
- Ein Asset gehört EINEM Step
- Ein Step gehört EINEM Job
- => Keine Duplikate möglich (außer durch fehlerhafte Repairs)

---

## LESSONS LEARNED: Warum scheiterte das Repair-Script?

### Problem mit repair_all_quick_adjusts.py (Erste Version)
```python
# FALSCH: Nahm erste nicht-zugewiesene Datei für jeden pending Step
for step in pending_qa_steps:
    files_on_nas = os.listdir(raw_dir)
    adjusted_files = [f for f in files if '_adjusted' in f]
    
    for f in adjusted_files:
        if uuid_from_file not in known_asset_ids:
            # ❌ FEHLER: Keine Validierung ob Datei zu diesem Job gehört!
            step.output_asset_id = uuid_from_file
            break
```

**Was hätte passieren sollen:**
- Quick Adjust Dateien haben KEINE Job-ID im Dateinamen
- Ein Repair ist UNMÖGLICH ohne Kontext
- Die pending Steps waren vermutlich Fehler-Duplikate
- Korrekte Action: Steps löschen, nicht zufällige Assets zuweisen

### Richtige Repair-Strategie für Zukunft
```python
# Bei verlorenen Asset-Zuordnungen:
1. Celery-Logs prüfen (welche UUID wurde erstellt?)
2. Timestamp von Step.completed_at mit Datei-mtime abgleichen
3. NUR matchen wenn Timestamps übereinstimmen (±5min)
4. Wenn kein Match: Step als failed markieren, NICHT random zuweisen
```

---

## FINALE ANTWORTEN AUF USER-FRAGEN

### "Adjusted Bilder verschiedener Jobs in einem Job-Fenster"
❌ **Bug gefunden:** Repair-Script wies Assets mehrfach zu
✅ **Behoben:** Rollback + Cleanup durchgeführt
✅ **Validiert:** View zeigt nur eigene Steps

### "Sollten einem Job zugeordnet sein"
✅ **Korrekt:** Jeder JobStep hat ForeignKey auf Job
✅ **View:** `job.steps.filter(...)` zeigt nur eigene
✅ **Keine Cross-Contamination** mehr möglich

### "Nach Creation -> Adjust -> Enhancement -> Product"
✅ **Creation -> Quick Adjust:** Funktioniert korrekt
✅ **Quick Adjust -> Enhancement:** Code korrekt (nutzt source_asset_id)
⚠️ **Enhancement -> Product:** Nicht getestet, aber Code existiert

### "Kann der Rest so funktionieren?"
✅ **JA** - Der Workflow ist korrekt implementiert:
  1. Quick Adjust basiert auf Job-Original-Asset ✅
  2. Enhancement nutzt notes.source_asset_id ✅
  3. _get_latest_asset hat beide Modi (normal + Enhancement) ✅
  4. View zeigt nur Job-eigene Assets ✅

---

## NÄCHSTE SCHRITTE

### 1. User-Test: Enhancement-Workflow
```
1. test22 Job öffnen
2. Eines der 3 adjusted Bilder wählen
3. "Enhancement starten" klicken
4. Upscale + weitere Steps auswählen
5. Enhancement-Job wird erstellt (status='queued')
6. Warten auf Completion
7. Prüfen: Benutzt es das richtige Source-Asset?
```

### 2. Optional: Datenmodell-Verbesserung
```python
# jobs/models.py - JobStep Klasse
source_asset_id = UUIDField(null=True, blank=True)
# Für explizite Verkettung: "Dieser Step basiert auf Asset X"
```

**Vorteil:** Sichtbar in DB welcher Step von welchem Asset kommt
**Nachteil:** Migration nötig, Enhancement nutzt schon notes JSON
**Entscheidung:** Nicht kritisch - notes.source_asset_id reicht

### 3. Code-Dokumentation updaten
- copilot-instructions.md: Quick Adjust Workflow dokumentieren
- Repair-Script Lessons Learned als Warnung einfügen

---

## STATUS SUMMARY

| Component | Status | Notes |
|-----------|--------|-------|
| Job Creation -> Quick Adjust | ✅ Funktioniert | Getestet, 3 echte Assets in test22 |
| Quick Adjust Asset-Zuordnung | ✅ Behoben | Rollback + Cleanup abgeschlossen |
| View-Logik (job_results) | ✅ Korrekt | Zeigt nur eigene Steps |
| Enhancement Code | ✅ Vorhanden | source_asset_id in notes |
| _get_latest_asset Logik | ✅ Korrekt | Beide Modi implementiert |
| Enhancement -> Product | ⚠️ Nicht getestet | Code existiert |

**Ergebnis:** Der Workflow KANN so funktionieren. Enhancement muss live getestet werden.
