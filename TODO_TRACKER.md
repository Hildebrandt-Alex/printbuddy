# 🎯 PrintBuddy Implementation Tracker

**Start:** 18. August 2026
**Status:** 🚀 In Progress
**Deployment:** Production (printbuddy.datemyhobby.com)

---

## ⚡ Security (CRITICAL - 20min)

### S1: nginx IP-Whitelist für /media/jobs/ [15min]
- [x] ~~Entscheidung: IP-Whitelist würde Studio-Workers blockieren~~
- [x] ~~MVP-Lösung: `/media/jobs/` bleibt public (UUIDs = Security-by-Obscurity)~~
- [x] ~~TODO für Phase 6: Django-Auth + X-Accel-Redirect~~
- **Status:** ✅ DEFERRED (proper Auth in Phase 6)
- **Reasoning:** Printful braucht public URLs, aber Studio-Workers auch → Konflikt

### S2: nginx /protected-bundles/ location [5min]
- [x] Backup erstellt: `/etc/nginx/sites-available/printbuddy.backup-*`
- [x] Location /protected-bundles/ hinzugefügt (internal, alias /mnt/agency_nas/bundles/)
- [x] nginx reload: ✅ active
- [x] Test: curl → HTTP 404 ✅ (internal funktioniert)
- **Status:** ✅ COMPLETED (18. Aug 2026, 02:35 CEST)
- **Deploy:** Production live

---

## 🛠️ Phase 1: Bugfixes (BLOCKING - 1h)

### P1.1: upscale_image RunPod API Fix [20min]
- [x] `gpu/tasks.py` Zeile 580 geändert
- [x] Fix: `endpoint = runpod.Endpoint(endpoint_id); endpoint.run_sync()`
- [x] Git commit: `fix: upscale_image RunPod API call korrekt`
- [x] Push + VPS Deploy ✅
- [x] Celery restart: gpu + cpu ✅ active
- **Status:** ✅ COMPLETED (18. Aug 2026, 02:40 CEST)
- **Commit:** b1706a6

### P1.2: Quick Adjust Canvas Fix [15min]
- [ ] `templates/studio/job_results.html` JavaScript selector korrigieren
- [ ] Canvas mit Bild füllen statt schwarz
- [ ] Git commit: `fix: Quick Adjust Modal zeigt Bild statt schwarzer Canvas`
- [ ] VPS Deploy
- [ ] Test: Quick Adjust öffnen → Bild sichtbar

### P1.3: PipelineTemplate "Preview Only" anlegen [10min]
- [ ] Django Admin → PipelineTemplates → Add
- [ ] Settings: step_generate=True, step_upscale=False, step_pod_export=False, step_preview=True
- [ ] Name: "Preview Only — Schnelle Iteration"
- [ ] default_model: flux_schnell, default_steps: 4, default_guidance: 0.0
- [ ] Test: Neuen Job erstellen → nur Preview-Step läuft

### P1.4: Verifizierung [15min]
- [ ] Neuer Job mit Preview-Only Template → 30s statt 5min
- [ ] Enhancement Job → upscale läuft ohne Fehler
- [ ] Quick Adjust → Canvas zeigt Bild

**Status P1:** ⏳ Not Started | Blocking für P2-P5
**Commit:** `fix: Phase 1 Bugfixes abgeschlossen`

---

## 🧹 Cleanup (17min)

### C1: Debug Scripts archivieren [10min]
- [ ] Ordner erstellen: `scripts/archive_2026-08/`
- [ ] Alle analyze_*, check_*, cleanup_*, debug_*, fix_*, repair_*, rollback_* verschieben (30+ Dateien)
- [ ] Git commit: `chore: Debug scripts von August 17 archiviert`
- [ ] VPS Deploy

### C2: Veraltete HTML Docs löschen [2min]
- [ ] Löschen: buisnes_architecture.html, howto.html, mvp_tracker.html, umsetzungsplan.html
- [ ] Git commit: `chore: Veraltete HTML Docs entfernt (redundant zu Markdown)`
- [ ] VPS Deploy

