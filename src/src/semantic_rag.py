"""
Módulo de Recuperação Semântica (RAG) para o Projeto SAVITS
Objetivo: Consultar a Ontologia Pinakes via SPARQL e utilizar um LLM 
para sintetizar respostas baseadas exclusivamente em evidências validadas.
"""

from rdflib import Graph
import os

class PinakesIA_Simulador:
    def synthesize_response(self, question, context_data):
        print("\n🧠 [Pinakes.ia] A processar contexto semântico...")
        if not context_data:
            return "Não encontrei evidências validadas na base de Tecnologias Sociais para responder a esta questão. (Prevenção de Alucinação Ativa)"
        
        return f"Com base nos dados estruturados do Ibict: A tecnologia '{context_data['titulo']}' desenvolvida por '{context_data['autor']}' atua na área de '{context_data['impacto']}'. O seu nível de maturidade é '{context_data['maturidade']}' e os dados estão conformes à LGPD ({context_data['lgpd']})."

def query_pinakes_knowledge_graph(graph_path, search_term):
    """
    Executa uma query SPARQL rigorosa no Grafo de Conhecimento.
    Isto garante que a IA apenas acede a dados FAIR e estruturados.
    """
    g = Graph()
    # Verifica se o arquivo existe antes de tentar fazer o parse
    if os.path.exists(graph_path):
        g.parse(graph_path, format="turtle")
    else:
        return {}
    
    query = f"""
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX pinakes: <http://ontologias.ibict.br/pinakes#>
    
    SELECT ?titulo ?autor ?impacto ?maturidade ?lgpd
    WHERE {{
        ?entidade a pinakes:TecnologiaSocial ;
                  dc:title ?titulo ;
                  dc:creator ?autor ;
                  pinakes:temImpactoSocial ?impacto ;
                  pinakes:nivelMaturidade ?maturidade ;
                  pinakes:statusLGPD ?lgpd .
                  
        FILTER(CONTAINS(LCASE(?impacto), LCASE("{search_term}")) || CONTAINS(LCASE(?titulo), LCASE("{search_term}")))
    }}
    """
    
    results = g.query(query)
    
    extracted_context = {}
    for row in results:
        extracted_context = {
            "titulo": str(row.titulo),
            "autor": str(row.autor),
            "impacto": str(row.impacto),
            "maturidade": str(row.maturidade),
            "lgpd": str(row.lgpd)
        }
        break 
        
    return extracted_context
