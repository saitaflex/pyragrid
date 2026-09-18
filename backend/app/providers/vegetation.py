"""vegetation.py — VegetationProvider interface + AssetFuelClassProvider (§5.1, §5.3)."""
from __future__ import annotations

from app import config


class VegetationProvider:
    def fuel_factor(self, site) -> float:
        raise NotImplementedError


class AssetFuelClassProvider(VegetationProvider):
    """Fuel factor from the asset's declared fuel_class; a land-cover dataset can replace it."""

    def fuel_factor(self, site) -> float:
        return config.FUEL_FACTOR[site.fuel_class]