### C3: Git löschen auf VPS [5min]
- [ ] `ssh datemyhobby 'cd /opt/printbuddy && git add -A && git commit -m "cleanup: lokale Änderungen committed"'`
- [ ] Push zu GitHub
- [ ] VPS: git pull

**Status C:** ⏳ Not Started | Kann parallel zu P2

---

## 📝 Dokumentation (45min)

### D1: docs/PIPELINE_OVERVIEW.md aktualisieren [15min]
- [ ] Neuer Workflow dokumentieren (Preview First → Upscale on-demand)
- [ ] Enhancement-Workflow erklären
- [ ] Git commit: `docs: Pipeline-Workflow aktualisiert`

### D2: docs/BILDPFADE.md aktualisieren [15min]
- [ ] /adjusted/ Ordner dokumentieren
- [ ] Export-on-Demand Logik
- [ ] Git commit: `docs: Bildpfade für neuen Workflow`

### D3: docs/POSTGRESQL_SETUP_WINDOWS.md check [15min]
- [ ] Auf Aktualität prüfen
- [ ] Falls nötig: ImageProduct neue Felder dokumentieren

**Status D:** ⏳ Not Started | Kann parallel zu P3-P5

---

## 🎨 Phase 2: Quick Adjust Refactoring (2h)

### P2.1: Quick Adjust Logic ändern [1h]
- [ ] `studio/views.py` quick_adjust_image() refactoren
- [ ] Entferne async `adjust_colors.delay()` Call
- [ ] Speichere direkt JPG Preview (Pillow inline)
- [ ] JobStep anlegen (status=done sofort)
- [ ] Git commit: `refactor: Quick Adjust direkt JPG (kein async)`
- [ ] VPS Deploy
- [ ] Test: Quick Adjust → sofortige Response

### P2.2: Template-Update [30min]
- [ ] `templates/studio/job_results.html` anpassen
- [ ] Adjusted Bilder mit Badge "🎨 Adjusted #N" anzeigen
- [ ] Git commit: `feat: Adjusted-Badge in Results View`
- [ ] VPS Deploy

### P2.3: Verifizierung [30min]
- [ ] Quick Adjust 5x hintereinander → alle Versionen sichtbar
- [ ] Keine async-Wartezeit
- [ ] Canvas zeigt Original korrekt

**Status P2:** ⏳ Not Started | Depends on P1
**Commit:** `feat: Phase 2 Quick Adjust Refactoring abgeschlossen`

---

## 📦 Phase 3: Product Workflow (CORE - 4h)

### P3.1: shop/models.py Migration [30min]
- [ ] ImageProduct erweitern: source_asset_id (UUIDField), export_status (CharField)
- [ ] Migration: `makemigrations --name add_image_product_export_fields`
- [ ] Git commit: `feat: ImageProduct source_asset_id + export_status`
- [ ] VPS Deploy + migrate

### P3.2: create_product_from_asset View [1h]
- [ ] `studio/views.py` neue Funktion
- [ ] POST: ImageProduct anlegen, Celery Chain starten
- [ ] GET: Produktauswahl-Template
- [ ] Git commit: `feat: Produkt-Erstellung aus Asset`

### P3.3: create_product_exports_chain Task [1h 30min]
- [ ] `postprocess/tasks.py` neue Task
- [ ] Workflow: Upscale → POD → CMYK (conditional) → Mockup → Status=ready
- [ ] required_export_types aus ProductVariant lesen
- [ ] Git commit: `feat: Product Export Chain on-demand`

### P3.4: Template create_product.html [30min]
- [ ] Neue Datei `templates/studio/create_product.html`
- [ ] Produktauswahl mit Radio-Buttons
- [ ] Git commit: `feat: Produkt-Wizard Template`

### P3.5: studio/urls.py Route [5min]
- [ ] Route: `job/<uuid:job_id>/asset/<uuid:asset_id>/create-product/`
- [ ] Git commit: `feat: Product-Creation Route`

### P3.6: job_results.html Button [10min]
- [ ] "📦 Produkt erstellen" Button nach "Für Galerie vormerken"
- [ ] Git commit: `feat: Produkt-Button in Results View`

