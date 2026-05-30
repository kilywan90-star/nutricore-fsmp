"""
FSMP Registry Loader — loads NMPA registration data into the product matching engine.

Data source: NMPA Special Food Registration Database (ypzsx.gsxt.gov.cn)
Compiled via CIRS Group FSMP Registration List (https://www.cirs-group.com)
Last updated: 2026 Q1 (310 total registrations known, 264 extracted)

Format of registration numbers:
  TY20175001 — Foreign product (imported)
  TY20185001 — Domestic product (5th digit = 5/6/7 indicates domestic year variant)
"""

import json
from pathlib import Path
from typing import Optional

from ..models.fsmp_product import FSMPProduct


_registry_cache: Optional[list[FSMPProduct]] = None


def _classify_fsmp_category(name: str) -> str:
    """Classify FSMP product category from product name keywords."""
    if '全营养' in name:
        if any(kw in name for kw in ['糖尿病', '肾病', '肝病', '肿瘤', '肺病', '苯丙酮尿症']):
            return 'specific_complete'
        return 'complete'
    if '蛋白质组件' in name:
        return 'modular'
    if '碳水化合物组件' in name:
        return 'modular'
    if '电解质' in name:
        return 'modular'
    if '脂肪组件' in name:
        return 'modular'
    if '增稠' in name:
        return 'modular'
    if '流质' in name:
        return 'incomplete'
    if any(kw in name for kw in ['氨基酸', '代谢障碍']):
        return 'specific_complete'
    if '婴儿' in name:
        return 'specific_complete'
    return 'complete'


def _extract_features(name: str, manufacturer: str) -> list[str]:
    """Extract special features from product name."""
    features = []
    kw_map = {
        'diabetes': ['糖尿病'],
        'renal': ['肾病'],
        'hepatic': ['肝病'],
        'immune_modulation': ['免疫', 'ω-3', 'Omega-3'],
        'low_residue': ['短肽', '要素'],
        'high_mct': ['MCT', '中链'],
        'fiber_enriched': ['膳食纤维', '纤维'],
        'high_protein': ['高蛋白'],
        'hydrolyzed': ['水解'],
    }
    for feat, keywords in kw_map.items():
        if any(kw in name for kw in keywords):
            features.append(feat)
    return features


def load_registry() -> list[FSMPProduct]:
    """Load FSMP product registry from JSON and convert to engine models."""
    global _registry_cache

    if _registry_cache is not None:
        return _registry_cache

    registry_path = Path(__file__).parent.parent.parent.parent / 'knowledge' / 'fsmp_registry_combined.json'
    if not registry_path.exists():
        # Fallback to MVP seed data
        from ..seed.fsmp_products import get_mvp_products
        return get_mvp_products()

    with open(registry_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    products = []
    for item in raw:
        name = item['product_name']
        # Clean product name — remove registration marks
        name_clean = name.replace('®', '').strip()

        cat = _classify_fsmp_category(name_clean)
        features = _extract_features(name_clean, item['manufacturer'])

        # Determine target population
        if '婴儿' in name_clean:
            target = 'infant'
        elif '1-10' in name_clean or '儿童' in name_clean:
            target = '1-10'
        else:
            target = 'adult'

        # Detect protein source from name
        prot_src = 'casein'  # default
        if '乳清' in name_clean or 'whey' in name_clean.lower():
            prot_src = 'whey'
        elif '水解' in name_clean or 'hydrolys' in name_clean.lower():
            prot_src = 'hydrolysate'
        elif '大豆' in name_clean or 'soy' in name_clean.lower():
            prot_src = 'soy'
        elif '氨基酸' in name_clean or 'amino' in name_clean.lower():
            prot_src = 'amino_acid'

        products.append(FSMPProduct(
            nmpa_registration_no=item['registration_no'],
            brand_name=name_clean,
            manufacturer=item['manufacturer'],
            category=cat,
            target_population=target,
            energy_density_kcal_per_100ml=100,  # defaults; fill from detailed spec when available
            protein_source=prot_src,
            protein_content_g_per_100ml=4.0,
            carb_source='',
            fat_source='',
            special_features=features,
            hospital_channel='',
        ))

    _registry_cache = products
    return products


def get_product_by_regno(reg_no: str) -> Optional[FSMPProduct]:
    """Look up a specific FSMP product by NMPA registration number."""
    products = load_registry()
    for p in products:
        if p.nmpa_registration_no == reg_no:
            return p
    return None


def get_registry_stats() -> dict:
    """Return statistics about the loaded registry."""
    products = load_registry()
    cats = {}
    for p in products:
        cats[p.category] = cats.get(p.category, 0) + 1
    return {
        'total_products': len(products),
        'categories': cats,
        'source': 'NMPA Special Food Registration Database (ypzsx.gsxt.gov.cn)',
    }
