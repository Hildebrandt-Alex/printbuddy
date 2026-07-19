# PrintBuddy — Copilot Architecture Reference

> **Für Copilot:** Diese Datei ist die bindende Architekturreferenz für das PrintBuddy-Projekt.
> Lies sie vollständig bevor du Code schreibst, vorschlägst oder erweiterst.
> Entscheidungen sind ADR-backed. Neue ADRs werden als `adr:` Commit hinzugefügt.

---

## 1. Projektübersicht

**PrintBuddy** ist eine Django-Applikation für KI-gestützte Bildgenerierung, Print-Produktion und Vertrieb.

**Kern-Flow:**

```
Prompt -> GPU-Generierung (RunPod/Vast.ai) -> Post-Processing (Upscale/CMYK/Vectorize)
       -> Galerie Landing Page -> Shop/Etsy -> Fulfillment (Printful) -> PrintBundle
```

**Team:** 2 Personen — A (Backend/Infra/Security), B (Content/Produkt/Vertrieb)
**Domain:** datemyhobby.com/printbuddy
**Runtime:** Django 4.2 LTS · Python 3.11 · PostgreSQL 15 · Redis 7 · Celery 5

---

## 2. Django App-Inventar

| App | Pfad | Zweck | Erweiterbar durch |
|-----|------|-------|-------------------|
| `gallery` | `gallery/` | Öffentliche Galerie-Landing Page, GalleryImage-Verwaltung | Neue CTA-Typen, Filterkategorien |
| `shop` | `shop/` | Merch-Shop, Stripe Checkout, Printful Fulfillment | Neue Produkttypen; neue Zahlmethode nur per ADR |
| `jobs` | `jobs/` | PipelineTemplate, Job, JobStep, PromptTemplate | Neue Step-Typen als TextChoices |
| `studio` | `studio/` | Externe Mitarbeiter Web App — Job-Erstellung & Bild-Sichtung | Neue Views, neue Aktions-Flows |
| `gpu` | `gpu/` | Celery Tasks für GPU-Generierung + Upscaling | Neuer GPU-Provider nur per ADR |
| `postprocess` | `postprocess/` | CPU-Tasks: CMYK, Vectorize, Mockup, QA | Neue Verarbeitungsschritte als Tasks |
| `bundles` | `bundles/` | PrintBundle — Druckdatei-Bündelung für Bestellungen | Neue Bundle-Formate |
| `etsy` | `etsy/` | Etsy Open API v3 Listing-Management | Neue Listing-Typen |
| `channels` | `channels/` | SalesChannel — generische Kanal-Abstraktion (Shop, Etsy, WooCommerce, Shopify, manuell) | Neuer `channel_type` als TextChoices |
| `partners` | `partners/` | FulfillmentPartner — Druckstudio-Login, Bestellübersicht, Bundle-Download | Neuer Partner per Admin |

**Verboten:**
- Keine Business-Logik in Views -> Services in `<app>/services.py` oder Celery Task
- Keine SQL-Queries in Templates
- Kein ORM-Objekt als Celery-Task-Argument — nur UUIDs übergeben
- Keine Secrets im Code oder Git-Repo

---

## 3. Datenmodell-Inventar

### gallery — GalleryImage

```python
id:             UUIDField(primary_key=True)
title:          CharField(max_length=120)
slug:           SlugField(unique=True)
description:    TextField(blank=True)
file_path:      ImageField(upload_to='gallery/full/')
thumb_path:     ImageField(upload_to='gallery/thumbs/', blank=True)
category:       CharField(choices=['shirt','poster','card','art'])
tags:           CharField(max_length=250, blank=True)   # kommasepariert
cta_type:       CharField(choices=['etsy','shop','contact'])
cta_url:        URLField(blank=True)
is_public:      BooleanField(default=False)
sort_order:     PositiveIntegerField(default=0)
source_job_id:  UUIDField(null=True)   # Referenz auf Job.id (loses Coupling, kein FK)
created_at:     DateTimeField(auto_now_add=True)
updated_at:     DateTimeField(auto_now=True)
# Methode: _generate_thumbnail() — 600x600 JPEG via Pillow, aufgerufen in save()
```

### shop — Product

```python
id:          UUIDField(primary_key=True)
name:        CharField(max_length=100)
slug:        SlugField(unique=True)
description: TextField()
category:    CharField(max_length=40)
base_image:  ImageField(upload_to='shop/products/')
is_active:   BooleanField(default=True)
created_at:  DateTimeField(auto_now_add=True)
```

### shop — ProductVariant

```python
product:               ForeignKey(Product, related_name='variants', on_delete=CASCADE)
size:                  CharField(max_length=10)
color:                 CharField(max_length=40)
printful_variant_id:   CharField(max_length=50)
price_eur:             DecimalField(max_digits=8, decimal_places=2)
cost_eur:              DecimalField(max_digits=8, decimal_places=2)
required_export_types: JSONField(default=list)   # z.B. ['pod','cmyk','preview']
is_active:             BooleanField(default=True)
```

### shop — Order

```python
id:                 UUIDField(primary_key=True)
stripe_session_id:  CharField(max_length=200, unique=True)
stripe_payment_id:  CharField(max_length=200, blank=True)
printful_order_id:  CharField(max_length=50, blank=True)
status:             CharField(choices=['pending','paid','processing','shipped','delivered','cancelled'])
email:              EmailField()
name:               CharField(max_length=100)
shipping_address:   JSONField()   # von Stripe-Event, nie direkt vom User
total_eur:          DecimalField(max_digits=10, decimal_places=2)
tracking_code:      CharField(max_length=100, blank=True)
channel:             ForeignKey('channels.SalesChannel', null=True, on_delete=SET_NULL)
fulfillment_partner: ForeignKey('partners.FulfillmentPartner', null=True, on_delete=SET_NULL)
source_channel:     CharField(max_length=30, default='shop')   # legacy
created_at:         DateTimeField(auto_now_add=True)
updated_at:         DateTimeField(auto_now=True)
```

### shop — OrderLine

```python
order:    ForeignKey(Order, related_name='lines', on_delete=CASCADE)
variant:  ForeignKey(ProductVariant, on_delete=PROTECT)
quantity: PositiveIntegerField(default=1)
price:    DecimalField(max_digits=8, decimal_places=2)
```

### channels — SalesChannel

