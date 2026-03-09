"""
Módulo de Integração Semântica para o Projeto SAVITS (Ibict)
Objetivo: Extrair metadados Dublin Core e estruturá-los segundo a Ontologia Pinakes,
garantindo rastreabilidade com identificadores dARK para posterior ingestão no Pinakes.ia.
"""

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DC, RDF, RDFS
import json
from datetime import datetime

# Definindo Namespaces customizados do Ibict
PINAKES = Namespace("http://ontologias.ibict.br/pinakes#")
DARK = Namespace("http://dark.ibict.br/")
SAVITS = Namespace("http://savits.ibict.br/recurso/")

def create_pinakes_graph():
    """Inicializa o Grafo de Conhecimento com os namespaces do Ibict."""
    g = Graph()
    g.bind("dc", DC)
    g.bind("pinakes", PINAKES)
    g.bind("dark", DARK)
    return g

def process_social_technology_record(g: Graph, record: dict):
    """
    Mapeia um registro bruto de Tecnologia Social (Dublin Core) 
    para a Ontologia Pinakes.
    """
    # Gerando um identificador dARK simulado para rastreabilidade
    record_id = record.get("id", "0000")
    dark_uri = URIRef(f"{DARK}ark:/13030/savits{record_id}")
    
    # Adicionando o Tipo da Entidade (Objeto Informacional Complexo)
    g.add((dark_uri, RDF.type, PINAKES.ObjetoInformacional))
    g.add((dark_uri, RDF.type, PINAKES.TecnologiaSocial))
    
    # Mapeamento Dublin Core -> Pinakes
    g.add((dark_uri, DC.title, Literal(record.get("title"))))
    g.add((dark_uri, DC.creator, Literal(record.get("author"))))
    
    # Adicionando Propriedades Específicas do SAVITS e Pilares FAIR/CARE
    g.add((dark_uri, PINAKES.temImpactoSocial, Literal(record.get("impact_area"))))
    g.add((dark_uri, PINAKES.nivelMaturidade, Literal(record.get("maturity_level"))))
    g.add((dark_uri, PINAKES.dataProcessamento, Literal(datetime.now().isoformat())))
    
    # Rastreabilidade e Governança (LGPD)
    g.add((dark_uri, PINAKES.statusLGPD, Literal("Anonimizado")))
    g.add((dark_uri, PINAKES.principioAplicado, Literal("FAIR_AND_CARE")))

    return g

if __name__ == "__main__":
    print("Iniciando pipeline CRISP-DM: Módulo de Compreensão e Preparação de Dados...")
    
    # Simulação de um registro extraído da BDTD ou de um formulário do piloto no DF
    raw_data = {
        "id": "7891",
        "title": "Sistema Híbrido de Purificação de Água para Escolas Rurais no DF",
        "author": "Silva, Maria E.",
        "impact_area": "Educação e Saúde (ODS 3 e 4)",
        "maturity_level": "Piloto Validado"
    }
    
    # 1. Cria o grafo semântico
    pinakes_graph = create_pinakes_graph()
    
    # 2. Processa e mapeia os dados
    process_social_technology_record(pinakes_graph, raw_data)
    
    # 3. Exporta para formato padrão da Web Semântica (Turtle)
    output_path = "../data/pinakes_graph.ttl"
    pinakes_graph.serialize(destination=output_path, format="turtle")
    
    print(f"✅ Grafo gerado com sucesso em: {output_path}")
    print("✅ Identificadores dARK atribuídos.")
    print("✅ Estrutura pronta para ingestão no motor de RAG (Pinakes.ia).")
