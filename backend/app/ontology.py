"""In-memory ontology and utilities for garment attributes.

Provides:
    * Controlled vocabularies (ONTOLOGY)
    * Synonym normalization (SYNONYMS)
    * Heuristic attribute extractor with lightweight caching
    * Confidence scoring for extracted attributes
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AttributeValue:  # simple value object (not DB model)
    family: str
    value: str
    canonical: str


ONTOLOGY: dict[str, set[str]] = {
    # Main garment categories with subcategories
    "category": {
        "jacket", "shirt", "pants", "dress", "skirt", "shoes", "accessories",
        "outerwear", "tops", "bottoms", "activewear", "undergarments", "swimwear"
    },

    # Subcategories for detailed classification
    "subcategory": {
        # Tops subcategories
        "t-shirt", "blouse", "tank-top", "camisole", "sweater", "hoodie", "cardigan",
        "polo", "henley", "crop-top", "tube-top", "halter-top", "wrap-top",

        # Outerwear subcategories
        "blazer", "coat", "parka", "bomber", "denim-jacket", "leather-jacket",
        "windbreaker", "puffer", "trench", "peacoat", "vest", "cape", "poncho",

        # Bottoms subcategories
        "jeans", "chinos", "trousers", "leggings", "shorts", "capris", "cargo-pants",
        "wide-leg", "skinny", "bootcut", "straight-leg", "palazzo", "culottes",

        # Dress subcategories
        "maxi", "midi", "mini", "shift", "wrap", "bodycon", "a-line", "sheath",
        "fit-and-flare", "slip-dress", "shirt-dress", "sweater-dress", "cocktail",

        # Skirt subcategories
        "pencil", "pleated", "circle", "asymmetrical", "high-low", "tiered",

        # Shoe subcategories
        "sneakers", "boots", "heels", "flats", "sandals", "loafers", "oxfords",
        "athletic", "dress-shoes", "ankle-boots", "knee-boots", "platform",
        "wedges", "stilettos", "pumps", "mules", "espadrilles", "clogs",

        # Accessories subcategories
        "belt", "bag", "hat", "scarf", "jewelry", "sunglasses", "watch",
        "handbag", "backpack", "tote", "clutch", "crossbody", "messenger",
        "baseball-cap", "beanie", "fedora", "beret", "bucket-hat",

        # Activewear subcategories
        "sports-bra", "yoga-pants", "running-shorts", "track-jacket", "athletic-tee",
        "compression-wear", "moisture-wicking", "performance-gear",

        # Undergarments subcategories
        "bra", "underwear", "shapewear", "slip", "bodysuit",

        # Swimwear subcategories
        "bikini", "one-piece", "tankini", "swim-shorts", "cover-up", "rash-guard"
    },

    # Fashion eras and decades
    "era": {
        "1920s", "1930s", "1940s", "1950s", "1960s", "1970s", "1980s", "1990s",
        "2000s", "2010s", "2020s", "victorian", "edwardian", "art-deco", "wartime",
        "post-war", "mod", "hippie", "disco", "punk", "new-wave", "grunge",
        "minimalist", "y2k", "boho", "normcore", "athleisure"
    },    # Brand categories and tiers
    "brand": {
        # Luxury brands
        "chanel", "louis-vuitton", "gucci", "prada", "hermes", "dior", "versace", "armani",
        "saint-laurent", "bottega-veneta", "celine", "balenciaga", "givenchy", "valentino",
        "tom-ford", "burberry", "fendi", "loewe", "off-white", "golden-goose",

        # Contemporary/Designer brands
        "theory", "rag-and-bone", "equipment", "isabel-marant", "acne-studios", "ganni",
        "staud", "reformation", "khaite", "toteme", "lemaire", "the-row", "proenza-schouler",
        "mansur-gavriel", "rejina-pyo", "nanushka", "jacquemus", "apc", "mm6",

        # Premium brands
        "j-crew", "banana-republic", "ann-taylor", "club-monaco", "cos", "and-other-stories",
        "everlane", "madewell", "anthropologie", "free-people", "urban-outfitters",
        "zara", "massimo-dutti", "reiss", "whistles", "sezane", "arket",

        # Athletic/Activewear brands
        "nike", "adidas", "lululemon", "athleta", "outdoor-voices", "alo-yoga",
        "girlfriend-collective", "patagonia", "the-north-face", "arc-teryx",
        "canada-goose", "moncler", "stone-island",

        # Denim specialists
        "levi-s", "ag-jeans", "citizens-of-humanity", "frame", "mother", "paige",
        "7-for-all-mankind", "current-elliott", "re-done", "agolde", "grlfrnd",
        "good-american",

        # Fast fashion/Contemporary
        "h-m", "forever-21", "target", "old-navy", "gap", "uniqlo", "muji", "asos",
        "boohoo", "pretty-little-thing", "nasty-gal", "princess-polly", "shein",

        # Vintage/Heritage brands
        "vintage", "deadstock", "champion", "carhartt", "dickies", "ben-davis", "pendleton",
        "ll-bean", "barbour", "filson", "red-wing", "dr-martens", "converse", "vans"
    },

    # Enhanced fit categories
    "fit": {
        "relaxed", "regular", "slim", "oversized", "fitted", "loose", "tailored",
        "cropped", "high-waisted", "low-rise", "mid-rise", "wide-leg", "skinny",
        "straight", "bootcut", "flare", "boyfriend", "girlfriend", "mom-fit",
        "dad-fit", "athletic-fit", "compression", "boxy", "flowing", "structured"
    },

    # Comprehensive material types
    "material": {
        # Natural fibers
        "cotton", "linen", "wool", "silk", "cashmere", "mohair", "alpaca", "angora",
        "hemp", "bamboo", "ramie", "jute", "flax", "merino-wool", "organic-cotton",
        "pima-cotton", "supima-cotton", "egyptian-cotton", "linen-cotton-blend",

        # Animal-derived materials
        "leather", "suede", "patent-leather", "faux-leather", "vegan-leather",
        "fur", "faux-fur", "shearling", "down", "feathers", "pearl", "shell",

        # Synthetic fibers
        "polyester", "nylon", "acrylic", "polyamide", "elastane", "spandex", "lycra",
        "rayon", "viscose", "modal", "tencel", "acetate", "microfiber", "fleece",
        "polyurethane", "polypropylene", "aramid", "kevlar",

        # Denim and cotton blends
        "denim", "chambray", "corduroy", "canvas", "twill", "poplin", "oxford-cloth",
        "jersey", "interlock", "french-terry", "terry-cloth", "velour", "velvet",

        # Technical/Performance materials
        "moisture-wicking", "breathable", "water-resistant", "waterproof", "windproof",
        "anti-microbial", "odor-resistant", "uv-protection", "compression-fabric",
        "stretch-fabric", "quick-dry", "thermal", "insulating", "reflective",

        # Specialty materials
        "sequined", "beaded", "embroidered", "lace", "mesh", "tulle", "chiffon",
        "organza", "taffeta", "satin", "crepe", "georgette", "voile", "gauze",
        "flannel", "ponte", "scuba", "neoprene", "metallic", "holographic",

        # Sustainable materials
        "organic", "recycled", "eco-friendly", "sustainable", "upcycled", "deadstock",
        "hemp-blend", "bamboo-fiber", "tencel-lyocell", "peace-silk", "ahimsa-silk"
    },

    # Enhanced color categories
    "color_primary": {
        "black", "white", "gray", "grey", "charcoal", "silver", "cream", "ivory", "beige", "tan",
        "brown", "chocolate", "camel", "cognac", "rust", "burgundy", "wine", "maroon",
        "red", "crimson", "coral", "pink", "rose", "blush", "fuchsia", "magenta",
        "orange", "peach", "apricot", "salmon", "terracotta", "burnt-orange",
        "yellow", "gold", "mustard", "lemon", "butter", "canary", "amber",
        "green", "olive", "sage", "mint", "emerald", "forest", "lime", "neon-green",
        "blue", "navy", "royal-blue", "sky-blue", "powder-blue", "teal", "turquoise", "aqua",
        "purple", "lavender", "plum", "eggplant", "violet", "lilac", "orchid", "indigo",
        "multicolor", "rainbow", "ombre", "tie-dye", "gradient"
    },

    # Enhanced pattern categories
    "pattern": {
        "solid", "striped", "plaid", "checkered", "gingham", "houndstooth", "tartan",
        "floral", "botanical", "paisley", "polka-dot", "geometric", "abstract",
        "graphic", "logo", "text", "animal-print", "leopard", "zebra", "snake",
        "camouflage", "tribal", "ethnic", "bohemian", "vintage-print", "retro",
        "argyle", "chevron", "herringbone", "pinstripe", "windowpane", "glen-plaid",
        "tie-dye", "ombre", "gradient", "iridescent", "metallic", "holographic",
        "embroidered", "applique", "patchwork", "quilted", "textured", "ribbed"
    },

    # Enhanced style categories
    "style": {
        "vintage", "retro", "classic", "timeless", "contemporary", "modern", "minimalist",
        "maximalist", "bohemian", "boho-chic", "hippie", "grunge", "punk", "goth",
        "preppy", "ivy-league", "collegiate", "nautical", "military", "utilitarian",
        "workwear", "americana", "western", "cowgirl", "country", "rustic",
        "streetwear", "urban", "hip-hop", "skater", "surf", "athletic", "sporty",
        "formal", "business", "professional", "corporate", "cocktail", "evening",
        "casual", "relaxed", "comfortable", "effortless", "laid-back", "weekend",
        "romantic", "feminine", "girly", "sweet", "edgy", "rebellious", "alternative",
        "artistic", "creative", "avant-garde", "experimental", "futuristic", "sci-fi",
        "glamorous", "luxurious", "sophisticated", "elegant", "chic", "polished",
        "trendy", "fashionable", "statement", "bold", "dramatic", "eye-catching"
    },

    # Enhanced seasonal categories
    "season": {
        "spring", "summer", "fall", "autumn", "winter", "all-season", "transitional",
        "resort", "cruise", "holiday", "vacation", "warm-weather", "cool-weather",
        "layering", "lightweight", "heavyweight", "breathable", "insulating"
    },

    # Enhanced occasion categories
    "occasion": {
        "casual", "everyday", "weekend", "work", "business", "professional", "office",
        "formal", "black-tie", "white-tie", "cocktail", "semi-formal", "dressy",
        "evening", "night-out", "date-night", "party", "celebration", "wedding",
        "brunch", "lunch", "dinner", "travel", "vacation", "resort", "beach",
        "outdoor", "hiking", "camping", "sports", "gym", "yoga", "running",
        "loungewear", "sleepwear", "at-home", "comfort", "maternity", "nursing"
    },

    # Enhanced neckline categories
    "neckline": {
        "crew", "round", "scoop", "v-neck", "deep-v", "plunging", "u-neck",
        "square", "sweetheart", "strapless", "off-shoulder", "one-shoulder",
        "halter", "high-neck", "mock-neck", "turtleneck", "cowl", "boat",
        "collar", "polo", "henley", "button-up", "zip-up", "keyhole", "cutout"
    },

    # Enhanced sleeve categories
    "sleeve_length": {
        "sleeveless", "cap-sleeve", "short", "elbow", "three-quarter", "long",
        "extra-long", "bell", "flare", "bishop", "puff", "raglan", "dolman",
        "kimono", "batwing", "fitted", "loose", "wide", "tapered", "cuffed"
    },

    # Size categories
    "size": {
        "xxs", "xs", "s", "m", "l", "xl", "xxl", "xxxl", "one-size", "plus-size",
        "petite", "tall", "regular", "maternity", "0", "2", "4", "6", "8", "10",
        "12", "14", "16", "18", "20", "22", "24", "26", "28", "30", "32"
    },

    # Condition categories for secondhand/vintage
    "condition": {
        "new-with-tags", "new-without-tags", "excellent", "very-good", "good",
        "fair", "worn", "damaged", "vintage", "deadstock", "sample", "prototype"
    },

    # Price tier categories
    "price_tier": {
        "budget", "affordable", "mid-range", "premium", "luxury", "investment",
        "designer", "haute-couture", "vintage", "collectible", "rare"
    }
}

# Synonym mappings for natural language processing
SYNONYMS: dict[str, dict[str, str]] = {
    "category": {
        # Main categories
        "top": "shirt",
        "upper": "shirt",
        "blouse": "shirt",
        "tee": "shirt",
        "sweater": "shirt",
        "hoodie": "shirt",
        "bottom": "pants",
        "trouser": "pants",
        "jean": "pants",
        "pant": "pants",
        "outerwear": "jacket",
        "coat": "jacket",
        "blazer": "jacket",
        "cardigan": "jacket",
        "footwear": "shoes",
        "boot": "shoes",
        "sneaker": "shoes",
        "heel": "shoes",
        "sandal": "shoes",
        "flat": "shoes",
        "accessory": "accessories",
        "bag": "accessories",
        "purse": "accessories",
        "jewelry": "accessories",
        "scarf": "accessories",
        "belt": "accessories",
        "hat": "accessories",
    },

    "subcategory": {
        # Tops synonyms
        "t-shirt": "t-shirt",
        "tee": "t-shirt",
        "tshirt": "t-shirt",
        "tank": "tank-top",
        "cami": "camisole",
        "jumper": "sweater",
        "pullover": "sweater",
        "sweatshirt": "hoodie",

        # Outerwear synonyms
        "jacket": "blazer",
        "suit-jacket": "blazer",
        "winter-coat": "coat",
        "overcoat": "coat",
        "rain-jacket": "windbreaker",
        "down-jacket": "puffer",
        "puffer-jacket": "puffer",
        "trench-coat": "trench",
        "peacoat": "peacoat",
        "waistcoat": "vest",

        # Bottoms synonyms
        "denim": "jeans",
        "jean": "jeans",
        "trouser": "trousers",
        "pant": "trousers",
        "legging": "leggings",
        "tight": "leggings",
        "short": "shorts",
        "bermuda": "shorts",
        "cargo": "cargo-pants",
        "wide-leg-pants": "wide-leg",
        "skinny-jeans": "skinny",
        "bootcut-jeans": "bootcut",
        "straight-jeans": "straight-leg",

        # Dress synonyms
        "maxi-dress": "maxi",
        "midi-dress": "midi",
        "mini-dress": "mini",
        "shift-dress": "shift",
        "wrap-dress": "wrap",
        "bodycon-dress": "bodycon",
        "a-line-dress": "a-line",
        "slip": "slip-dress",

        # Shoe synonyms
        "sneaker": "sneakers",
        "trainer": "sneakers",
        "athletic-shoe": "sneakers",
        "boot": "boots",
        "ankle-boot": "ankle-boots",
        "knee-boot": "knee-boots",
        "high-heel": "heels",
        "pump": "pumps",
        "stiletto": "stilettos",
        "wedge": "wedges",
        "flat-shoe": "flats",
        "sandal": "sandals",
        "loafer": "loafers",
        "oxford": "oxfords",
        "mule": "mules",

        # Accessories synonyms
        "handbag": "bag",
        "purse": "bag",
        "tote-bag": "tote",
        "cross-body": "crossbody",
        "messenger-bag": "messenger",
        "clutch-bag": "clutch",
        "backpack": "backpack",
        "cap": "baseball-cap",
        "hat": "baseball-cap",
        "beanie": "beanie",
        "fedora": "fedora",
        "bucket-hat": "bucket-hat"
    },

    "era": {
        "twenties": "1920s",
        "thirties": "1930s",
        "forties": "1940s",
        "fifties": "1950s",
        "sixties": "1960s",
        "seventies": "1970s",
        "eighties": "1980s",
        "nineties": "1990s",
        "2000": "2000s",
        "2010": "2010s",
        "2020": "2020s",
        "retro": "vintage",
        "antique": "victorian",
        "wwii": "wartime",
        "world-war": "wartime",
        "post-wwii": "post-war",
        "swinging-sixties": "mod",
        "flower-power": "hippie",
        "bohemian": "hippie",
        "1970s": "disco",
        "new-romantic": "new-wave",
        "alternative": "grunge",
        "millennial": "y2k",
        "athletic": "athleisure"
    },

    "brand": {
        # Luxury brand variations
        "chanel": "chanel",
        "lv": "louis-vuitton",
        "louis-v": "louis-vuitton",
        "ysl": "saint-laurent",
        "saint-laurent": "saint-laurent",
        "armani": "armani",
        "giorgio-armani": "armani",
        "emporio-armani": "armani",

        # Contemporary brand variations
        "j-crew": "j-crew",
        "jcrew": "j-crew",
        "banana-republic": "banana-republic",
        "br": "banana-republic",
        "ann-taylor": "ann-taylor",
        "at": "ann-taylor",
        "club-monaco": "club-monaco",
        "cm": "club-monaco",

        # Athletic brand variations
        "nike": "nike",
        "adidas": "adidas",
        "lululemon": "lululemon",
        "lulu": "lululemon",
        "athleta": "athleta",
        "ov": "outdoor-voices",
        "alo": "alo-yoga",
        "gf-collective": "girlfriend-collective",
        "patagonia": "patagonia",
        "tnf": "the-north-face",
        "north-face": "the-north-face",

        # Denim brand variations
        "levis": "levi-s",
        "levi": "levi-s",
        "ag": "ag-jeans",
        "coh": "citizens-of-humanity",
        "citizens": "citizens-of-humanity",
        "frame-denim": "frame",
        "mother-denim": "mother",
        "paige-denim": "paige",
        "7fam": "7-for-all-mankind",
        "7-for-all": "7-for-all-mankind",

        # Fast fashion variations
        "h&m": "h-m",
        "hm": "h-m",
        "f21": "forever-21",
        "forever21": "forever-21",
        "old-navy": "old-navy",
        "on": "old-navy",
        "uniqlo": "uniqlo",
        "muji": "muji",

        # Vintage variations
        "vintage": "vintage",
        "retro": "vintage",
        "antique": "vintage",
        "deadstock": "deadstock",
        "nos": "deadstock"
    },

    "fit": {
        "loose": "relaxed",
        "baggy": "relaxed",
        "roomy": "relaxed",
        "normal": "regular",
        "standard": "regular",
        "classic": "regular",
        "tight": "slim",
        "narrow": "slim",
        "skinny": "slim",
        "big": "oversized",
        "large": "oversized",
        "boxy": "oversized",
        "snug": "fitted",
        "form-fitting": "fitted",
        "wide": "loose",
        "boyfriend": "boyfriend",
        "girlfriend": "girlfriend",
        "mom": "mom-fit",
        "dad": "dad-fit",
        "high-waist": "high-waisted",
        "low-waist": "low-rise",
        "mid-waist": "mid-rise",
        "compression": "compression",
        "athletic": "athletic-fit"
    },

    "material": {
        # Natural fiber synonyms
        "100%-cotton": "cotton",
        "pure-cotton": "cotton",
        "organic-cotton": "organic-cotton",
        "linen": "linen",
        "flax": "linen",
        "wool": "wool",
        "woolen": "wool",
        "merino": "merino-wool",
        "cashmere": "cashmere",
        "silk": "silk",
        "mulberry-silk": "silk",
        "hemp": "hemp",
        "bamboo": "bamboo",

        # Synthetic synonyms
        "poly": "polyester",
        "polyester": "polyester",
        "nylon": "nylon",
        "spandex": "elastane",
        "lycra": "elastane",
        "elastane": "elastane",
        "stretch": "elastane",
        "rayon": "rayon",
        "viscose": "viscose",
        "modal": "modal",
        "tencel": "tencel",
        "synthetic": "synthetic",
        "man-made": "synthetic",
        "artificial": "synthetic",

        # Leather synonyms
        "leather": "leather",
        "genuine-leather": "leather",
        "real-leather": "leather",
        "suede": "suede",
        "patent": "patent-leather",
        "faux-leather": "faux-leather",
        "pleather": "faux-leather",
        "vegan-leather": "vegan-leather",

        # Denim synonyms
        "denim": "denim",
        "jean": "denim",
        "chambray": "chambray",
        "canvas": "canvas",
        "twill": "twill",

        # Performance synonyms
        "moisture-wicking": "moisture-wicking",
        "quick-dry": "quick-dry",
        "breathable": "breathable",
        "waterproof": "waterproof",
        "water-resistant": "water-resistant",
        "windproof": "windproof"
    },

    "color_primary": {
        "grey": "gray",
        "charcoal": "charcoal",
        "off-white": "cream",
        "ivory": "ivory",
        "nude": "beige",
        "tan": "tan",
        "camel": "camel",
        "cognac": "cognac",
        "burgundy": "burgundy",
        "wine": "wine",
        "maroon": "maroon",
        "crimson": "red",
        "coral": "coral",
        "pink": "pink",
        "rose": "rose",
        "blush": "blush",
        "orange": "orange",
        "peach": "peach",
        "salmon": "salmon",
        "yellow": "yellow",
        "mustard": "mustard",
        "gold": "gold",
        "olive": "olive",
        "sage": "sage",
        "mint": "mint",
        "emerald": "green",
        "forest": "green",
        "lime": "lime",
        "navy": "navy",
        "royal": "royal-blue",
        "sky": "sky-blue",
        "powder": "powder-blue",
        "teal": "teal",
        "turquoise": "turquoise",
        "purple": "purple",
        "lavender": "lavender",
        "plum": "plum",
        "violet": "violet"
    },

    "pattern": {
        "plain": "solid",
        "stripe": "striped",
        "check": "checkered",
        "gingham": "gingham",
        "plaid": "plaid",
        "tartan": "tartan",
        "houndstooth": "houndstooth",
        "floral": "floral",
        "flower": "floral",
        "botanical": "botanical",
        "paisley": "paisley",
        "polka-dot": "polka-dot",
        "dots": "polka-dot",
        "geometric": "geometric",
        "abstract": "abstract",
        "graphic": "graphic",
        "logo": "logo",
        "text": "text",
        "animal": "animal-print",
        "leopard": "leopard",
        "zebra": "zebra",
        "snake": "snake",
        "camo": "camouflage",
        "camouflage": "camouflage",
        "tribal": "tribal",
        "ethnic": "ethnic",
        "argyle": "argyle",
        "chevron": "chevron",
        "herringbone": "herringbone",
        "pinstripe": "pinstripe",
        "tie-dye": "tie-dye",
        "tiedye": "tie-dye",
        "ombre": "ombre",
        "gradient": "gradient"
    },

    "style": {
        "retro": "vintage",
        "classic": "classic",
        "timeless": "timeless",
        "modern": "modern",
        "contemporary": "contemporary",
        "minimal": "minimalist",
        "maximalist": "maximalist",
        "boho": "bohemian",
        "bohemian": "bohemian",
        "hippie": "hippie",
        "grunge": "grunge",
        "punk": "punk",
        "goth": "goth",
        "gothic": "goth",
        "preppy": "preppy",
        "ivy": "ivy-league",
        "collegiate": "collegiate",
        "nautical": "nautical",
        "military": "military",
        "utility": "utilitarian",
        "workwear": "workwear",
        "americana": "americana",
        "western": "western",
        "cowgirl": "cowgirl",
        "street": "streetwear",
        "urban": "urban",
        "sporty": "athletic",
        "formal": "formal",
        "business": "business",
        "professional": "professional",
        "cocktail": "cocktail",
        "evening": "evening",
        "casual": "casual",
        "relaxed": "relaxed",
        "comfortable": "comfortable",
        "romantic": "romantic",
        "feminine": "feminine",
        "girly": "girly",
        "edgy": "edgy",
        "rebellious": "rebellious",
        "alternative": "alternative",
        "artistic": "artistic",
        "creative": "creative",
        "glamorous": "glamorous",
        "luxurious": "luxurious",
        "sophisticated": "sophisticated",
        "elegant": "elegant",
        "chic": "chic",
        "trendy": "trendy",
        "fashionable": "fashionable"
    },

    "season": {
        "spring": "spring",
        "summer": "summer",
        "fall": "fall",
        "autumn": "fall",
        "winter": "winter",
        "all-season": "all-season",
        "year-round": "all-season",
        "transitional": "transitional",
        "resort": "resort",
        "cruise": "cruise",
        "holiday": "holiday",
        "vacation": "vacation",
        "warm": "warm-weather",
        "hot": "warm-weather",
        "cool": "cool-weather",
        "cold": "cool-weather"
    },

    "occasion": {
        "everyday": "casual",
        "weekend": "weekend",
        "work": "work",
        "office": "office",
        "business": "business",
        "professional": "professional",
        "formal": "formal",
        "dressy": "dressy",
        "semi-formal": "semi-formal",
        "cocktail": "cocktail",
        "evening": "evening",
        "party": "party",
        "celebration": "celebration",
        "wedding": "wedding",
        "date": "date-night",
        "night-out": "night-out",
        "brunch": "brunch",
        "travel": "travel",
        "vacation": "vacation",
        "beach": "beach",
        "outdoor": "outdoor",
        "sports": "sports",
        "gym": "gym",
        "yoga": "yoga",
        "running": "running",
        "lounge": "loungewear",
        "sleep": "sleepwear",
        "home": "at-home"
    },

    "neckline": {
        "crew": "crew",
        "round": "round",
        "scoop": "scoop",
        "v": "v-neck",
        "vneck": "v-neck",
        "v-neck": "v-neck",
        "deep-v": "deep-v",
        "plunging": "plunging",
        "u-neck": "u-neck",
        "square": "square",
        "sweetheart": "sweetheart",
        "strapless": "strapless",
        "off-shoulder": "off-shoulder",
        "one-shoulder": "one-shoulder",
        "halter": "halter",
        "high-neck": "high-neck",
        "mock": "mock-neck",
        "turtle": "turtleneck",
        "turtleneck": "turtleneck",
        "cowl": "cowl",
        "boat": "boat",
        "collar": "collar",
        "polo": "polo",
        "henley": "henley",
        "button": "button-up",
        "zip": "zip-up",
        "keyhole": "keyhole",
        "cutout": "cutout"
    },

    "sleeve_length": {
        "sleeveless": "sleeveless",
        "tank": "sleeveless",
        "cap": "cap-sleeve",
        "short": "short",
        "elbow": "elbow",
        "three-quarter": "three-quarter",
        "3/4": "three-quarter",
        "long": "long",
        "extra-long": "extra-long",
        "bell": "bell",
        "flare": "flare",
        "bishop": "bishop",
        "puff": "puff",
        "raglan": "raglan",
        "dolman": "dolman",
        "kimono": "kimono",
        "batwing": "batwing"
    }
}


def normalize(family: str, raw: str) -> str | None:
    """Normalize a raw attribute value using synonyms and ontology validation."""
    r = raw.strip().lower()

    # Check if it's already in the ontology
    if family in ONTOLOGY and r in ONTOLOGY[family]:
        return r

    # Check synonyms for this specific family
    if family in SYNONYMS and r in SYNONYMS[family]:
        normalized = SYNONYMS[family][r]
        if family in ONTOLOGY and normalized in ONTOLOGY[family]:
            return normalized

    return None


def families() -> list[str]:
    return list(ONTOLOGY.keys())


def all_values() -> dict[str, list[str]]:
    return {k: sorted(v) for k, v in ONTOLOGY.items()}


_CLASSIFY_CACHE: dict[str, dict[str, list[str]]] = {}
_CLASSIFY_HITS = 0
_CLASSIFY_MISSES = 0


def classify_basic(description: str) -> dict[str, list[str]]:
    """Extract ontology attributes from free-form description using heuristics.

    Goals: low false positive rate, determinism, inexpensive.
    """
    text = description.lower()
    tokens = re.findall(r"[a-zA-Z0-9]+(?:'[a-z]+)?", text)  # Include numbers for years/eras
    token_set = set(tokens)

    out: dict[str, list[str]] = {}

    def add(fam: str, raw: str):
        valn = normalize(fam, raw)
        if not valn:
            return
        out.setdefault(fam, [])
        if valn not in out[fam]:
            out[fam].append(valn)

    fam_matches: dict[str, set[str]] = {}

    def fam_add(fam: str, val: str):
        fam_matches.setdefault(fam, set()).add(val)

    # Token / boundary matches for all families
    for fam in ["category", "subcategory", "era", "brand", "style", "color_primary",
                "pattern", "neckline", "sleeve_length", "material", "fit", "season",
                "occasion", "size", "condition", "price_tier"]:
        for candidate in ONTOLOGY.get(fam, []):
            if " " in candidate or "-" in candidate:
                # Multi-word or hyphenated terms
                escaped = re.escape(candidate)
                if re.search(r"\b" + escaped + r"\b", text):
                    fam_add(fam, candidate)
            else:
                # Single words
                if candidate in token_set:
                    fam_add(fam, candidate)

    # Synonym surfaces - check all synonym families
    for fam, syn_dict in SYNONYMS.items():
        for surf, canon in syn_dict.items():
            surf_matches = (
                (" " in surf or "-" in surf) and
                re.search(r"\b" + re.escape(surf) + r"\b", text)
            ) or (
                " " not in surf and "-" not in surf and surf in token_set
            )
            if surf_matches and canon in ONTOLOGY.get(fam, set()):
                fam_add(fam, canon)

    # Special pattern matching for decades/years
    year_matches = re.findall(r'\b(19|20)\d{2}s?\b', text)
    for year_match in year_matches:
        if year_match.endswith('s'):
            decade = year_match
        else:
            # Convert year to decade (e.g., "1995" -> "1990s")
            year_int = int(year_match)
            decade_start = (year_int // 10) * 10
            decade = f"{decade_start}s"

        if decade in ONTOLOGY.get("era", set()):
            fam_add("era", decade)

    # Brand detection with special handling for common abbreviations
    brand_indicators = ["by", "from", "brand", "label", "designer"]
    for i, token in enumerate(tokens):
        if token in brand_indicators and i + 1 < len(tokens):
            next_token = tokens[i + 1]
            if next_token in ONTOLOGY.get("brand", set()):
                fam_add("brand", next_token)

    # Loose boosts and heuristics
    if "band" in token_set and ("tee" in token_set or "shirt" in token_set or "t" in token_set):
        fam_add("style", "vintage")
    if "graphic" in token_set:
        fam_add("pattern", "graphic")
    if "vintage" in token_set or "retro" in token_set:
        fam_add("style", "vintage")
    if "designer" in token_set or "luxury" in token_set:
        fam_add("price_tier", "luxury")
    if "used" in token_set or "preloved" in token_set or "secondhand" in token_set:
        fam_add("condition", "good")

    # Subcategory to category mapping
    subcategory_to_category = {
        # Tops subcategories -> tops/shirt
        "t-shirt": "shirt", "blouse": "shirt", "tank-top": "shirt", "camisole": "shirt",
        "sweater": "shirt", "hoodie": "shirt", "cardigan": "shirt", "polo": "shirt",
        "henley": "shirt", "crop-top": "shirt", "tube-top": "shirt", "halter-top": "shirt",
        "wrap-top": "shirt",

        # Outerwear subcategories -> jacket
        "blazer": "jacket", "coat": "jacket", "parka": "jacket", "bomber": "jacket",
        "denim-jacket": "jacket", "leather-jacket": "jacket", "windbreaker": "jacket",
        "puffer": "jacket", "trench": "jacket", "peacoat": "jacket", "vest": "jacket",
        "cape": "jacket", "poncho": "jacket",

        # Bottoms subcategories -> pants
        "jeans": "pants", "chinos": "pants", "trousers": "pants", "leggings": "pants",
        "shorts": "pants", "capris": "pants", "cargo-pants": "pants", "wide-leg": "pants",
        "skinny": "pants", "bootcut": "pants", "straight-leg": "pants", "palazzo": "pants",
        "culottes": "pants",

        # Dress subcategories -> dress
        "maxi": "dress", "midi": "dress", "mini": "dress", "shift": "dress",
        "wrap": "dress", "bodycon": "dress", "a-line": "dress", "sheath": "dress",
        "fit-and-flare": "dress", "slip-dress": "dress", "shirt-dress": "dress",
        "sweater-dress": "dress", "cocktail": "dress",

        # Skirt subcategories -> skirt
        "pencil": "skirt", "pleated": "skirt", "circle": "skirt", "asymmetrical": "skirt",
        "high-low": "skirt", "tiered": "skirt",

        # Shoe subcategories -> shoes
        "sneakers": "shoes", "boots": "shoes", "heels": "shoes", "flats": "shoes",
        "sandals": "shoes", "loafers": "shoes", "oxfords": "shoes", "athletic": "shoes",
        "dress-shoes": "shoes", "ankle-boots": "shoes", "knee-boots": "shoes",
        "platform": "shoes", "wedges": "shoes", "stilettos": "shoes", "pumps": "shoes",
        "mules": "shoes", "espadrilles": "shoes", "clogs": "shoes"
    }

    # If we found subcategories, infer main categories
    if "subcategory" in fam_matches:
        for subcat in fam_matches["subcategory"]:
            if subcat in subcategory_to_category:
                main_cat = subcategory_to_category[subcat]
                fam_add("category", main_cat)

    # Category single-selection (prioritize most specific)
    if "category" in fam_matches and len(fam_matches["category"]) > 1:
        priority = ["dress", "jacket", "shoes", "skirt", "pants", "shirt", "accessories",
                   "outerwear", "tops", "bottoms", "activewear", "undergarments", "swimwear"]
        for p in priority:
            if p in fam_matches["category"]:
                fam_matches["category"] = {p}
                break

    # Style consolidation - avoid too many style tags
    if "style" in fam_matches and len(fam_matches["style"]) > 3:
        # Keep only the most specific/important styles
        priority_styles = ["vintage", "formal", "casual", "minimalist", "bohemian",
                          "streetwear", "workwear", "preppy", "athletic", "romantic"]
        kept_styles = []
        for style in priority_styles:
            if style in fam_matches["style"]:
                kept_styles.append(style)
                if len(kept_styles) >= 3:
                    break
        if kept_styles:
            fam_matches["style"] = set(kept_styles)

    # Add all matches to output
    for fam, vals in fam_matches.items():
        for v in sorted(vals):
            add(fam, v)

    return out


def classify_basic_cached(description: str) -> dict[str, list[str]]:
    global _CLASSIFY_HITS, _CLASSIFY_MISSES
    key = description.strip().lower()
    cached = _CLASSIFY_CACHE.get(key)
    if cached is not None:
        _CLASSIFY_HITS += 1
        return cached
    _CLASSIFY_MISSES += 1
    result = classify_basic(description)
    if len(_CLASSIFY_CACHE) > 2048:  # simple size bound
        _CLASSIFY_CACHE.clear()
        _CLASSIFY_HITS = 0
        _CLASSIFY_MISSES = 0
    _CLASSIFY_CACHE[key] = result
    return result


def classify_cache_stats() -> dict[str, float | int]:
    total = _CLASSIFY_HITS + _CLASSIFY_MISSES
    hit_rate = (_CLASSIFY_HITS / total) if total else 0.0
    return {
        "size": len(_CLASSIFY_CACHE),
        "hits": _CLASSIFY_HITS,
        "misses": _CLASSIFY_MISSES,
        "hit_rate": round(hit_rate, 4),
    }


def clear_classify_cache() -> None:
    global _CLASSIFY_HITS, _CLASSIFY_MISSES
    _CLASSIFY_CACHE.clear()
    _CLASSIFY_HITS = 0
    _CLASSIFY_MISSES = 0


def attribute_confidences(
    description: str, attrs: dict[str, list[str]]
) -> dict[tuple[str, str], float]:
    """Assign heuristic confidences to extracted attributes.

    Scoring (capped at 0.95): base 0.55; +0.2 if first mention < token 30; +0.1 repeated;
    +0.05 if family in strong-cue set.
    """
    text = description.lower()
    tokens = re.findall(r"[a-zA-Z]+(?:'[a-z]+)?", text)
    conf: dict[tuple[str, str], float] = {}
    for fam, values in attrs.items():
        for v in values:
            base = 0.55
            occurrences = [i for i, t in enumerate(tokens) if t == v]
            if occurrences and occurrences[0] < 30:
                base += 0.2
            if len(occurrences) > 1:
                base += 0.1
            if fam in {"pattern", "style", "color_primary"}:
                base += 0.05
            if base > 0.95:
                base = 0.95
            conf[(fam, v)] = round(base, 3)
    return conf
