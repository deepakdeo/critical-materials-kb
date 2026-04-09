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

    # DOE — Battery and Supply Chain Reports
    "doe-battery-supply-chain-review-2024.pdf": (
        "https://www.energy.gov/sites/default/files/2024-12/"
        "20212024-Four%20Year%20Review%20of%20Supply%20Chains%20for%20the%20"
        "Advanced%20Batteries%20Sector.pdf"
    ),
    "doe-lithium-battery-blueprint-2021.pdf": (
        "https://www.energy.gov/sites/default/files/2021-06/"
        "FCAB%20National%20Blueprint%20Lithium%20Batteries%200621_0.pdf"
    ),
    "doe-supply-chain-readiness-2025.pdf": (
        "https://www.energy.gov/sites/default/files/2025-01/"
        "Identifying_Risks_in_the_Energy_Industrial_Base-"
        "Supply_Chain_Readiness_Levels_vFinalPublication.pdf"
    ),

    # USGS — Minerals Outlook and Maps
    "usgs-sir-2025-5021.pdf": "https://pubs.usgs.gov/sir/2025/5021/sir20255021.pdf",
    "usgs-global-minerals-map-2025.pdf": "https://pubs.usgs.gov/fs/2025/3038/fs20253038.pdf",

    # Intelligence Community
    "ncsc-critical-minerals.pdf": (
        "https://www.dni.gov/files/NCSC/documents/supplychain/"
        "Critical_Minerals_Supply_Chain_Resilience.pdf"
    ),

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


def get_source_url_with_page(
    filename: str, page_numbers: list[int] | None = None,
) -> str | None:
    """Get the public URL for a source document, deep-linked to a page.

    When the source is a direct PDF URL and the chunk has a known page
    number, appends a `#page=N` fragment. Chromium, Firefox, and Safari
    PDF viewers all honor this fragment and jump straight to the page,
    which gives analysts a one-click path from a cited chunk to the
    exact page they need to verify.

    For non-PDF sources (HTML landing pages, company sites, etc.) the
    base URL is returned unchanged — there's no equivalent standard for
    HTML deep-linking.

    Args:
        filename: The document filename as stored in Supabase.
        page_numbers: Optional list of 1-indexed page numbers from the
            chunk's metadata. The first page is used as the anchor.

    Returns:
        Public URL string (possibly with #page=N appended), or None if
        no URL is known for the filename.
    """
    base_url = SOURCE_URL_MAP.get(filename)
    if not base_url:
        return None
    if not page_numbers:
        return base_url
    # Only append a page fragment if the base URL points directly at a PDF.
    # HTML company sites / press releases don't support deep page anchors.
    if not base_url.lower().endswith(".pdf"):
        return base_url
    return f"{base_url}#page={page_numbers[0]}"


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
