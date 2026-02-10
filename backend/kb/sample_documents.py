"""
Sample fact-check and news documents for the knowledge base.
Each entry: title, url, text. Used by ingest.py to seed the vector store.
"""
SAMPLE_DOCUMENTS = [
    {
        "title": "COVID-19 vaccines do not contain microchips",
        "url": "https://example.com/factcheck/covid-vaccine-microchip",
        "text": "Fact-check: COVID-19 vaccines do not contain microchips or tracking devices. The vaccines authorized for use (Pfizer-BioNTech, Moderna, Johnson & Johnson, AstraZeneca) contain only standard vaccine ingredients such as mRNA or viral vector components, lipids, salts, and sugars. There is no technology in any approved vaccine that can track or identify individuals. This claim has been repeatedly debunked by health authorities and fact-checkers worldwide.",
    },
    {
        "title": "Earth is round, not flat",
        "url": "https://example.com/factcheck/earth-shape",
        "text": "The Earth is an oblate spheroid (round), not flat. Evidence includes: satellite imagery, circumnavigation, the curvature of the horizon, gravity, and centuries of astronomy and physics. Flat Earth claims have been refuted by NASA, ESA, and every major scientific institution. Ships disappearing hull-first and different star visibility in different hemispheres are simple observational proofs.",
    },
    {
        "title": "5G networks do not cause COVID-19",
        "url": "https://example.com/factcheck/5g-covid",
        "text": "5G wireless networks do not cause or spread COVID-19. Viruses cannot travel on radio waves or mobile networks. COVID-19 is spread through respiratory droplets from infected people. The 5G and coronavirus conspiracy theory has been debunked by the WHO, FCC, and international health agencies. There is no biological mechanism by which radio waves could create or transmit a virus.",
    },
    {
        "title": "Climate change is primarily driven by human activity",
        "url": "https://example.com/factcheck/climate-human-activity",
        "text": "Scientific consensus, including IPCC reports, states that climate change is primarily driven by human activities, especially greenhouse gas emissions from burning fossil fuels, deforestation, and industry. Natural factors alone cannot explain the observed warming since the mid-20th century. Multiple lines of evidence link rising CO2 and global temperature to human emissions.",
    },
    {
        "title": "Vitamin C does not cure the common cold",
        "url": "https://example.com/factcheck/vitamin-c-cold",
        "text": "Vitamin C does not cure the common cold. Large-scale reviews show that regular vitamin C supplementation may slightly reduce cold duration in some people but does not prevent colds. Megadoses do not provide additional benefit. The claim that vitamin C cures colds is not supported by current medical evidence.",
    },
    {
        "title": "Breaking: Local library extends hours",
        "url": "https://example.com/news/library-hours",
        "text": "The city library will extend its weekend hours starting next month. Saturday hours will be 9 AM to 6 PM and Sunday 12 PM to 5 PM. The change was approved by the library board to improve access for working families. No new funding was required; staff will work on a rotating schedule.",
    },
    {
        "title": "Elections are secure and legitimate",
        "url": "https://example.com/factcheck/election-security",
        "text": "U.S. elections are secure. Multiple layers of security include paper ballots or paper trails, post-election audits, and certification by state and local officials. Widespread fraud claims have been investigated and rejected by courts and election officials from both parties. There is no evidence that voting systems switched or lost votes at scale.",
    },
    {
        "title": "Masks reduce spread of respiratory viruses",
        "url": "https://example.com/factcheck/masks-effectiveness",
        "text": "Masks, especially well-fitted respirators (N95/KN95) and surgical masks, reduce the spread of respiratory viruses including COVID-19 and flu. They work by blocking droplets and aerosols from infected wearers and reducing inhalation by the wearer. CDC and WHO recommend masks in high-transmission settings. Studies show mask mandates are associated with lower case rates when combined with other measures.",
    },
]
