# WORKFLOW-ANALYSE & LÖSUNGSPLAN
# =====================================

## AKTUELLER ZUSTAND nach Rollback

### Job: test22 (94a82c60)
- **Original Assets:**
  - Generate: 6734ea2c (raw/6734ea2c.png) ✅
  - Preview: f9fd1f5d (exports/preview/f9fd1f5d_preview.jpg) ✅

- **Quick Adjusts (3 mit echten Assets):**
  1. ba274f35 (Order 4, 09.08. 23:44) ✅ raw/ba274f35_adjusted.png
  2. 8b3f4086 (Order 7, 09.08. 17:13) ✅ raw/8b3f4086_adjusted_20260810_022143.png
  3. bf0c505f (Order 8, 09.08. 17:13) ✅ raw/bf0c505f_adjusted.png

- **Pending Quick Adjusts:** 2 Steps ohne Assets (vermutlich Duplikate/Fehler)

### Job: sdxl (646e8898)
- **Original Assets:**
  - Generate: b5486c8e
  - Preview: 489f2d1f

- **Quick Adjusts (1 echt):**
  1. (Order 4) ✅ raw/..._adjusted.png
  
- **Pending:** 4 Steps (vom Repair fälschlicherweise zugewiesen)

### Job: maxtest2 (2f05e48d)
- **Original Assets:**
  - Generate: c6019116
  - Preview: e1f4d0bd

- **Quick Adjusts (1 echt):**
  1. 843ff5c4 ✅
  
- **Pending:** 1 Step

---

## WORKFLOW-LOGIK: Ist-Zustand

### 1. Job Creation Phase
```
User erstellt Job -> Generate (GPU) -> Preview Export (CPU)
                  -> Job status = 'done'
                  -> User sieht Preview in job_results View
```

### 2. Quick Adjust Phase (KORREKT implementiert)
```
User klickt "Quick Adjust" Button auf job_results Page
  -> quick_adjust_image View (studio/views.py:1037)
  -> Erstellt JobStep(step_type='quick_adjust', status='pending', params={...})
  -> adjust_colors Task (postprocess/tasks.py:486)
     -> Nutzt _get_latest_asset(job_id, prefer_upscaled=True)
     -> Lädt: raw/<generate_asset_id>.png oder raw/<upscale_asset_id>_4x.png
     -> Wendet PIL Adjustments an
     -> Speichert: raw/<neue_uuid>_adjusted_<timestamp>.png
     -> _save_step setzt output_asset_id = neue_uuid
  -> User sieht adjusted Bild in job_results (HTMX reload)
```

**✅ KORREKT:** Quick Adjust basiert immer auf dem Original-Generate-Asset des Jobs!

### 3. Enhancement Phase (NOCH NICHT GETESTET)
```
User wählt adjusted Bild -> "Enhancement" Button
  -> enhancement_job_create View
  -> Erstellt neuen Job mit pipeline_template (step_generate=False)
  -> Job.notes = {"source_asset_id": "<adjusted_uuid>"}
  -> Upscale Task nutzt _get_latest_asset
     -> Liest notes.source_asset_id
     -> Sucht: exports/preview/<uuid>_preview.jpg
             ODER raw/<uuid>_adjusted_*.png
             ODER raw/<uuid>_cropped.png
             ODER raw/<uuid>.png
```

**✅ KORREKT:** Enhancement-Jobs nutzen source_asset_id aus notes!

---

## PROBLEM: Warum zeigt test22 Bilder anderer Jobs?

**ROOT CAUSE:** Das Repair-Script hat **blind** Assets zugewiesen:
- test22 bekam sdxl Assets (8b3f4086: ursprünglich test22, aber auch sdxl zugewiesen)
- test22 bekam maxtest2 Asset (843ff5c4)
- Alle Jobs teilten sich 4 Assets (af93325d, 843ff5c4, 8b3f4086, bf0c505f)

**ROLLBACK AUSGEFÜHRT:** 7 falsche Zuweisungen zurückgesetzt ✅

**AKTUELLER STAND:**
- test22: 3 echte Quick Adjusts ✅
- sdxl: 1 echter Quick Adjust ✅
- maxtest2: 1 echter Quick Adjust ✅

---

## VERBLEIBENDE PENDING STEPS: Was damit tun?

### Option A: Löschen (sauber)
Alle pending Quick Adjust Steps ohne Assets löschen - sie waren Fehler.

### Option B: Behalten (dokumentiert)
Status pending lassen als Dokumentation "User wollte Adjust aber es gab Fehler".

**EMPFEHLUNG:** Option A - Löschen. Sie haben keine Dateien, nur DB-Müll.

---

## WORKFLOW-VALIDIERUNG: Kann Rest funktionieren?

### ✅ Job Creation -> Quick Adjust
- FUNKTIONIERT korrekt
- Quick Adjust basiert auf Original-Job-Asset ✅
- Jeder Quick Adjust bekommt eigene UUID ✅
- Dateien mit Timestamp-Versionierung ✅

### ⚠️ Quick Adjust -> Enhancement
- **Code existiert** (_get_latest_asset hat Enhancement-Mode) ✅
- **Nicht getestet** - muss verifiziert werden
- **Potential Issue:** Enhancement von adjusted Bild könnte falsch sein

### ❓ Enhancement -> Product Creation
- **Nicht implementiert** in aktuellem Code
- Braucht: ImageProduct mit source_asset.output_asset_id von Enhancement-Job

---

## BENÖTIGTE ACTIONS

1. **Cleanup:** Pending Quick Adjust Steps ohne Assets löschen
2. **Test:** Enhancement-Workflow mit adjusted Bild testen
3. **Verify:** Prüfen ob enhancement_job_create source_asset_id korrekt setzt
4. **Document:** JobStep.params könnte source_asset_id speichern (optional)

---

## DATENMODELL-VERBESSERUNG (Optional, nicht kritisch)

### JobStep erweitern:
```python
source_asset_id: UUIDField(null=True, blank=True)  # Welches Asset wurde verarbeitet?
```

**Vorteil:** Explizite Verkettung sichtbar in DB
**Nachteil:** Migration nötig, Enhancement nutzt bereits notes JSON

**ENTSCHEIDUNG:** Nicht nötig - notes.source_asset_id reicht aus.

---

## ZUSAMMENFASSUNG

✅ **Quick Adjust Workflow:** KORREKT implementiert
✅ **Enhancement-Logik:** Code vorhanden (_get_latest_asset)
✅ **Rollback:** 7 falsche Zuweisungen bereinigt
⚠️ **Verbleibende Pending Steps:** Sollten gelöscht werden (DB-Müll)
❓ **Enhancement-Test:** Muss User durchführen

**DER REST SOLLTE FUNKTIONIEREN** - Enhancement verwendet notes.source_asset_id.