```python
id:           UUIDField(primary_key=True)
name:         CharField(max_length=100)   # "Eigener Shop", "Etsy", "Partner Shop Berlin"
channel_type: CharField(choices=['own_shop','etsy','woocommerce','shopify','manual'])
is_active:    BooleanField(default=True)
webhook_url:  CharField(max_length=500, blank=True)  # wohin Bestellbestätigungen gepusht werden
api_key:      CharField(max_length=200, blank=True)  # verschlüsselt in DB
api_secret:   CharField(max_length=200, blank=True)  # verschlüsselt in DB
base_url:     URLField(blank=True)    # für WooCommerce, Shopify etc.
notes:        TextField(blank=True)
created_at:   DateTimeField(auto_now_add=True)
```

### partners — FulfillmentPartner

```python
id:                 UUIDField(primary_key=True)
name:               CharField(max_length=100)   # "Druckstudio München"
user:               OneToOneField(User, on_delete=PROTECT)   # Django Login
email:              EmailField()
contact_name:       CharField(max_length=100)
export_formats:     JSONField(default=list)    # ['pod','cmyk','vector'] — Druck-Kapazitäten des Partners
notify_email:       BooleanField(default=True)
notify_webhook_url: CharField(max_length=500, blank=True)   # optional: Webhook für neue Aufträge
notes:              TextField(blank=True)
is_active:          BooleanField(default=True)
created_at:         DateTimeField(auto_now_add=True)
```

### partners — PartnerProduct (M2M-Durchgangstabelle: Partner ↔ Produkt)

```python
partner:      ForeignKey(FulfillmentPartner, on_delete=CASCADE)
product:      ForeignKey('shop.Product', on_delete=CASCADE)
export_types: JSONField(default=list)   # z.B. ['cmyk','pod'] — subset von ProductVariant.required_export_types
notes:        TextField(blank=True)
# class Meta: unique_together = [('partner', 'product')]
```

### partners — PartnerVariant (welcher Partner kann welche Variante produzieren)

```python
partner:      ForeignKey(FulfillmentPartner, on_delete=CASCADE)
variant:      ForeignKey('shop.ProductVariant', on_delete=CASCADE)
partner_sku:  CharField(max_length=100, blank=True)   # interne SKU / Bestellnummer des Druckstudios
is_available: BooleanField(default=True)   # z.B. A4 aktuell nicht lieferbar
notes:        TextField(blank=True)
# class Meta: unique_together = [('partner', 'variant')]
# Wenn kein PartnerVariant-Eintrag: Partner kann diese Variante nicht produzieren
```

### shop — ImageProduct (Bild ↔ Produkt Zuordnung + Mockup)

```python
image:        ForeignKey('gallery.GalleryImage', on_delete=CASCADE, related_name='product_links')
product:      ForeignKey(Product, on_delete=CASCADE, related_name='image_links')
mockup_file:  ImageField(upload_to='shop/mockups/', blank=True)   # voraus-berechnetes Mockup
mockup_status: CharField(choices=['pending','generating','ready','failed'], default='pending')
is_primary:   BooleanField(default=False)   # Haupt-Produktbild in der Gallerie
created_at:   DateTimeField(auto_now_add=True)
# class Meta: unique_together = [('image', 'product')]
# Wird angelegt wenn Studio-Mitarbeiter Bild via AssetSelectView für Shop freigibt
# generate_all_mockups Task wird dadurch automatisch ausgelöst
```

### jobs — PipelineTemplate

```python
id:               UUIDField(primary_key=True)
name:             CharField(max_length=100)
description:      TextField(blank=True)
category:         CharField(choices=['shirt_batch','poster_offset','card_pod','vector_art','custom'])
# Pipeline Steps als Boolean Flags
step_generate:    BooleanField(default=True)
step_upscale:     BooleanField(default=True)
step_vectorize:   BooleanField(default=False)   # Inkscape CLI + Potrace -> SVG
step_cmyk:        BooleanField(default=False)   # TIFF + PDF/X-4 via Ghostscript
step_pod_export:  BooleanField(default=True)    # PNG 300dpi sRGB
step_preview:     BooleanField(default=True)    # JPG 72dpi (immer)
step_mockup:      BooleanField(default=False)   # Printful Mockup API
step_auto_qa:     BooleanField(default=False)   # CLIP-Score + Blur-Check
# Default Generation Parameters
default_width:    PositiveIntegerField(default=1024)
default_height:   PositiveIntegerField(default=1024)
default_dpi:      PositiveIntegerField(default=300)
default_steps:    PositiveIntegerField(default=30)
default_guidance: FloatField(default=7.5)
default_model:    CharField(choices=['flux_dev','flux_schnell','sdxl','custom_lora'])
# LIZENZ-HINWEIS:
# flux_dev    -> Nicht kommerziell lizenziert. Nur für interne Tests, Studio-Preview, QA.
#               Darf NICHT für Bilder verwendet werden die verkauft werden.
# flux_schnell-> Apache 2.0 — kommerzielle Nutzung erlaubt. Standard für Produktion.
# sdxl        -> CreativeML Open Rail+M — kommerzielle Nutzung erlaubt.
# custom_lora -> Lizenz abhängig vom Basis-Modell des LoRA. Vor Produktion prüfen.
is_active:        BooleanField(default=True)
created_at:       DateTimeField(auto_now_add=True)
```

### jobs — Job

```python
id:                UUIDField(primary_key=True)
title:             CharField(max_length=150)
status:            CharField(choices=['draft','queued','running','done','failed','cancelled'])
pipeline_template: ForeignKey(PipelineTemplate, on_delete=PROTECT)
prompt:            TextField()
negative_prompt:   TextField(blank=True)
reference_image:   ImageField(upload_to='jobs/refs/', blank=True)
# Parameter Overrides (None = Template-Default verwenden)
width:             PositiveIntegerField(null=True)
height:            PositiveIntegerField(null=True)
num_images:        PositiveIntegerField(default=1)
model:             CharField(blank=True)
steps:             PositiveIntegerField(null=True)
guidance:          FloatField(null=True)
seed:              BigIntegerField(null=True)
# Tracking
created_by:        ForeignKey(User, on_delete=PROTECT)
celery_chain_id:   CharField(max_length=100, blank=True)
notes:             TextField(blank=True)
started_at:        DateTimeField(null=True)
completed_at:      DateTimeField(null=True)
created_at:        DateTimeField(auto_now_add=True)
# WICHTIG: status=draft -> nur Admin-Aktion setzt status=queued (ADR-11)
# studio_workers dürfen Jobs NICHT selbst starten
```

### jobs — JobStep

