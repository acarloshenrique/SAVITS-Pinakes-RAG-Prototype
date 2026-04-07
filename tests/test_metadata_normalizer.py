from src.curation.metadata_normalizer import normalize_record


def test_normalize_record_enriches_lgpd_and_deia_tags():
    raw = {
        "title": "Inclusao digital em bibliotecas comunitarias",
        "autores": ["Maria Silva"],
        "palavras_chave": ["inclusao digital", "equidade"],
        "dados_pessoais": True,
        "source_uri": "https://brcris.ibict.br/work/123",
    }

    normalized = normalize_record(raw)

    assert normalized["lgpd_status"] == "Controlado"
    assert normalized["lgpd_legal_basis"].lower().startswith("consentimento")
    assert normalized["source_reference"] == "https://brcris.ibict.br/work/123"
    assert normalized["impact_area"], "Impact area should not be empty"
    assert "Inclusao" in normalized["deia_tags"]
    assert normalized["ark_id"].startswith("ark:/13030/savits-")
