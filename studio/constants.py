"""
Studio Constants — Produkt-Typen für Product Wizard
"""

PRODUCT_TYPES = {
    'tshirt_pod': {
        'label': 'T-Shirt (Print-on-Demand)',
        'description': 'Printful POD — direkter Versand an Kunden',
        'pipeline_name': 'POD Standard',  # Muss im Admin existieren
        'exports': ['pod', 'preview'],
        'mockup': True,
        'icon': '👕',
        'category': 'shirt_batch',
        'help_text': 'PNG 300dpi sRGB für Printful. Mockup wird automatisch erstellt.',
    },
    
    'poster_offset': {
        'label': 'Poster (Offset-Druck)',
        'description': 'Professioneller Druck mit CMYK-Farbraum, 3mm Bleed',
        'pipeline_name': 'Offset CMYK',
        'exports': ['cmyk', 'pod', 'preview'],
        'mockup': False,
        'icon': '🖼️',
        'category': 'poster_offset',
        'help_text': 'CMYK TIFF + PDF/X-4 für Druckerei. Auch POD-Backup falls Offset-Druck nicht verfügbar.',
    },
    
    'card_pod': {
        'label': 'Grußkarte',
        'description': 'POD-Karte mit Mockup für Shop',
        'pipeline_name': 'Karte POD',
        'exports': ['pod', 'preview'],
        'mockup': True,
        'icon': '💌',
        'category': 'card_pod',
        'help_text': 'PNG 300dpi sRGB für Printful Karten. Mockup zeigt Karte auf Tisch.',
    },
    
    'vector_art': {
        'label': 'Vektor-Art (SVG)',
        'description': 'Inkscape-Vektorisierung für Laser-Cut & Vinyl',
        'pipeline_name': 'Vektor Export',
        'exports': ['vector', 'preview'],
        'mockup': False,
        'icon': '✂️',
        'category': 'vector_art',
        'help_text': 'SVG via Inkscape CLI + Potrace. Für Cricut, Laser-Cut, Vinyl-Druck.',
    },
    
    'gallery_only': {
        'label': 'Nur Galerie (kein Druck)',
        'description': 'Web-Preview ohne Druckdateien',
        'pipeline_name': None,  # Keine Pipeline — nur Preview-Export
        'exports': ['preview'],
        'mockup': False,
        'icon': '🎨',
        'category': 'custom',
        'help_text': 'Nur JPG 72dpi für Web-Galerie. Keine Druckdateien erstellt.',
    },
}


def get_product_type(product_type_key: str) -> dict:
    """
    Gibt Produkt-Typ-Info zurück für Template-Rendering
    """
    return PRODUCT_TYPES.get(product_type_key, {
        'label': product_type_key,
        'description': 'Unbekannter Produkt-Typ',
        'pipeline_name': None,
        'exports': ['preview'],
        'mockup': False,
        'icon': '❓',
        'category': 'custom',
        'help_text': '',
    })


def get_all_product_types():
    """
    Gibt Liste aller verfügbaren Produkt-Typen zurück
    """
    return list(PRODUCT_TYPES.keys())