```python
id:              UUIDField(primary_key=True)
job:             ForeignKey(Job, related_name='steps', on_delete=CASCADE)
step_type:       CharField(choices=['generate','upscale','vectorize','cmyk_export',
                                    'pod_export','preview_export','mockup_gen','auto_qa'])
order:           PositiveIntegerField()
status:          CharField(choices=['pending','running','done','skipped','failed'])
params:          JSONField(default=dict)   # step-spezifische Overrides
output_asset_id: UUIDField(null=True)     # UUID des erzeugten Assets
started_at:      DateTimeField(null=True)
completed_at:    DateTimeField(null=True)
error_msg:       TextField(blank=True)
```

### jobs — PromptTemplate

```python
id:             UUIDField(primary_key=True)
title:          CharField(max_length=150)
category:       CharField(max_length=60)
base_text:      TextField()
variables:      JSONField(default=dict)   # {'style': '...', 'subject': '...'}
example_output: ImageField(blank=True)
is_public:      BooleanField(default=True)
created_at:     DateTimeField(auto_now_add=True)
```

### bundles — PrintBundle

```python
id:           UUIDField(primary_key=True)
order:        ForeignKey(Order, on_delete=CASCADE)
asset_ids:    JSONField(default=list)    # Liste von Asset-UUIDs
bundle_path:  CharField(max_length=500, blank=True)
format:       CharField(choices=['zip','folder'])
status:       CharField(choices=['pending','building','ready','delivered'])
created_at:   DateTimeField(auto_now_add=True)
```

---

## 4. Celery Tasks

| Task | App | Queue | Trigger | Zweck |
|------|-----|-------|---------|-------|
| `generate_image` | `gpu` | `gpu_queue` | Job-Start Chain | RunPod primary, Vast.ai fallback |
| `upscale_image` | `gpu` | `gpu_queue` | nach generate | Real-ESRGAN 4x via RunPod |
| `vectorize_image` | `postprocess` | `cpu_queue` | conditional | Inkscape CLI + Potrace -> SVG |
| `cmyk_export` | `postprocess` | `cpu_queue` | conditional | Pillow + Ghostscript -> TIFF + PDF/X-4 |
| `pod_export` | `postprocess` | `cpu_queue` | conditional | PNG 300dpi sRGB |
| `preview_export` | `postprocess` | `cpu_queue` | immer | JPG 72dpi 1200px |
| `mockup_gen` | `postprocess` | `cpu_queue` | conditional | Printful Mockup API |
| `auto_qa` | `postprocess` | `cpu_queue` | conditional | CLIP-Score + Blur-Check |
| `notify_studio` | `jobs` | `cpu_queue` | Chain-Ende | Job.status=done setzen |
| `create_printful_order` | `shop` | `cpu_queue` | Stripe Webhook | POST /orders an Printful |
| `create_print_bundle` | `bundles` | `cpu_queue` | Order paid | ZIP auf NAS erstellen |
| `notify_fulfillment_partner` | `partners` | `cpu_queue` | Order bezahlt | E-Mail + optional Webhook an zugewiesenen Partner |
| `push_order_to_channel` | `channels` | `cpu_queue` | Order-Status-Update | Bestellbestätigung an Channel-Webhook pushen |
| `generate_all_mockups` | `postprocess` | `cpu_queue` | Asset-Selektion (Studio) | Printful Mockup API für alle ImageProduct-Einträge eines Bildes aufrufen; setzt mockup_status=ready |

### Pipeline Chain (jobs/services.py)

```python
from celery import chain
from gpu.tasks import generate_image, upscale_image
from postprocess.tasks import (vectorize_image, cmyk_export, pod_export,
                                preview_export, mockup_gen, auto_qa)
from jobs.tasks import notify_studio

def build_pipeline_chain(job_id: str):
    job = Job.objects.get(id=job_id)
    t = job.pipeline_template
    steps = [generate_image.si(job_id)]
    if t.step_upscale:    steps.append(upscale_image.si(job_id))
    if t.step_vectorize:  steps.append(vectorize_image.si(job_id))
    if t.step_cmyk:       steps.append(cmyk_export.si(job_id))
    if t.step_pod_export: steps.append(pod_export.si(job_id))
    steps.append(preview_export.si(job_id))   # immer
    if t.step_mockup:     steps.append(mockup_gen.si(job_id))
    if t.step_auto_qa:    steps.append(auto_qa.si(job_id))
    steps.append(notify_studio.si(job_id))
    return chain(*steps)
```

**Task-Regeln:**
- `.si()` (immutable) in Chains — kein State-Transfer via Return-Value
- Nur UUIDs als Task-Argumente — kein ORM-Objekt serialisieren
- `bind=True, max_retries=3` für externe API-Calls
- Tasks sind idempotent — mehrfaches Ausführen = gleicher Outcome
- Jeder Task schreibt `JobStep.status='running'` beim Start, `'done'/'failed'` am Ende

---

## 5. URL-Routen

### Öffentlich

| URL | View | Hinweis |
|-----|------|---------|
| `/gallery/` | `GalleryListView` | paginate_by=24, `?cat=` Filter |
| `/gallery/<slug>/` | `GalleryDetailView` | nur `is_public=True` |
| `/shop/` | `ProductListView` | |
| `/shop/product/<slug>/` | `ProductDetailView` | |
| `/shop/cart/` | `CartView` | Session-basiert |
| `/shop/checkout/` | `create_checkout_session` (POST) | Stripe Session erstellen |
| `/shop/success/` | `OrderSuccessView` | |
| `/shop/webhook/stripe/` | `stripe_webhook` | **CSRF-exempt, `construct_event()` PFLICHT** |
| `/shop/configure/<slug>/` | `ProductConfiguratorView` | Bild wählen → Produktvorschläge mit Mockups → In Warenkorb |

### Studio (`@login_required`, Gruppe: `studio_workers`)

| URL | View | Hinweis |
|-----|------|---------|
| `/studio/` | `StudioDashboard` | |
| `/studio/job/new/` | `JobCreateView` | |
| `/studio/job/<uuid>/` | `JobDetailView` | HTMX polling alle 3s |
| `/studio/job/<uuid>/results/` | `JobResultsView` | |
| `/studio/job/<uuid>/select/` | `AssetSelectView` (POST) | Bild freigeben → legt ImageProduct-Einträge an → löst generate_all_mockups aus |
| `/studio/jobs/` | `JobListView` | |
| `/studio/prompts/` | `PromptLibraryView` | |

### Admin

`/<CUSTOM_ADMIN_PATH>/` — **Nie `/admin/` als URL-Pfad verwenden**