### P3.7: VPS Deploy + Test [15min]
- [ ] Deploy
- [ ] Celery restart
- [ ] Test: Asset → Produkt erstellen → Exports laufen

### P3.8: Verifizierung [20min]
- [ ] Produkt erstellen aus Preview → Upscale + POD läuft
- [ ] ImageProduct.export_status = ready nach Chain
- [ ] required_export_types werden beachtet

### P3.9: Dokumentation Update [10min]
- [ ] copilot-instructions.md Section 4 updaten
- [ ] Git commit: `docs: Product Workflow dokumentiert`

**Status P3:** ⏳ Not Started | Depends on P1
**Commit:** `feat: Phase 3 Product Workflow abgeschlossen`

---

## 🖼️ Phase 4: Printful Mockup Integration (3h)

### P4.1: postprocess/printful.py HTTP-Client [1h]
- [ ] Neue Datei erstellen
- [ ] Funktionen: create_mockup_task(), get_mockup_task_result(), download_mockup_image()
- [ ] PRINTFUL_API_KEY aus settings
- [ ] Git commit: `feat: Printful HTTP-Client`

### P4.2: generate_printful_mockup Task [1h 30min]
- [ ] `postprocess/tasks.py` Stub ersetzen
- [ ] Workflow: Task erstellen → polling (max 10min) → download → ImageProduct.mockup_status=ready
- [ ] Retry logic (max_retries=5)
- [ ] Git commit: `feat: Printful Mockup Generation Task`

### P4.3: Product Model erweitern [10min]
- [ ] Product.printful_product_id (PositiveIntegerField)
- [ ] ProductVariant.printful_variant_id (CharField)
- [ ] Migration: `makemigrations --name add_printful_ids`
- [ ] Git commit: `feat: Printful IDs in Product Models`

### P4.4: VPS Deploy + Test [15min]
- [ ] Deploy
- [ ] Test mit Printful Sandbox
- [ ] Mockup-Bild erfolgreich downloadet

### P4.5: Verifizierung [5min]
- [ ] Mockup-Task bei Printful erstellt (API-Call 200)
- [ ] ImageProduct.mockup_status = ready
- [ ] Mockup-Bild in /media/shop/mockups/

**Status P4:** ⏳ Not Started | Depends on P3
**Commit:** `feat: Phase 4 Printful Mockup Integration abgeschlossen`

**⚠️ SECURITY NOTE:** Printful benötigt public image URL → nginx /media/jobs/ muss für Printful IPs erreichbar sein (S1)

---

## 📦 Phase 5: Bundle Generation System (3h)

### P5.1: bundles/tasks.py erstellen [2h]
- [ ] Neue Datei anlegen
- [ ] create_print_bundle Task implementieren
- [ ] Logik: Order → ProductVariant.required_export_types → Partner.export_formats → ZIP
- [ ] NAS-Pfad: /mnt/agency_nas/bundles/{order_id}_bundle.zip
- [ ] Git commit: `feat: Bundle Generation Task`

### P5.2: shop/admin.py Bundle-Action [20min]
- [ ] Admin Action "📦 Bundle für Partner erstellen"
- [ ] bundle_status() custom column
- [ ] Git commit: `feat: Bundle Admin Action`

### P5.3: partners/views.py download_bundle [30min]
- [ ] Neue Datei erstellen
- [ ] download_bundle View mit X-Accel-Redirect
- [ ] Security: nur eigener Partner kann downloaden
- [ ] Git commit: `feat: Partner Bundle Download`

### P5.4: partners/urls.py Route [5min]
- [ ] Route: `bundle/<uuid:bundle_id>/download/`
- [ ] Git commit: `feat: Bundle Download Route`

### P5.5: nginx protected-bundles location [5min]
- [ ] (bereits in S2 erledigt)
- [ ] Test: direkter Zugriff → 404

### P5.6: VPS Deploy + Test [10min]
- [ ] Deploy
- [ ] Order erstellen → Admin Action → Bundle ZIP auf NAS
- [ ] Partner einloggen → Bundle downloadbar

