import requests

OPENALEX_URL = "https://api.openalex.org/works"

def harvest_openalex(query="information science", per_page=20):
    
    params = {
        "search": query,
        "per_page": per_page
    }

    r = requests.get(OPENALEX_URL, params=params)
    data = r.json()

    results = []

    for work in data["results"]:

        record = {
            "title": work.get("title"),
            "year": work.get("publication_year"),
            "authors": [
                a["author"]["display_name"]
                for a in work.get("authorships", [])
            ],
            "doi": work.get("doi"),
            "abstract": work.get("abstract_inverted_index")
        }

        results.append(record)

    return results


if __name__ == "__main__":

    docs = harvest_openalex()

    print("Documentos coletados:", len(docs))