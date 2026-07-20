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
        'endpoint_info': {
            'endpoint': 'RUNPOD_FLUX_SCHNELL_ENDPOINT',  # Wird vom User bereitgestellt
            'parameters': 'prompt, num_inference_steps (4-8), guidance_scale (2-5), width, height, seed',
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
        'endpoint_info': {
            'endpoint': 'RUNPOD_FLUX_DEV_ENDPOINT',  # Wird vom User bereitgestellt
            'parameters': 'prompt, num_inference_steps (20-50), guidance_scale (5-10), width, height, seed',
        },
        'best_for': ['QA Testing', 'Preview-Renderings', 'Concept Development (nicht zum Verkauf!)'],
        'warning': '🚫 Lizenz erlaubt KEINEN Verkauf generierter Bilder! Nur für Studio-intern.',
    },
    
    'sdxl': {
        'name': 'SDXL 2.1.1',
        'license': 'CreativeML Open Rail+M — Kommerziell OK ✓',
        'use_case': 'Photorealistische Generierung + Img2Img für Reference-basierte Designs.',
        'speed': '⚡ Langsam (25-50 Steps)',
        'quality': '★★★★★ Exzellent (besonders Fotorealismus)',
        'example_prompt': 'a majestic steampunk dragon soaring through a cloudy sky, intricate clockwork details, golden hour lighting, highly detailed, negative_prompt: blurry, very low quality, deformed, ugly, text, watermark, signature',
        'example_negative': 'blurry, very low quality, deformed, ugly, text, watermark, signature',
        'recommended_params': {
            'steps': 25,
            'refiner_steps': 50,
            'guidance': 7.5,
            'scheduler': 'K_EULER',
            'width': 1024,
            'height': 1024,
            'strength': 0.3,
            'high_noise_frac': 0.8,
        },
        'param_impact': {
            'steps': '25-50 Steps: SDXL 2.1.1 braucht weniger Steps als v1. 25 = gut, 50 = maximale Qualität.',
            'refiner_steps': '30-75: Refiner poliert Details nach dem Base-Model. Höher = feiner, aber langsamer.',
            'guidance': '6.0-9.0: Standard CFG. 7.5 = balanced. <6 = kreativ. >10 = oversaturated.',
            'scheduler': 'K_EULER (empfohlen), DPM++, DDIM. Beeinflusst Sampling-Qualität.',
            'strength': '0.3-0.8: Für Img2Img. 0.3 = nah am Original. 0.8 = starke Veränderung.',
            'high_noise_frac': '0.6-0.9: Wann Refiner aktiviert. 0.8 = Standard Balance.',
        },
        'img2img': {
            'enabled': True,
            'strength_range': '0.3-0.8',
            'strength_impact': '0.3 = nah am Original (nur Details ändern). 0.8 = starke Veränderung (Konzept behalten).',
            'use_cases': ['Logo-Redesign', 'Sketch-to-Image', 'Style Transfer', 'Produkt-Variationen'],
        },
        'endpoint_info': {
            'endpoint': 'vdjnfxf6h8q0ra',
            'parameters': 'prompt, negative_prompt, num_inference_steps (25-50), refiner_inference_steps (30-75), guidance_scale (6-9), scheduler (K_EULER/DPM++/DDIM), strength (0.3-0.8), high_noise_frac (0.6-0.9), width, height, seed, image_url (für Img2Img)',
        },
        'best_for': ['Fotorealistische Produkte', 'Architektur-Renderings', 'Portrait-Fotografie', 'Mockups', 'Hochwertige Prints'],
    },
    
    'face_swap': {
        'name': 'Face Swap (INSwapper)',
        'license': 'Apache 2.0 — Kommerziell OK ✓',
        'use_case': 'Tausche ein Gesicht (Face Image) auf einen anderen Körper/Kontext (Target Image). Kein Prompt benötigt.',
        'speed': '⚡⚡⚡ Ultra-Schnell (kein Diffusion-Prozess)',
        'quality': '★★★★☆ Abhängig von Quell-Bildqualität',
        'example_prompt': 'Nicht benötigt - Face Swap basiert nur auf Bildern',
        'example_negative': '',
        'recommended_params': {
            'face_restore': True,
            'background_enhance': False,
            'face_upsample': True,
            'upscale': 2,
            'blend_ratio': 0.75,
        },
        'param_impact': {
            'face_restore': 'True = Verbessert Gesichtsdetails nach dem Swap (empfohlen)',
            'background_enhance': 'True = Schärft Hintergrund (kann artifacts erzeugen)',
            'face_upsample': 'True = Hochskalierung des Gesichts vor Swap (bessere Qualität)',
            'upscale': '1-4: Skalierungsfaktor. 1 = Original-Größe, 2 = doppelte Auflösung (empfohlen), 4 = 4x (langsam)',
            'blend_ratio': '0.5-1.0: Stärke des Swaps. 0.75 = Natural Blend (empfohlen), 1.0 = Komplett ersetzen',
        },
        'endpoint_info': {
            'endpoint': 'e04sh4ebfrvyrh',
            'parameters': 'face_image (Gesicht), target_image (Zielbild), face_restore (bool), background_enhance (bool), face_upsample (bool), upscale (1-4), blend_ratio (0.5-1.0)',
        },
        'face_swap': True,
        'best_for': ['Personalisierte Merch-Produkte', 'Kundengesicht auf Mockups', 'Marketing-Material', 'Schnelle Varianten'],
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