### Partner-Dashboard (`@login_required`, Gruppe: `print_partners`)

| URL | View | Hinweis |
|-----|------|------|
| `/partner/` | `PartnerDashboard` | Offene Aufträge, letzte Lieferungen |
| `/partner/orders/` | `PartnerOrderListView` | Alle Bestellungen des eingeloggten Partners |
| `/partner/order/<uuid>/` | `PartnerOrderDetailView` | Bestelldetails + Bundle-Download-Link |
| `/partner/order/<uuid>/shipped/` | `PartnerMarkShippedView` (POST) | Tracking-Code eintragen, Status → shipped |

---

## 6. Infrastruktur-Topologie

```
Internet / Browser / Etsy / Stripe
           |
           v HTTPS :443
        [Nginx]  <- TLS-Termination, Static Files, Reverse Proxy
           |
           v HTTP 127.0.0.1:8000
       [Gunicorn — 4 Workers]
           |
    +------+------+
    v             v
[PG 15]       [Redis 7]    <- beide nur 127.0.0.1, nie direkt erreichbar
                  |
                  v  Redis Broker
     +------------------------+
     | Celery gpu-worker x1   |  <- Q: gpu_queue (concurrency=1)
     | Celery cpu-worker x2   |  <- Q: cpu_queue (concurrency=2)
     +------------------------+
           |                  |
     HTTPS API          NFS v4 via Tailscale VPN
           v                  v
    [RunPod EU]         [Synology DS925+]
    [Vast.ai Fallback]  /mnt/agency_nas/
```

**NAS-Ordnerstruktur:**

```
/mnt/agency_nas/
  raw/              <- GPU-Roh-Outputs (vollaufgelöst)
  exports/
    pod/            <- PNG 300dpi sRGB (Printful-ready)
    offset/         <- CMYK TIFF + PDF/X-4 mit 3mm Bleed
    preview/        <- JPG 72dpi max 1200px (Web/Galerie)
    vector/         <- SVG (Inkscape CLI Output)
  gallery/          <- kuratierte öffentliche Bilder
  bundles/          <- ZIP-Druckdatei-Bundles je Order
  backups/
    db/             <- pg_dump täglich 02:00
    media/          <- Django media/ wöchentlich
```

---

## 7. Deployment Workflow: Local -> GitHub -> VPS

**Prinzip: Kein Docker im MVP. Lokal entwickeln, VPS deployen mit einem Kommando.**

### Local Development Setup (einmalig)

```bash
python -m venv venv
source venv/Scripts/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # LOCAL_DEV=true, MOCK_GPU=true setzen
python manage.py migrate          # SQLite lokal
python manage.py createsuperuser
python manage.py runserver        # http://127.0.0.1:8000

# Celery lokal (separates Terminal):
celery -A printbuddy worker -Q cpu_queue --loglevel=info
```

**`MOCK_GPU=true`** -> `generate_image` gibt Placeholder-PNG zurück, kein RunPod-Call.
**Lokale GPU-Tests:** `MOCK_GPU=false` + echte `RUNPOD_API_KEY` wenn GPU-Pipeline getestet werden soll.

### Git-Workflow

```
main              -> Production (VPS) — nur per PR mergen, nie direkt pushen
feature/<thema>   -> Lokal entwickeln + testen -> PR -> main
fix/<thema>       -> Bugfixes, lokal testen -> PR -> main
adr/<nummer>      -> ADR-Commits dokumentieren
```

### SSH-Konfiguration (Windows Dev Machine)

**Wichtig:** VPS ist **NUR via SSH-Config-Alias** erreichbar, **nicht** via direkter IP-Adresse.

**Datei:** `C:\Users\alex\.ssh\config`

```
Host datemyhobby
  HostName datemyhobby.com
  User root
  IdentityFile C:\Users\alex\.ssh\datemyhobby_ssh_key
  IdentitiesOnly yes
```

**Verbindung testen:** `ssh datemyhobby 'echo OK'`

### deploy.sh (auf VPS unter /opt/printbuddy/deploy.sh)

```bash
#!/bin/bash
set -e
cd /opt/printbuddy
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --quiet
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput --clear
sudo systemctl restart gunicorn
sudo systemctl restart celery-gpu celery-cpu
echo "Deploy $(git rev-parse --short HEAD) abgeschlossen"
```

**Aufruf:** `ssh datemyhobby 'bash /opt/printbuddy/deploy.sh'` — läuft in < 5 Minuten.
**Rollback:** `git revert HEAD --no-edit && git push && ssh datemyhobby 'bash /opt/printbuddy/deploy.sh'`

**NIEMALS verwenden:** `ssh root@67.86.108.37` (IP nicht erreichbar, Firewall/Tailscale-only)

### Environment-Variablen (.env.example)

