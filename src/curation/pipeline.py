from src.ingestion.openalex_harvester import harvest_openalex
from src.curation.metadata_normalizer import normalize_record


def run_pipeline():

    raw = harvest_openalex()

    cleaned = []

    for r in raw:
        cleaned.append(normalize_record(r))

    return cleaned


if __name__ == "__main__":

    docs = run_pipeline()

    print("Documentos processados:", len(docs))