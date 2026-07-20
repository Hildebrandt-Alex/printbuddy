"""
Model Descriptions & Parameter Guidance für Studio Wizard
Wird dynamisch im Frontend angezeigt bei Model-Auswahl
"""

MODEL_DESCRIPTIONS = {
    'flux_schnell': {
        'name': 'FLUX Schnell',
        'license': 'Apache 2.0 — Kommerziell OK ✓',
        'use_case': 'Standard-Generierung für alle Print-Produkte. Ultra-schnell, hochqualitativ, lizenziert für Verkauf.',
        'speed': '⚡⚡⚡ Ultra-Fast (4 Steps)',
        'quality': '★★★★☆ Sehr gut',
        'example_prompt': 'A lone snowboarder carving down an untouched powder slope; the trail behind them disintegrates into cascading pixel voxels of cyan, magenta, and gold, alpine sky crystal-clear, hi-key lighting, large negative space, ultra-sharp 8-k',
        'example_negative': 'blurry, low quality, watermark, text, logo, distorted, deformed',
        'recommended_params': {
            'steps': 4,
            'guidance': 7,
            'width': 1024,
            'height': 1024,
        },
        'param_impact': {
            'steps': '4 Steps: FLUX Schnell ist für 4 Steps optimiert. Mehr = minimal bessere Qualität, aber langsamer.',
            'guidance': '7 (fixed): FLUX Schnell funktioniert am besten mit Guidance 7. Nicht ändern!',
            'size': 'Native: 1024x1024. Andere Auflösungen möglich (512-2048).',
        },
        'endpoint_info': {
            'endpoint': 'black-forest-labs-flux-1-schnell (Public API)',
            'api_url': 'https://api.runpod.ai/v2/black-forest-labs-flux-1-schnell/run',
            'parameters': 'prompt, negative_prompt, seed, num_inference_steps (default: 4), guidance (fixed: 7), image_format (png/jpg), width, height',
        },
        'img2img': {
            'enabled': True,
            'note': 'Image2Image experimentell - Prompt + Reference Image kombinierbar',
        },
        'best_for': ['T-Shirts', 'Poster', 'Grußkarten', 'Rapid Prototyping', 'Batch-Produktion'],
    },
    
    'flux_dev': {
        'name': 'FLUX Dev',
        'license': '⚠️ NICHT für Verkauf! Nur interne Tests/Preview',
        'use_case': 'Hochwertige Test-Generierung. Darf NICHT für kommerzielle Produkte verwendet werden.',
        'speed': '⚡⚡ Mittel (28 Steps)',
        'quality': '★★★★★ Exzellent',
        'example_prompt': 'A masked DJ in a retro space-suit spins translucent vinyl records on an outdoor rooftop, behind them a monolithic LED wall displays swirling pixel blocks that echo the record grooves, cinematic night lighting, subtle RGB glitch, crisp shadows',
        'example_negative': 'cartoon, anime, painting, drawing, low resolution, bad anatomy, deformed, blurry',
        'recommended_params': {
            'steps': 28,
            'guidance': 7,
            'width': 1024,
            'height': 1024,
        },
        'param_impact': {
            'steps': '28 Steps: Optimal für FLUX Dev. 20-40 möglich. Mehr Steps = minimal bessere Details.',
            'guidance': '7 (fixed): FLUX Dev funktioniert am besten mit Guidance 7. Nicht ändern!',
            'size': 'Native: 1024x1024. Exzellente Upscale-Kompatibilität. Bis 2048x2048 möglich.',
        },
        'endpoint_info': {
            'endpoint': 'black-forest-labs-flux-1-dev (Public API)',
            'api_url': 'https://api.runpod.ai/v2/black-forest-labs-flux-1-dev/run',
            'parameters': 'prompt, negative_prompt, seed, num_inference_steps (default: 28), guidance (fixed: 7), image_format (png/jpg), width, height',
        },
        'img2img': {
            'enabled': True,
            'note': 'Image2Image experimentell - Prompt + Reference Image kombinierbar',
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