```bash
# Django
SECRET_KEY=                          # >= 50 Zeichen, zufällig
DEBUG=False                          # True nur lokal
ALLOWED_HOSTS=datemyhobby.com
DATABASE_URL=postgres://user:pass@localhost:5432/printbuddy

# Feature Flags
MOCK_GPU=false                       # true = kein RunPod-Call
LOCAL_DEV=false

# Stripe
STRIPE_SECRET_KEY=                   # sk_test_... lokal / sk_live_... VPS
STRIPE_WEBHOOK_SECRET=               # whsec_... aus Stripe Dashboard
STRIPE_PUBLISHABLE_KEY=

# Printful
PRINTFUL_API_KEY=

# RunPod
RUNPOD_API_KEY=
RUNPOD_ENDPOINT_ID=
RUNPOD_UPSCALE_ENDPOINT=

# Vast.ai (Fallback)
VASTAI_API_KEY=

# Etsy
ETSY_API_KEY=
ETSY_API_SECRET=
ETSY_REDIRECT_URI=https://datemyhobby.com/etsy/callback/

# Email
EMAIL_HOST=smtp.mailgun.org
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

---

## 8. Architektur-Entscheidungen (ADRs) — Bindend

| # | Entscheidung | Status | Änderung erfordert |
|---|-------------|--------|-------------------|
| ADR-01 | Django 4.2 LTS (nicht FastAPI/Node.js) | Accepted | Neue ADR + vollständige Migration |
| ADR-02 | PostgreSQL 15 (nicht SQLite in Prod, nicht MySQL) | Accepted | Neue ADR |
| ADR-03 | Celery 5 + Redis 7, zwei Queues: `gpu_queue` / `cpu_queue` | Accepted | Neue ADR |
| ADR-04 | RunPod EU On-Demand + Vast.ai Fallback (kein eigener GPU-Server im MVP) | Accepted | Neue ADR wenn >200 Jobs/Mo |
| ADR-05 | Printful als normiertes Fulfillment-Backend für alle Kanäle | Accepted | Neue ADR |
| ADR-06 | Stripe Hosted Checkout — PCI SAQ A (kein Custom Checkout-UI) | Accepted | **Nie ohne Security-Review** |
| ADR-07 | Synology DS925+ via NFS v4 + Tailscale VPN | Accepted | Neue ADR |
| ADR-08 | Hetzner VPS DE-Datacenter (DSGVO-konform) | Accepted | Neue ADR |
| ADR-09 | Studio App: Django HTML Templates first (HTMX-Upgrade per ADR) | Accepted | Kein SPA ohne ADR |
| ADR-10 | Vektorisierung: Inkscape CLI + Potrace (Open Source, VPS-installierbar) | Accepted | Neue ADR wenn Qualität unzureichend |
| ADR-11 | Jobs starten nur durch Admin-Action — `studio_workers` können nicht starten | Accepted | Sicherheit — nur per ADR ändern |
| ADR-12 | HTMX Polling alle 3s für Studio-Status-Updates (kein WebSocket im MVP) | Accepted | Neue ADR wenn Real-Time kritisch |

**Neue ADR hinzufügen:**
```
git checkout -b adr/13-redis-sentinel
# docs/adr/ADR-13-redis-sentinel.md anlegen
git commit -m "adr: ADR-13 Redis Sentinel für HA"
# PR -> main
```

---

## 9. Coding Standards & Guidelines

### Python / Django

- **Formatierung:** Black (88 Zeichen), isort für Imports. `black .` vor jedem Commit.
- **Models:** UUID Primary Keys überall (`default=uuid.uuid4`). Choices als `models.TextChoices` — kein Magic String.
- **Fat Models:** Business-Logik als Model-Methode oder Manager. Views nur HTTP-Handling.
- **Services Layer:** Komplexe Multi-Model-Logik in `<app>/services.py` (Two Scoops of Django Pattern). Beispiel: `jobs/services.py::build_pipeline_chain()`.
- **Kein Raw SQL:** ORM verwenden. Wenn unvermeidbar: parametrisierte Queries via `connection.execute(sql, [params])` — niemals String-Format.
- **ENV-Config:** Alle Secrets + Config ausschließlich in `.env` via `django-environ`. Niemals in `settings.py` hardcoden. Niemals in Git committen.
- **Migrations:** `makemigrations --name <beschreibung>`. Datenmigrations explizit schreiben, nicht automatisch.
- **Logging:** `logger = logging.getLogger(__name__)` — kein `print()` in Produktion.

### Security (OWASP Django Cheat Sheet)

- `CSRF_COOKIE_SECURE = True` + `SESSION_COOKIE_SECURE = True` in Produktion
- `DEBUG = False` in Produktion — absolutes Verbot, kein Verhandeln
- `ALLOWED_HOSTS` exakt auf Domain gesetzt — kein `*`
- File-Uploads: MIME-Type via Pillow validieren (nicht nur Dateiendung prüfen)
- Stripe Webhook: `stripe.Webhook.construct_event()` immer vor Verarbeitung prüfen — HTTP 400 bei Fehler
- `@login_required` auf **allen** Studio-Views — nie vergessen
- Admin-URL: custom path — nie `/admin/`
- `X_FRAME_OPTIONS = 'DENY'` (Clickjacking-Schutz)
- `SECURE_SSL_REDIRECT = True` in Produktion

### Celery

- `.si()` (immutable signatures) in Chains — kein impliziter State via Return-Value
- Nur UUIDs als Task-Argumente — kein ORM-Objekt serialisieren
- `bind=True, max_retries=3` als Default für externe API-Calls
- Tasks sind **idempotent** — mehrfaches Ausführen = gleicher Outcome
- Jeder Task schreibt `JobStep.status='running'` beim Start und `'done'/'failed'` am Ende

### Git Commits (Conventional Commits)

```
feat:     neue Funktion (z.B. feat: JobCreateView für Studio App)
fix:      Bugfix (z.B. fix: Stripe Webhook Signatur-Fehler)
adr:      Architekturentscheidung (z.B. adr: ADR-13 Redis Sentinel)
chore:    Wartung, Dependency-Update, pip-audit
test:     neuer/geänderter Test
refactor: Umstrukturierung ohne Funktionsänderung
```

---

## 10. Third-Party API Contracts

| API | Env-Keys | Kritische Regel |
|-----|----------|-----------------|
| **Stripe Checkout + Webhook** | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | `construct_event()` **immer** vor Verarbeitung — HTTP 400 bei Fehler |
| **Printful API v2** | `PRINTFUL_API_KEY` | `POST /orders`; retry 3x bei 5xx; `PROTECT` FK auf ProductVariant |
| **RunPod SDK** | `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`, `RUNPOD_UPSCALE_ENDPOINT` | `runpod.run_sync(timeout=300)` — Vast.ai Fallback bei Exception |
| **Vast.ai** | `VASTAI_API_KEY` | Nur als Fallback — automatisch von `generate_image` aktiviert |
| **Etsy Open API v3** | `ETSY_API_KEY`, `ETSY_API_SECRET` | Access Token TTL 3600s; **Refresh Token TTL 90 Tage — in DB speichern!** |
| **Printful Mockup API** | `PRINTFUL_API_KEY` (gleicher Key) | `GET /mockup-generator/create-task/<product-id>` — optional Step |

### Modell-Lizenz-Regeln (Bildrechte)

| Modell | Lizenz | Kommerzieller Verkauf | Interner Einsatz |
|--------|--------|----------------------|------------------|
| `flux_schnell` | Apache 2.0 | ✅ Erlaubt | ✅ |
| `sdxl` | CreativeML Open Rail+M | ✅ Erlaubt | ✅ |
| `custom_lora` | Basis-Modell-Lizenz | ⚠️ Vor Produktion prüfen | ✅ |
| `flux_dev` | Nicht kommerziell | ❌ **Verboten für Verkauf** | ✅ Test/Preview/QA |

**Pflicht:** `PipelineTemplate.default_model` muss für alle Produktions-Templates auf `flux_schnell` oder `sdxl` stehen. `flux_dev` nur in Templates mit `is_active=False` oder explizitem `[DEV]`-Prefix im Namen.

---

## 11. Implementierungsplan — Phasen mit Test-Gates

> Reihenfolge ist bindend. Lokal entwickeln und testen, dann VPS deployen.
> Nächste Phase erst starten wenn Test-Gate der aktuellen Phase bestanden.

### Phase 0 — Local Dev Setup (Tag 1, ~4h)

1. `django-admin startproject printbuddy .`
2. Apps anlegen: `gallery`, `shop`, `jobs`, `studio`, `gpu`, `postprocess`, `bundles`, `etsy`
3. `requirements.txt`: `Django==4.2.*`, `celery`, `redis`, `Pillow`, `stripe`, `runpod`, `django-environ`, `psycopg2-binary`, `black`, `isort`
4. `settings/` splitten: `base.py`, `local.py`, `production.py` + `.env.example`
5. `python manage.py migrate` (SQLite lokal) + Superuser

**Test-Gate:** `python manage.py check` ohne Fehler. Admin erreichbar. GitHub-Repo gepusht.

### Phase 1 — Core Models + Admin (Woche 1, ~1 Tag)

1. Alle Modelle implementieren: `GalleryImage`, `PipelineTemplate`, `Job`, `JobStep`, `PromptTemplate`, `Product`, `ProductVariant`, `Order`, `OrderLine`, `PrintBundle`
2. Admin-Registrierungen: `list_display`, `list_filter`, `search_fields` für alle
3. Custom Admin-Action `start_selected_jobs` auf `JobAdmin`
4. `makemigrations --name initial` + `migrate`

**Test-Gate:** PipelineTemplate anlegen. Job (draft) erstellen. GalleryImage hochladen -> Thumbnail erscheint automatisch.

### Phase 2 — VPS Infrastructure Baseline (Woche 1–2, parallel zu Phase 1)

1. SSH-Key-Only Auth, fail2ban, UFW (22/80/443), unattended-upgrades
2. PostgreSQL 15 + Redis 7 installieren und absichern (localhost-only)
3. Tailscale VPN + NAS-Mount `/mnt/agency_nas/`
4. Nginx + Gunicorn + certbot (HTTPS)
5. GitHub Repo + `deploy.sh` auf VPS
6. Celery systemd-Services (`celery-gpu.service`, `celery-cpu.service`) + Flower mit HTTP-Auth

**Test-Gate:** `ssh user@vps 'bash deploy.sh'` läuft durch. Admin über HTTPS erreichbar. NAS-Mount sichtbar. Celery in Flower als `online`.

### Phase 3 — Gallery Landing Page (Woche 2–3)

1. `GalleryListView` + `GalleryDetailView`
2. `list.html` (Grid + Kategorie-Filter + CTA-Logik) + `detail.html`
3. Nginx-Route konfigurieren

**Test-Gate:** 3 Test-Bilder, `is_public=True`, sichtbar auf `/gallery/`. Filter + CTAs OK. Mobile-Test bestanden.

### Phase 4 — Studio Web App (Woche 3–4)

1. Django-User Gruppe `studio_workers` + Login-View
2. `StudioDashboard`, `JobCreateView`, `JobListView`, `JobDetailView`
3. `JobCreateView` Form: PipelineTemplate-Dropdown, Prompt, Overrides (collapsible)
4. HTMX-Polling auf `job_detail.html` (alle 3s)
5. Admin: `start_selected_jobs` Custom Action

**Test-Gate:** `studio_worker` erstellt Job -> `draft` in DB. Admin startet -> `queued`. `studio_worker` erreicht `/admin/` nicht (403). HTMX-Update ohne Page-Reload.

### Phase 5 — GPU Pipeline (Woche 4–5)

1. `gpu/tasks.py`: `generate_image` (RunPod primary + Vast.ai fallback)
2. `gpu/tasks.py`: `upscale_image`
3. `postprocess/tasks.py`: `pod_export`, `preview_export`, `vectorize_image`, `cmyk_export`
4. `jobs/services.py`: `build_pipeline_chain()`
5. `jobs/tasks.py`: `notify_studio`
6. `MOCK_GPU=true` Pfad für lokale Tests (Placeholder PNG, kein RunPod-Call)

**Test-Gate:** `MOCK_GPU=true`: alle `JobStep.status='done'`, Preview-Datei vorhanden. VPS: echtes Bild unter `/mnt/agency_nas/exports/preview/`. Vast.ai Fallback greift wenn RunPod deaktiviert.

### Phase 6 — Studio Results + Selektion (Woche 5)

1. `JobResultsView` (Grid aller generierten Outputs)
2. `AssetSelectView` (POST: `selected=True` + Kommentar)
3. `PromptLibraryView`

**Test-Gate:** Bilder in Results sichtbar und selektierbar. Status-Update nach ≤ 3s ohne Page-Reload.

### Phase 6.5 — Studio Extended: Knowledge Base (Woche 5–6)

**Status:** ✅ **Completed** (19. Juli 2026)

1. ✅ Knowledge Modelle (`/studio/knowledge/models/`)
   - Ordnerverzeichnis-Struktur mit aufklappbaren `<details>`
   - Alle Produktions-Modelle erklärt (FLUX Schnell, SDXL)
   - Alle Test-Modelle (FLUX Dev mit Lizenz-Warnung)
   - Weitere Open-Source Modelle (SD 1.5, SDXL Turbo, Stable Cascade, PixArt-Σ)
   - Proprietäre Modelle (DALL-E 3, Midjourney, Adobe Firefly)
   - Custom LoRAs erklärt
   - Parameter-Erklärungen (Steps, Guidance, Seed, Negative Prompt, Aspect Ratio)
   - **Alle Pipeline-Typen erklärt:**
     - ✅ Text-to-Image (Implementiert)
     - 🟡 Image-to-Image (In Planung)
     - 🔴 Inpainting (Future)
     - 🔴 ControlNet (Future)
     - 🟡 Multi-Image Compositing (In Planung)
     - ✅ Upscaling Real-ESRGAN (Implementiert)
     - 🔴 Video-Generierung AnimateDiff/SVD (Future)
     - 🔴 3D-Generierung Shap-E (Research)
   - Prompt Engineering Best Practices

2. ✅ Knowledge IT (`/studio/knowledge/it/`)
   - Komponenten-Übersicht (VPS, NAS, RunPod, Tailscale)
   - Django Apps & Models erklärt
   - NAS Ordnerstruktur mit File-Tree Visualisierung
   - Tailscale VPN Konfiguration
   - **"Wo was ändern?" Developer-Guide:**
     - Frontend (Templates, Styling)
     - Backend (Views, Models, Migrations)
     - GPU-Pipeline (Tasks, RunPod)
     - NAS Struktur (Permissions)
     - VPS Server (Nginx, Gunicorn, Celery, systemd)
   - Wichtige Parameter & Environment-Variablen
   - Tech-Stack Vergleich: Was & Warum + Upgrade-Szenarien
   - Konten & Zugänge (Django-Rollen, Linux-User, Synology, Externe Dienste)

3. ✅ Navigation erweitert
   - Studio Nav-Bar: `📚 Modelle` und `⚙️ IT` Links
   - Routes: `/studio/knowledge/models/` und `/studio/knowledge/it/`
   - Views: `knowledge_models`, `knowledge_it` in `studio/views.py`

**Test-Gate:** 
- [x] Knowledge-Seiten im Studio erreichbar
- [x] Alle Modelle (aktuelle + zukünftige) dokumentiert
- [x] Alle Pipeline-Typen mit Status-Badges (✅🟡🔴) erklärt
- [x] Developer-Guide vollständig (wo welche Änderung welche Wirkung hat)
- [x] Aufklappbare Navigation funktioniert ohne JavaScript (HTML5 `<details>`)
- [x] Dark Theme konsistent mit Studio-Design
- [x] Mobile-responsive

**Nächste Phase 6.5 Steps (noch offen):**

#### Priority 1: Projekt-System (2-3 Tage) 🎯 IN ARBEIT

**Ziel:** Jobs und Assets in Projekten organisieren, Team-Kollaboration ermöglichen.

**Implementation:**
1. **Model:** `Project` in `jobs/models.py`
   ```python
   id:            UUIDField(primary_key=True)
   title:         CharField(max_length=120)
   slug:          SlugField(unique=True)
   description:   TextField(blank=True)
   created_by:    ForeignKey(User, on_delete=PROTECT)
   team_members:  ManyToManyField(User, related_name='projects', blank=True)
   is_active:     BooleanField(default=True)
   created_at:    DateTimeField(auto_now_add=True)
   updated_at:    DateTimeField(auto_now=True)
   ```

2. **Model-Erweiterungen:**
   - `Job.project`: ForeignKey(Project, null=True, blank=True, on_delete=SET_NULL)
   - `GalleryImage.project`: ForeignKey(Project, null=True, blank=True, on_delete=SET_NULL)

3. **Migrations:**
   - `makemigrations --name add_project_system`
   - Data Migration: Default-Projekt "Uncategorized" erstellen, alle bestehenden Jobs/Images zuweisen

4. **Studio UI:**
   - `ProjectListView` (`/studio/projects/`)
   - `ProjectDetailView` (`/studio/project/<slug>/`) — Jobs + Assets eines Projekts
   - `ProjectCreateView` — Neues Projekt anlegen
   - `JobListView` erweitern: Projekt-Filter-Dropdown
   - `JobCreateView` erweitern: Projekt-Auswahl-Field
   - `AssetSelectView` erweitern: Projekt-Zuordnung bei Freigabe

5. **Test-Gate:**
   - [ ] Jobs nach Projekt filterbar
   - [ ] Projekt-Detail zeigt alle zugehörigen Jobs + Assets
   - [ ] Team-Members können Projekt sehen aber nicht editieren (später: Permissions)
   - [ ] Asset-Move zwischen Projekten funktioniert

#### Priority 2: Batch-Operationen (1-2 Tage)

**Ziel:** Bulk-Actions für Jobs & Assets — effizienteres Arbeiten bei großen Mengen.

**Implementation:**
1. **Studio UI:**
   - Checkbox-Spalte in `JobListView` + `JobResultsView`
   - "Alle auswählen" / "Auswahl aufheben" Buttons
   - Action-Dropdown: ["In Projekt verschieben", "Löschen", "Status ändern", "Batch-Export"]

2. **Backend:**
   - `studio/views.py`: `bulk_move_to_project(request)` (POST)
   - `studio/views.py`: `bulk_delete_jobs(request)` (POST, soft-delete via `is_deleted` Flag)
   - `studio/views.py`: `bulk_export_assets(request)` → ZIP-Download (Celery Task)

3. **Test-Gate:**
   - [ ] 10 Jobs gleichzeitig in anderes Projekt verschieben < 2s
   - [ ] Bulk-Delete fordert Bestätigung, setzt `is_deleted=True`
   - [ ] Batch-Export erstellt ZIP mit allen Selected Assets

#### Priority 3: Fotografie-Features (3-4 Tage)

**Ziel:** Img2Img Reference-Upload, Multi-Image Compositing, Inpainting.

**Implementation:**

**3.1 Image-to-Image Reference Upload:**
1. `JobCreateView` Template erweitern:
   - File-Upload-Field für `reference_image`
   - Strength-Slider (0.0–1.0, default 0.5)
   - Preview des hochgeladenen Bildes

2. `gpu/tasks.py::generate_image` erweitern:
   - Wenn `Job.reference_image` vorhanden: Base64-encode + an RunPod senden
   - RunPod Endpoint muss Img2Img unterstützen (neuer Endpoint oder Parameter)

3. Test-Gate:
   - [ ] Reference-Image hochladen → in `/mnt/agency_nas/raw/` gespeichert
   - [ ] Img2Img GPU-Job läuft mit korrektem Strength-Parameter
   - [ ] Output zeigt erkennbare Ähnlichkeit zum Input

**3.2 Multi-Image Compositing:**
1. `JobCreateView`: Mehrere Reference-Images hochladen (max 3)
2. `Job.reference_images`: JSONField mit Liste von Pfaden
3. Compositing-Pipeline als neue PipelineTemplate (`category='multi_img_composite'`)
4. RunPod Endpoint: Bilder kombinieren via ControlNet OpenPose + Depth

**3.3 Inpainting mit Mask-Editor (🔴 Complex — später):**
1. Canvas-basierter Mask-Editor (HTML5 Canvas + JavaScript)
2. Mask als PNG speichern, zusammen mit Original an RunPod
3. RunPod Endpoint: Inpainting Model (SD 1.5 Inpainting oder SDXL Inpaint)

#### Priority 4: Quick Adjustments (2-3 Tage)

**Ziel:** Kleine Anpassungen ohne GPU-Rechnung — schnell, CPU-basiert.

**Implementation:**

**4.1 Color-Slider (Pillow CPU-basiert):**
1. `JobResultsView` erweitern: "Quick Adjust" Button je Asset
2. Modal mit Slidern:
   - Brightness (-100 bis +100)
   - Contrast (-100 bis +100)
   - Saturation (-100 bis +100)
   - Sharpness (0 bis 200)
3. `postprocess/tasks.py::quick_color_adjust(asset_id, params)`
4. Preview in Real-Time (JavaScript + Pillow Server-Side)

**4.2 Background Removal:**
1. `rembg` Bibliothek installieren (U2-Net Model, CPU-fähig)
2. Alternative: SAM2 Model via RunPod (GPU-beschleunigt)
3. Button "Remove Background" → Task → Output mit transparentem Hintergrund (PNG)

**4.3 Crop-Tool:**
1. JavaScript Canvas Crop-UI (ähnlich Instagram)
2. Koordinaten an Backend senden
3. Pillow `Image.crop()` → neues Asset erstellen

**Test-Gate:**
- [ ] Color-Adjustments unter 3s Response-Zeit (CPU-Queue)
- [ ] Background-Removal < 10s für 1024x1024 Bild
- [ ] Crop speichert neues Asset, Original bleibt erhalten

#### Priority 5: Vertrieb-Integration (1-2 Tage)

**Ziel:** Printful Mock-API testen, Etsy-Backend checken, weitere Kanäle recherchieren.

**Implementation:**
1. Printful Mocking: `MOCK_PRINTFUL=true` in `.env`, `postprocess/tasks.py` Mock-Responses
2. Etsy API v3: Token-Refresh-Mechanismus testen (TTL 90 Tage)
3. WooCommerce/Shopify: API-Capabilities recherchieren, `SalesChannel` erweitern

#### Priority 6: Backend-Dokumentation (1 Tag)

**Ziel:** Admin-Interface mit `help_text` für alle wichtigen Felder, bessere UX für nicht-technische Admins.

**Implementation:**
1. Alle Models durchgehen: `help_text` hinzufügen
   - `PipelineTemplate.default_model`: "FLUX Schnell (Apache 2.0, kommerziell OK) empfohlen. FLUX Dev nur für Tests!"
   - `Job.status`: "draft = erstellt, queued = wartet auf GPU, running = läuft, done = fertig"
   - `Product.required_export_types`: '["pod", "cmyk"] — welche Dateiformate für Produktion nötig'
2. `JobAdmin`: Custom Action "Start Selected Jobs" mit Bestätigungs-Prompt
3. `OrderAdmin`: Inline für `OrderLine`, `readonly_fields` für Stripe-IDs

**Test-Gate:**
- [ ] Admin-User (nicht Superuser) versteht alle Felder ohne externe Dokumentation
- [ ] Help-Texts erscheinen als Tooltip

### Phase 7 — Merch-Shop (Woche 6–7)

1. `ProductListView`, `ProductDetailView`, `CartView` (Session-basiert)
2. `create_checkout_session` (Stripe, EUR, `shipping_address_collection`)
3. `stripe_webhook` (CSRF-exempt, `construct_event()` Pflicht)
4. `create_printful_order` Celery-Task

**Test-Gate:** Stripe Testmodus: Checkout -> Webhook -> Printful Sandbox Order erstellt. HTTP 400 bei falscher Webhook-Signatur.

### Phase 8 — Vertrieb + Bundles (Woche 7–8)

1. `etsy/listing.py`: `create_listing()`, `upload_listing_image()`, `activate_listing()`
2. `create_print_bundle` Task (ZIP auf NAS, Dateitypen je `required_export_types`)
3. Studio: Etsy-Listing-Action auf ausgewählten Assets

**Test-Gate:** Etsy Draft-Listing aus Studio erstellt. Bundle-ZIP enthält korrekte Dateitypen je `required_export_types`.

### Phase 9 — Go-Live (Ende Woche 8)

Go-Live Blocker (alle müssen True sein):
- [ ] `DEBUG=False` in `.env` Production
- [ ] Stripe Webhook Signatur-Check aktiv (verifiziert mit `stripe-cli`)
- [ ] Alle Secrets in `.env`, `.env` in `.gitignore`, nicht im Repo
- [ ] Admin-URL custom (nicht `/admin/`)
- [ ] Impressum + Datenschutzerklärung erreichbar
- [ ] Backup-Restore einmal erfolgreich auf Staging durchgeführt
- [ ] Stripe Test-Key -> Live-Key eingetragen
- [ ] `pip-audit` ohne kritische CVEs
- [ ] Rollback-Drill: Deploy-Rollback unter 15 Minuten

---

## 12. Was NICHT verändert werden darf (ohne ADR)

- Stripe Webhook URL `/shop/webhook/stripe/` — Änderung erfordert Update in Stripe Dashboard
- Stripe `construct_event()` Signatur-Check — darf nicht deaktiviert oder umgangen werden
- PostgreSQL in Production — kein SQLite, kein MySQL
- Redis `bind 127.0.0.1` — nie direkt aus Internet erreichbar
- `DEBUG=True` in Production — absolutes Verbot
- Job-Start durch `studio_workers` — nur Admin-Action (ADR-11)
- Secrets im Code oder im Git-Repo

---

## 13. Offene ADRs (Proposed — noch keine bindende Entscheidung)

| # | Thema | Optionen | Empfehlung |
|---|-------|---------|-----------|
| ADR-13 | Redis HA | Single-Node vs. Sentinel vs. Cluster | Single-Node bis ~1000 Jobs/Mo |
| ADR-14 | HTMX -> Vue.js | Django+HTMX vs. Vue.js SPA | Nur upgraden wenn HTMX nicht ausreicht |
| ADR-15 | Dedizierter GPU-Server | RunPod On-Demand vs. Hetzner GX2-15 (~€107/Mo) | Dedicated ab >200 regelmäßigen Jobs/Mo |
| ADR-16 | Rechtsform | EU+KUR vs. EU+Regelbesteuerung vs. UG | EU+KUR für MVP empfohlen |
| ADR-17 | CI/CD | Manuell `deploy.sh` vs. GitHub Actions | GitHub Actions ab zweitem Entwickler |
| ADR-18 | Asset-Storage | NAS-first vs. Hetzner Object Storage S3 | S3 wenn NAS-Heimanschluss zum Problem wird |
| ADR-19 | Multi-Channel | `source_channel` CharField vs. FK auf `SalesChannel`-Modell | `SalesChannel` FK — Accepted |
| ADR-20 | Partner-Fulfillment | Printful-only vs. eigene Druckstudios als `FulfillmentPartner` | `FulfillmentPartner`-Modell — Accepted |
