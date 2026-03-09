import streamlit as st
import os
from semantic_rag import query_pinakes_knowledge_graph, PinakesIA_Simulador

st.set_page_config(page_title="SAVITS | Pinakes.ia RAG", page_icon="🏛️", layout="centered")

st.title("🏛️ SAVITS - Inteligência Preditiva")
st.subheader("Protótipo de RAG Semântico via Ontologia Pinakes")

st.markdown("""
Este painel demonstra a integração entre **Grandes Modelos de Linguagem (LLMs)** e o **Grafo de Conhecimento Pinakes**, garantindo respostas auditáveis, sem alucinações e em conformidade com a LGPD e princípios FAIR.
""")

st.divider()

user_query = st.text_input("Faça uma pergunta sobre o impacto das Tecnologias Sociais validadas:", 
                           placeholder="Ex: Quais tecnologias atuam na Educação?")

if st.button("Consultar Pinakes.ia"):
    if user_query:
        with st.spinner("Consultando o Grafo de Conhecimento (SPARQL)..."):
            graph_path = os.path.join(os.path.dirname(__file__), "../data/pinakes_graph.ttl")
            context = query_pinakes_knowledge_graph(graph_path, user_query)
            
            llm = PinakesIA_Simulador()
            resposta = llm.synthesize_response(user_query, context)
            
            st.success("✅ Busca Concluída com Sucesso")
            
            st.markdown("### Resposta do Sistema:")
            st.info(resposta)
            
            if context:
                st.markdown("### 🔍 Rastreabilidade dos Dados (Evidência Científica):")
                st.json(context)
    else:
        st.warning("Por favor, insira uma pergunta.")
