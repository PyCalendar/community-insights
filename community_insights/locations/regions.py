"""The regions whose official languages differ from those of their country.

CLDR, which Babel ships, knows the languages of countries and marks some as official in a
region only (``official_regional``), but not in which region. This table names the region
for those that people often write in their GitHub profile. The languages are those that are
official in the region, after Wikipedia's articles on the regions and their languages.
"""

from .region import Region

REGIONS = (
    Region("GB", "WLS", "WLS", ("wales", "cymru"), ("en", "cy")),
    Region("GB", "SCT", "SCT", ("scotland", "alba"), ("en", "gd")),
    Region("GB", "NIR", "NIR", ("northern ireland",), ("en", "ga")),
    Region("ES", "CT", "56", ("catalonia", "catalunya", "cataluna"), ("es", "ca")),
    Region("ES", "PV", "59", ("basque country", "euskadi", "pais vasco"), ("es", "eu")),
    Region("ES", "GA", "58", ("galicia",), ("es", "gl")),
    Region("ES", "VC", "60", ("valencian community", "comunitat valenciana"), ("es", "ca")),
    Region("ES", "IB", "07", ("balearic islands", "illes balears"), ("es", "ca")),
    Region("CA", "QC", "10", ("quebec",), ("fr",)),
    Region("NL", "FR", "02", ("friesland", "fryslan"), ("nl", "fy")),
    Region("IT", "32", "17", ("south tyrol", "sudtirol", "alto adige"), ("it", "de")),
)
BY_NAME = {name: region for region in REGIONS for name in region.names}
BY_GEONAMES = {(region.country, region.geonames): region for region in REGIONS}
BY_CODE = {(region.country, region.code): region for region in REGIONS}
