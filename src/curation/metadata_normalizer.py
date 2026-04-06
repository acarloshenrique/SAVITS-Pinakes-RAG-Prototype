def normalize_record(record):

    normalized = {}

    normalized["title"] = record.get("title", "").strip()

    normalized["year"] = record.get("year")

    normalized["authors"] = record.get("authors", [])

    normalized["doi"] = record.get("doi")

    normalized["abstract"] = record.get("abstract")

    return normalized