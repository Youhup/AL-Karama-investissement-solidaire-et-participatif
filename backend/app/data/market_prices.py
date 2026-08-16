"""Référentiel de prix de marché indicatifs pour les produits typiques des
contreparties en nature (MAD, prix de détail approximatifs au Maroc).

Utilisé par l'agent d'analyse (check_refund_plan_viability, cf.
agentic_analysis/tools.py) pour situer la valeur unitaire ESTIMÉE PAR LE
PORTEUR : sans ce référentiel, un porteur peut déclarer son huile d'argan
à 800 MAD/L pour gonfler artificiellement le ratio valeur/mise de son plan
de remboursement — la valeur déclarée n'était vérifiée nulle part.

Fourchettes VOLONTAIREMENT larges (qualité artisanale variable, écarts
régionaux) : être hors fourchette n'est pas une preuve, c'est un signal à
interpréter par l'agent puis l'admin. À maintenir par l'équipe : ajouter
une entrée suffit, aucune autre modification de code n'est nécessaire.

- product_keywords : il suffit qu'UN mot-clé (sans accents, insensible à la
  casse) apparaisse dans la description du produit du palier.
- unit_keywords : l'unité du palier doit correspondre à l'un d'eux (égalité,
  ou inclusion pour les mots-clés d'au moins 2 caractères — "kilo" matche
  "kilogramme", mais "g" ne matche pas "kg").
"""

MARKET_PRICE_REFERENCES = [
    {"label": "Huile d'argan", "product_keywords": ("argan",), "unit_keywords": ("litre", "l"), "min_mad": 80, "max_mad": 250},
    {"label": "Safran sec", "product_keywords": ("safran",), "unit_keywords": ("gramme", "g"), "min_mad": 20, "max_mad": 50},
    {"label": "Huile d'olive", "product_keywords": ("olive",), "unit_keywords": ("litre", "l"), "min_mad": 60, "max_mad": 130},
    {"label": "Miel", "product_keywords": ("miel",), "unit_keywords": ("kg", "kilo", "pot"), "min_mad": 80, "max_mad": 350},
    {"label": "Amlou", "product_keywords": ("amlou",), "unit_keywords": ("kg", "kilo", "pot"), "min_mad": 70, "max_mad": 220},
    {"label": "Dattes", "product_keywords": ("datte",), "unit_keywords": ("kg", "kilo"), "min_mad": 20, "max_mad": 180},
    {"label": "Couscous artisanal", "product_keywords": ("couscous",), "unit_keywords": ("kg", "kilo"), "min_mad": 15, "max_mad": 45},
    {"label": "Huile de figue de barbarie", "product_keywords": ("barbarie", "figue"), "unit_keywords": ("ml",), "min_mad": 20, "max_mad": 60},
    {"label": "Eau de rose", "product_keywords": ("rose",), "unit_keywords": ("litre", "l"), "min_mad": 40, "max_mad": 150},
    {"label": "Savon noir", "product_keywords": ("savon",), "unit_keywords": ("kg", "kilo", "pot"), "min_mad": 20, "max_mad": 90},
    {"label": "Fromage de chèvre", "product_keywords": ("fromage", "chevre"), "unit_keywords": ("kg", "kilo"), "min_mad": 80, "max_mad": 220},
    {"label": "Poulet fermier (beldi)", "product_keywords": ("poulet",), "unit_keywords": ("kg", "kilo", "piece", "unite"), "min_mad": 45, "max_mad": 120},
    {"label": "Œufs fermiers", "product_keywords": ("oeuf",), "unit_keywords": ("unite", "piece", "oeuf", "douzaine"), "min_mad": 1, "max_mad": 40},
    {"label": "Agneau / viande ovine", "product_keywords": ("agneau", "mouton", "ovin"), "unit_keywords": ("kg", "kilo"), "min_mad": 70, "max_mad": 140},
    {"label": "Panier de légumes", "product_keywords": ("legume", "panier"), "unit_keywords": ("panier", "unite", "piece"), "min_mad": 30, "max_mad": 120},
    {"label": "Confiture artisanale", "product_keywords": ("confiture",), "unit_keywords": ("pot", "unite", "piece"), "min_mad": 20, "max_mad": 80},
    {"label": "Tapis artisanal", "product_keywords": ("tapis",), "unit_keywords": ("piece", "unite", "tapis"), "min_mad": 250, "max_mad": 6000},
    {"label": "Poterie", "product_keywords": ("poterie", "tajine", "ceramique"), "unit_keywords": ("piece", "unite"), "min_mad": 20, "max_mad": 500},
    {"label": "Panier / vannerie", "product_keywords": ("vannerie", "osier", "couffin"), "unit_keywords": ("piece", "unite"), "min_mad": 25, "max_mad": 200},
]
