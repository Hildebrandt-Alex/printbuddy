/**
 * Pipeline Template Admin — Auto-Fill Defaults bei Modell-Wechsel
 * Datei: static/admin/js/pipeline_template_defaults.js
 */
(function () {
  'use strict';

  // Default-Parameter je Modell
  const MODEL_DEFAULTS = {
    flux_schnell: {
      steps: 4,
      guidance: 0,
      width: 1024,
      height: 1024,
      // Schritte: nur Generate + Preview für normalen Workflow
      step_generate: true,
      step_upscale: false,
      step_pod_export: true,
      step_preview: true,
      step_vectorize: false,
      step_cmyk: false,
      step_mockup: false,
      step_auto_qa: false,
    },
    flux_dev: {
      steps: 20,
      guidance: 3.5,
      width: 1024,
      height: 1024,
      step_generate: true,
      step_upscale: false,
      step_pod_export: false,
      step_preview: true,
      step_vectorize: false,
      step_cmyk: false,
      step_mockup: false,
      step_auto_qa: false,
    },
    sdxl: {
      steps: 30,
      guidance: 7.5,
      width: 1024,
      height: 1024,
      step_generate: true,
      step_upscale: false,
      step_pod_export: true,
      step_preview: true,
      step_vectorize: false,
      step_cmyk: false,
      step_mockup: false,
      step_auto_qa: false,
    },
    custom_lora: {
      steps: 30,
      guidance: 7.5,
      width: 1024,
      height: 1024,
      step_generate: true,
      step_upscale: false,
      step_pod_export: true,
      step_preview: true,
      step_vectorize: false,
      step_cmyk: false,
      step_mockup: false,
      step_auto_qa: false,
    },
  };

  function applyDefaults(model) {
    const d = MODEL_DEFAULTS[model];
    if (!d) return;

    // Zahlenfelder
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val;
    };
    setVal('id_default_steps', d.steps);
    setVal('id_default_guidance', d.guidance);
    setVal('id_default_width', d.width);
    setVal('id_default_height', d.height);

    // Checkboxen
    const setCheck = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = val;
    };
    setCheck('id_step_generate',   d.step_generate);
    setCheck('id_step_upscale',    d.step_upscale);
    setCheck('id_step_pod_export', d.step_pod_export);
    setCheck('id_step_preview',    d.step_preview);
    setCheck('id_step_vectorize',  d.step_vectorize);
    setCheck('id_step_cmyk',       d.step_cmyk);
    setCheck('id_step_mockup',     d.step_mockup);
    setCheck('id_step_auto_qa',    d.step_auto_qa);

    // Hinweis einblenden
    let badge = document.getElementById('pb-model-info');
    if (!badge) {
      badge = document.createElement('p');
      badge.id = 'pb-model-info';
      badge.style.cssText = 'margin:.5rem 0;padding:.4rem .75rem;border-radius:4px;font-size:.85rem;font-weight:600;display:inline-block;';
      const sel = document.getElementById('id_default_model');
      sel.parentNode.insertBefore(badge, sel.nextSibling);
    }

    const msgs = {
      flux_schnell: { text: '✅ FLUX Schnell — Apache 2.0, kommerziell erlaubt. Steps 4, Guidance 0.', color: '#14532d', fg: '#86efac' },
      flux_dev:     { text: '⚠️ FLUX Dev — NICHT für Verkauf! Nur Test/Preview.', color: '#78350f', fg: '#fde68a' },
      sdxl:         { text: '✅ SDXL — CreativeML Open Rail+M, kommerziell erlaubt. Steps 30, Guidance 7.5.', color: '#14532d', fg: '#86efac' },
      custom_lora:  { text: '⚠️ Custom LoRA — Lizenz des Basis-Modells vor Produktion prüfen!', color: '#78350f', fg: '#fde68a' },
    };
    const m = msgs[model];
    if (m) {
      badge.textContent = m.text;
      badge.style.background = m.color;
      badge.style.color = m.fg;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const sel = document.getElementById('id_default_model');
    if (!sel) return;

    sel.addEventListener('change', function () {
      applyDefaults(this.value);
    });

    // Beim Laden: aktuelles Modell anzeigen (für Bearbeiten-View)
    if (sel.value) {
      // Nur Badge setzen, keine Werte überschreiben beim Bearbeiten
      const d = MODEL_DEFAULTS[sel.value];
      if (!d) return;
      const msgs = {
        flux_schnell: { text: '✅ FLUX Schnell — Apache 2.0, kommerziell erlaubt.', color: '#14532d', fg: '#86efac' },
        flux_dev:     { text: '⚠️ FLUX Dev — NICHT für Verkauf! Nur Test/Preview.', color: '#78350f', fg: '#fde68a' },
        sdxl:         { text: '✅ SDXL — CreativeML Open Rail+M, kommerziell erlaubt.', color: '#14532d', fg: '#86efac' },
        custom_lora:  { text: '⚠️ Custom LoRA — Lizenz prüfen!', color: '#78350f', fg: '#fde68a' },
      };
      const m = msgs[sel.value];
      if (m) {
        let badge = document.getElementById('pb-model-info');
        if (!badge) {
          badge = document.createElement('p');
          badge.id = 'pb-model-info';
          badge.style.cssText = 'margin:.5rem 0;padding:.4rem .75rem;border-radius:4px;font-size:.85rem;font-weight:600;display:inline-block;';
          sel.parentNode.insertBefore(badge, sel.nextSibling);
        }
        badge.textContent = m.text;
        badge.style.background = m.color;
        badge.style.color = m.fg;
      }
    }
  });
})();
