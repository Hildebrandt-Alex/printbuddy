"""
Model Descriptions & Parameter Guidance für Studio Wizard
Wird dynamisch im Frontend angezeigt bei Model-Auswahl
"""

MODEL_DESCRIPTIONS = {
    'flux_schnell': {
        'name': 'FLUX Schnell',
        'license': 'Apache 2.0 — Kommerziell OK ✓',
        'use_case': 'Standard-Generierung für alle Print-Produkte. Schnell, hochqualitativ, lizenziert für Verkauf.',
        'speed': '⚡⚡⚡ Ultra-Fast (4-8 Steps)',
        'quality': '★★★★☆ Sehr gut',
        'example_prompt': 'A majestic lion wearing a golden crown, oil painting style, dramatic lighting, detailed fur texture',
        'example_negative': 'blurry, low quality, watermark, text, logo, distorted face',
        'recommended_params': {
            'steps': 4,
            'guidance': 3.5,
            'width': 1024,
            'height': 1024,
        },
        'param_impact': {
            'steps': '4-8 Steps: FLUX Schnell ist optimiert für wenige Steps. Mehr Steps = kein Quality-Gewinn!',
            'guidance': '2.0-5.0: Niedrige Guidance (3-4) = kreativer. Höhere Guidance (7+) funktioniert NICHT gut.',
            'size': 'Native: 1024x1024. Andere Auflösungen möglich, aber Qualitätsverlust bei extremen Ratios.',
        },
        'best_for': ['T-Shirts', 'Poster', 'Grußkarten', 'Rapid Prototyping'],
    },
    
    'flux_dev': {
        'name': 'FLUX Dev',
        'license': '⚠️ NICHT für Verkauf! Nur interne Tests/Preview',
        'use_case': 'Hochwertige Test-Generierung. Darf NICHT für kommerzielle Produkte verwendet werden.',
        'speed': '⚡⚡ Mittel (20-30 Steps)',
        'quality': '★★★★★ Exzellent',
        'example_prompt': 'Photorealistic portrait of a cyberpunk hacker, neon lights, rain-soaked city street, cinematic depth of field, 8k quality',
        'example_negative': 'cartoon, anime, painting, drawing, low resolution, bad anatomy, deformed',
        'recommended_params': {
            'steps': 30,
            'guidance': 7.5,
            'width': 1024,
            'height': 1024,
        },
        'param_impact': {
            'steps': '20-50 Steps: Mehr Steps = bessere Details. Dev braucht mehr Iterations als Schnell.',
            'guidance': '5.0-10.0: Standard CFG. Zu hoch (>12) = oversaturated. Zu niedrig (<4) = chaotisch.',
            'size': 'Native: 1024x1024. Exzellente Upscale-Kompatibilität.',
        },
        'best_for': ['QA Testing', 'Preview-Renderings', 'Concept Development (nicht zum Verkauf!)'],
        'warning': '🚫 Lizenz erlaubt KEINEN Verkauf generierter Bilder! Nur für Studio-intern.',
    },
    
    'sdxl': {
        'name': 'SDXL 1.0',
        'license': 'CreativeML Open Rail+M — Kommerziell OK ✓',
        'use_case': 'Photorealistische Generierung + Img2Img für Reference-basierte Designs.',
        'speed': '⚡ Langsam (30-50 Steps)',
        'quality': '★★★★☆ Sehr gut (besonders Fotorealismus)',
        'example_prompt': 'Professional product photography, modern minimalist design, studio lighting, white background, advertisement quality',
        'example_negative': 'amateur, poor lighting, cluttered, low resolution, amateur photography',
        'recommended_params': {
            'steps': 40,
            'guidance': 7.5,
            'width': 1024,
            'height': 1024,
        },
        'param_impact': {
            'steps': '30-50 Steps: SDXL braucht viele Steps für Details. <30 = unfertig aussehend.',
            'guidance': '6.0-9.0: Standard CFG für Balance. <6 = zu kreativ/chaotisch. >10 = zu hart/kontrastreich.',
            'size': 'Native: 1024x1024. Kann auch 768x1344 (Portrait) oder 1344x768 (Landscape).',
        },
        'img2img': {
            'enabled': True,
            'strength_range': '0.3-0.8',
            'strength_impact': '0.3 = nah am Original (nur Details ändern). 0.8 = starke Veränderung (Konzept behalten).',
            'use_cases': ['Logo-Redesign', 'Sketch-to-Image', 'Style Transfer', 'Produkt-Variationen'],
        },
        'best_for': ['Fotorealistische Produkte', 'Architektur-Renderings', 'Portrait-Fotografie', 'Mockups'],
    },
}


def get_model_info(model_key: str) -> dict:
    """Gibt Model-Info für Template-Rendering zurück"""
    return MODEL_DESCRIPTIONS.get(model_key, {
        'name': model_key,
        'license': 'Unbekannt',
        'use_case': 'Keine Beschreibung verfügbar.',
        'example_prompt': '',
        'example_negative': '',
        'recommended_params': {},
        'param_impact': {},
        'best_for': [],
    })


def get_all_models():
    """Gibt Liste aller verfügbaren Modelle zurück"""
    return list(MODEL_DESCRIPTIONS.keys())