### P5.7: Verifizierung [15min]
- [ ] Bundle enthält korrekte Dateitypen
- [ ] ZIP-Struktur: {product_name}_{export_type}_{asset_id}.{ext}
- [ ] Partner-Dashboard zeigt Bundle-Liste

**Status P5:** ⏳ Not Started | Depends on P3
**Commit:** `feat: Phase 5 Bundle Generation System abgeschlossen`

---

## ✅ Final Verification (1h)

### V1: End-to-End Test [30min]
- [ ] Job erstellen (Preview Only) → 30s
- [ ] Quick Adjust → sofort
- [ ] Für Galerie vormerken
- [ ] Produkt erstellen → Upscale + POD läuft
- [ ] Mockup generiert
- [ ] Order erstellen → Bundle generiert

### V2: Security Check [15min]
- [ ] /media/jobs/ nur für Printful IPs erreichbar
- [ ] /protected-bundles/ nur via Django Auth
- [ ] Keine öffentlichen Debug-Logs

### V3: Performance Check [10min]
- [ ] Preview-Job: < 1min
- [ ] Product-Export-Chain: < 5min
- [ ] Quick Adjust: < 3s Response

### V4: Dokumentation vollständig [5min]
- [ ] Alle Docs auf neuem Stand
- [ ] TODO_TRACKER.md abgeschlossen
- [ ] Git: alle Commits gepusht

**Status V:** ⏳ Not Started

---

## 📊 Progress Summary

| Phase | Status | Estimated | Actual | Completion |
|-------|--------|-----------|--------|------------|
| Security (S1-S2) | ⏳ Not Started | 20min | - | 0% |
| Phase 1 (P1.1-P1.4) | ⏳ Not Started | 1h | - | 0% |
| Cleanup (C1-C3) | ⏳ Not Started | 17min | - | 0% |
| Docs (D1-D3) | ⏳ Not Started | 45min | - | 0% |
| Phase 2 (P2.1-P2.3) | ⏳ Not Started | 2h | - | 0% |
| Phase 3 (P3.1-P3.9) | ⏳ Not Started | 4h | - | 0% |
| Phase 4 (P4.1-P4.5) | ⏳ Not Started | 3h | - | 0% |
| Phase 5 (P5.1-P5.7) | ⏳ Not Started | 3h | - | 0% |
| Verification (V1-V4) | ⏳ Not Started | 1h | - | 0% |
| **TOTAL** | **0/68 TODOs** | **~15h** | **0h** | **0%** |

---

## 🚀 Execution Plan

### Day 1 (6h):
1. **Security (S1-S2)** → 20min ⚠️ CRITICAL
2. **Phase 1 (P1)** → 1h 🚫 BLOCKING
3. **Cleanup (C)** → 17min (parallel)
4. **Phase 2 (P2)** → 2h
5. **Phase 3 Start (P3.1-P3.5)** → 3h

### Day 2 (6h):
1. **Phase 3 Ende (P3.6-P3.9)** → 1h
2. **Phase 4 (P4)** → 3h
3. **Docs (D)** → 45min
4. **Verification (V)** → 1h 15min

### Day 3 (3h, optional):
1. **Phase 5 (P5)** → 3h (Bundle System für Partner)

---

## 📌 Critical Path

```
S1-S2 (Security) → P1 (Bugfixes) → P2 (Quick Adjust) → P3 (Product Workflow) → P4 (Printful) → [P5 optional]
```

**Blockers:**
- S1 must be done BEFORE P4 (Printful needs public URLs)
- P1 must be done BEFORE P2-P5 (bugs block development)
- P3 must be done BEFORE P4-P5 (Models + Workflow needed)

---

## 🎯 Next Action

**JETZT STARTEN:** Security Fix S1 (nginx IP-Whitelist)

**Command:** `ssh datemyhobby 'sudo vim /etc/nginx/sites-available/printbuddy'`

---

**Last Updated:** 18. August 2026, 02:30 CEST
**Git Repo:** github.com/yourusername/printbuddy (private)
**VPS:** printbuddy.datemyhobby.com (Ubuntu 22.04, Hetzner)
