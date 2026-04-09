"""Mapping of ingested document filenames to their public source URLs."""

# Maps document names (as stored in Supabase) to their publicly accessible URLs.
# Documents without a known public URL are omitted.
SOURCE_URL_MAP: dict[str, str] = {
    # USGS Mineral Commodity Summaries
    "mcs2025.pdf": "https://pubs.usgs.gov/periodicals/mcs2025/mcs2025.pdf",
    "mcs2026.pdf": "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026.pdf",

    # DOE Reports
    "doe-critical-materials-assessment-2023.pdf": (
        "https://www.energy.gov/sites/default/files/2023-07/"
        "doe-critical-material-assessment_07312023.pdf"
    ),
    "doe-cmm-program-overview-2025.pdf": (
        "https://www.energy.gov/sites/default/files/2025-01/"
        "critical-minerals-materials-program-january2025.pdf"
    ),

    # GAO Reports
    "gao-24-107176.pdf": "https://www.gao.gov/assets/gao-24-107176.pdf",
    "gao-24-106959.pdf": "https://www.gao.gov/assets/gao-24-106959.pdf",

    # CRS Reports
    "R47833.2.pdf": "https://crsreports.congress.gov/product/pdf/R/R47833",
    "IF11226.12.html": "https://crsreports.congress.gov/product/pdf/IF/IF11226",
    "R47982.19.pdf": "https://crsreports.congress.gov/product/pdf/R/R47982",

    # DPA Title III Announcements (war.gov, formerly defense.gov)
    "dpa-6k-additive-2023.html": (
        "https://www.war.gov/News/Releases/Release/Article/3606819/"
        "dod-awards-234-million-to-expand-domestic-capability-to-upcycle-scrap-material/"
    ),
    "dpa-fireweed-mactung-2024.html": (
        "https://fireweedmetals.com/fireweed-metals-corp-awarded-up-to-c35-4-m-"
        "in-joint-us-canadian-government-funding-to-advance-mactung-and-essential-"
        "infrastructure-to-unlock-the-critical-minerals-district-at-macmillan-pass-yukon-t/"
    ),
    "dpa-battery-minerals-2022.html": (
        "https://www.war.gov/News/Releases/Release/Article/2989973/"
        "defense-production-act-title-iii-presidential-determination-for-critical-materi/"
    ),
    "dpa-hypersonics-2023.html": (
        "https://www.war.gov/News/Releases/Release/Article/3317872/"
        "defense-production-act-title-iii-presidential-determination-for-airbreathing-en/"
    ),

    # DFARS
    "dfars-225.7018-final-rule-2024.pdf": (
        "https://www.federalregister.gov/documents/2024/05/30/"
        "2024-11513/defense-federal-acquisition-regulation-supplement"
    ),

    # Industry
    "kennametal-defense.html": "https://www.kennametal.com",
    "kennametal-tungsten-powders.html": "https://www.kennametal.com",
    "gtp-about.html": "https://www.globaltungsten.com",
    "elmet-kep.html": "https://www.elmettechnologies.com",
    "6k-additive.html": "https://www.6kinc.com",
    "rtx-hmi.html": "https://www.rtx.com",

    # Knowledge Graph (special case)
    "Knowledge Graph": None,
}


def get_source_url(filename: str) -> str | None:
    """Get the public URL for a source document.

    Args:
        filename: The document filename.

    Returns:
        Public URL string, or None if not available.
    """
    return SOURCE_URL_MAP.get(filename)


def get_all_sources() -> list[dict]:
    """Get all source documents with their URLs.

    Returns:
        List of dicts with name and url fields.
    """
    return [
        {"name": name, "url": url}
        for name, url in SOURCE_URL_MAP.items()
        if url is not None
    ]
