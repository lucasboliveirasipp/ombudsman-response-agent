import streamlit as st
import pandas as pd
import io  # Adicionado para manipulação de bytes para o CSV
from typing import List, Any, Dict, Optional
from docx import Document
from datetime import datetime
from uuid import uuid4
from .config import llm
from feedback_local import MONGO
from feedback_local import get_local_datetime_for_mongo
from .tools import get_time_counter, calc_time_counter

# 1. IMPORTAÇÕES DOS AGENTES DE COMERCIALIZAÇÃO
# ----------------------------------------------------
from .comercializacao.vida.ouvidoria_comercial_global_agent import (
    OuvidoriaGlobalAgent as ComercializacaoGlobalAgent,
)
from .comercializacao.vida.ouvidoria_comercial_sistema_agent import (
    OuvidoriaSistemaAgent as ComercializacaoSistemaAgent,
)
from .comercializacao.vida.ouvidoria_comercial_final_agent import (
    OuvidoriaFinalAgent as ComercializacaoFinalAgent,
)

# ----------------------------------------------------
# 2. IMPORTAÇÕES DOS AGENTES DE SINISTRO (PREVIDÊNCIA - VGBL)
# ----------------------------------------------------
from .sinistro.previdencia.vgbl_acme.ouvidoria_vgbl_global_agent import (
    OuvidoriaVgblGlobalAgent as SinistroPrevidenciaGlobalAgent,
)
from .sinistro.previdencia.vgbl_acme.ouvidoria_vgbl_sistema_agent import (
    OuvidoriaVgblSistemaAgent as SinistroPrevidenciaSistemaAgent,
)
from .sinistro.previdencia.vgbl_acme.ouvidoria_vgbl_final_agent import (
    OuvidoriaVgblFinalAgent as SinistroPrevidenciaFinalAgent,
)

# ----------------------------------------------------
# 3. IMPORTAÇÕES DOS AGENTES DE SINISTRO (VIDA - VIDA VIVA ACME)
# ----------------------------------------------------
from .sinistro.vida.vida_viva_acme.ouvidoria_vida_viva_acme_global_agent import (
    OuvidoriaVidaGlobalAgent as SinistroVidaGlobalAgent,
)
from .sinistro.vida.vida_viva_acme.ouvidoria_vida_viva_acme_sistema_agent import (
    OuvidoriaVidaSistemaAgent as SinistroVidaSistemaAgent,
)
from .sinistro.vida.vida_viva_acme.ouvidoria_vida_viva_acme_final_agent import (
    OuvidoriaVidaFinalAgent as SinistroVidaFinalAgent,
)

# ----------------------------------------------------
# 4. IMPORTAÇÕES DOS AGENTES DE RESGATE
# ----------------------------------------------------
from .resgate.ouvidoria_resgate_global_agent import (
    OuvidoriaResgateAgent as ResgateGlobalAgent,
)
from .resgate.ouvidoria_resgate_sistema_agent import (
    OuvidoriaResgateSistemaAgent as ResgateSistemaAgent,
)
from .resgate.ouvidoria_resgate_final_agent import (
    OuvidoriaResgateFinalAgent as ResgateFinalAgent,
)

# ----------------------------------------------------
# 5. MAPPING DE AGENTES (CONSOLIDADO)
# ----------------------------------------------------
AGENT_MAPPING = {
    "Agente Comercialização": {
        "global": ComercializacaoGlobalAgent,
        "sistema": ComercializacaoSistemaAgent,
        "final": ComercializacaoFinalAgent,
        "agent_name": "comercializacao",
    },
    "Agente Sinistro": {
        "global": SinistroPrevidenciaGlobalAgent,
        "sub_agents": {
            "previdencia": {
                "global": SinistroPrevidenciaGlobalAgent,
                "sistema": SinistroPrevidenciaSistemaAgent,
                "final": SinistroPrevidenciaFinalAgent,
                "display_name": "Previdência(VGBL)",
                "code_key": "previdencia",
            },
            "vida": {
                "global": SinistroVidaGlobalAgent,
                "sistema": SinistroVidaSistemaAgent,
                "final": SinistroVidaFinalAgent,
                "display_name": "VIDA (Vida Viva)",
                "code_key": "vida",
            },
        },
        "agent_name": "sinistro_router",
    },
    "Agente Resgate": {
        "global": ResgateGlobalAgent,
        "sistema": ResgateSistemaAgent,
        "final": ResgateFinalAgent,
        "agent_name": "resgate",
    },
}

AGENT_NAME = "agente_ouvidoria"

config = {}

AGENT_OPTIONS = list(AGENT_MAPPING.keys())

def apply_custom_styles():
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; max-width: 1200px; }
        .header-container {
            background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%);
            color: white; padding: 30px; border-radius: 14px; margin-bottom: 20px;
            text-align: center; box-shadow: 0 4px 15px rgba(30, 58, 138, 0.2);
        }
        .section-title {
            font-size: 20px; font-weight: 700; color: #1E3A8A;
            margin-top: 25px; margin-bottom: 15px; border-left: 5px solid #1E3A8A; padding-left: 10px;
        }
        div.stDownloadButton > button {
            background-color: #1E3A8A !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 0.5rem 2rem !important;
            border: none !important;
            font-weight: bold !important;
        }
        </style>
    """, unsafe_allow_html=True)


def set_sinistro_chosen():
    """Callback para definir que um sub-agente de sinistro foi escolhido."""
    st.session_state["sinistro_chosen"] = True
    if "response" in st.session_state:
        del st.session_state["response"]


def set_agent_and_reset_sinistro():
    """
    Callback para definir o agente principal (lendo de 'agent_type_selector')
    e resetar o estado de escolha do sinistro se o novo agente não for Sinistro.
    """
    new_agent = st.session_state["agent_type_selector"]
    st.session_state["selected_agent_type"] = new_agent

    if new_agent != "Agente Sinistro":
        st.session_state["sinistro_chosen"] = False
        st.session_state["sinistro_type_selector"] = AGENT_MAPPING["Agente Sinistro"][
            "sub_agents"
        ]["previdencia"]["display_name"]

    if "response" in st.session_state:
        del st.session_state["response"]


def initialize_run_state():
    """Garante que sempre tenhamos um ID de execução único e estados iniciais."""
    if "run_id" not in st.session_state:
        st.session_state["run_id"] = str(uuid4())
    if f"feedback_saved_{st.session_state['run_id']}" not in st.session_state:
        st.session_state[f"feedback_saved_{st.session_state['run_id']}"] = False

    if "selected_agent_type" not in st.session_state:
        st.session_state["selected_agent_type"] = AGENT_OPTIONS[0]

    if "sinistro_chosen" not in st.session_state:
        st.session_state["sinistro_chosen"] = False

    if "sinistro_type_selector" not in st.session_state:
        default_sinistro = AGENT_MAPPING["Agente Sinistro"]["sub_agents"][
            "previdencia"
        ]["display_name"]
        st.session_state["sinistro_type_selector"] = default_sinistro


def reset_run_state():
    """Reseta a sessão para uma nova execução, gerando novo ID."""
    st.session_state["run_id"] = str(uuid4())
    if "response" in st.session_state:
        del st.session_state["response"]


def save_feedback(score: int, response_data: Dict[str, Any], agent_name: str = "Agente Desconhecido", justification: str = None):
    """
    Salva o feedback no banco.
    """
    run_id = st.session_state.get("run_id")
    if not run_id:
        st.error("Erro: ID de execução não encontrado.")
        return

    if st.session_state.get(f"feedback_saved_{run_id}", False):
        return

    try:
        collection = MONGO["agente_ouvidoria"]
        response_id = str(uuid4())

        feedback_entry = {
            "timestamp": get_local_datetime_for_mongo(),
            "response_id": response_id,
            "chatbot_response": response_data.get("email_conteudo", ""),
            "user_question": response_data.get("ficha_data", {}),
            "feedback": score,
            "justification": justification # Adicionado para salvar o texto do usuário
        }

        collection.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "agent_name": agent_name,
                    "datetime": get_local_datetime_for_mongo(),
                },
                "$push": {"interactions": feedback_entry},
            },
            upsert=True,
        )

        st.session_state[f"feedback_saved_{run_id}"] = True
        st.toast("✅ Feedback salvo com sucesso!")

    except Exception as e:
        st.error(f"Erro ao salvar feedback: {e}")


def display_response(response: Dict[str, Any]):
    """Exibe o resultado do processamento com opção de exportação para DOCX e CSV."""

    st.subheader("Processamento Concluído")

    elapsed_time = response.get("elapsed_time", "N/A")
    st.info(f"Tempo Total de Processamento: **{elapsed_time}**")

    email_conteudo = response.get("email_conteudo", "N/A")
    email_template_raw = response.get("email_template_raw", "N/A")
    agente_destino = response.get("agente_destino", "N/A")

    st.markdown("---")
    st.subheader("E-mail de Retorno Gerado")

    tab_conteudo, tab_template = st.tabs(["Conteúdo Final", "Template Bruto Utilizado"])

    with tab_conteudo:
        st.markdown("##### E-mail Preenchido (Conteúdo Final)")
        st.text_area(
            f"Corpo do E-mail (Destino: {agente_destino})",
            value=email_conteudo,
            height=400,
        )

        # --- GERAÇÃO DO DOCUMENTO WORD (.DOCX) ---
        try:
            doc = Document()
            doc.add_heading('E-mail de Retorno - Ouvidoria', 0)

            # Adiciona o texto respeitando parágrafos
            for paragrafo in email_conteudo.split('\n'):
                doc.add_paragraph(paragrafo)

            docx_buffer = io.BytesIO()
            doc.save(docx_buffer)
            docx_buffer.seek(0)

            st.download_button(
                label="📥 Baixar E-mail em Word (.docx)",
                data=docx_buffer,
                file_name=f"Email_Retorno_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="download_email_docx"
            )
        except Exception as e:
            st.error(f"Erro ao gerar arquivo Word: {e}")

    with tab_template:
        st.markdown("##### Template Bruto (Com Placeholders)")
        st.code(email_template_raw, language="python")

    st.markdown("### Detalhes da Análise")
    col1, col2 = st.columns(2)

    ficha_data = response.get("ficha_data", {})
    col1.markdown("**Ficha do Chamado (Roteamento):**")
    col1.json(ficha_data)

    sistema_data = response.get("sistema_data", {})
    col2.markdown("**Telas do Sistema (Contrato):**")
    if sistema_data:
        col2.json(sistema_data)
    else:
        col2.warning("Nenhuma extração de Telas do Sistema realizada.")

    st.markdown("---")
    st.markdown("### 📥 Exportar Dados Estruturados (CSV)")

    # --- EXPORTAÇÃO CSV ---
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        try:
            csv_buffer_ficha = io.BytesIO()
            pd.DataFrame([ficha_data]).to_csv(
                csv_buffer_ficha, index=False, sep=";", encoding="utf-8-sig"
            )
            st.download_button(
                label="Download Ficha do Chamado (CSV)",
                data=csv_buffer_ficha.getvalue(),
                file_name="Ficha_Chamado_Extraida.csv",
                mime="text/csv",
                key="download_ficha",
            )
        except Exception as e:
            st.error(f"Erro ao gerar CSV da Ficha: {e}")

    with col_btn2:
        if sistema_data:
            try:
                csv_buffer_sistema = io.BytesIO()
                pd.DataFrame([sistema_data]).to_csv(
                    csv_buffer_sistema, index=False, sep=";", encoding="utf-8-sig"
                )
                st.download_button(
                    label="Download Telas do Sistema (CSV)",
                    data=csv_buffer_sistema.getvalue(),
                    file_name="Telas_Sistema_Extraidas.csv",
                    mime="text/csv",
                    key="download_sistema",
                )
            except Exception as e:
                st.error(f"Erro ao gerar CSV do Sistema: {e}")


def handle_ouvidoria_flow(
    ficha_chamado_file: Any, imagens_pdf_file: Optional[Any], selected_agent_key: str
):
    """Orquestra o fluxo de Ouvidoria, selecionando os agentes com base na chave escolhida e roteando internamente o Sinistro."""

    agent_config = AGENT_MAPPING.get(selected_agent_key)

    if not agent_config or agent_config.get("global") is None:
        st.error(
            f"Agente '{selected_agent_key}' não implementado ou inválido. Por favor, selecione outro."
        )
        return None

    GlobalAgentClass = agent_config["global"]

    SistemaAgentClass = agent_config.get("sistema")
    FinalAgentClass = agent_config.get("final")
    agente_destino = selected_agent_key  # Default para o nome do agente principal

    sub_agent_type = None

    if selected_agent_key == "Agente Sinistro":
        selected_display_name = st.session_state["sinistro_type_selector"]

        # Encontra a chave de código interna ('previdencia' ou 'vida')
        for key, sub_config in agent_config["sub_agents"].items():
            if sub_config["display_name"] == selected_display_name:
                sub_agent_type = key  # 'previdencia' ou 'vida'
                break

        if sub_agent_type:
            sub_agents = agent_config["sub_agents"][sub_agent_type]
            GlobalAgentClass = sub_agents["global"]
            SistemaAgentClass = sub_agents["sistema"]
            FinalAgentClass = sub_agents["final"]
            agente_destino = sub_agents["display_name"]
            st.success(
                f"Roteamento Interno Concluído! Sub-Agente selecionado: **{agente_destino}**"
            )
        else:
            st.error(
                f"Erro de Roteamento: Tipo de Sinistro '{selected_display_name}' não mapeado."
            )
            return None

    st.markdown(f"**Agente Selecionado:** `{selected_agent_key}` ({agente_destino})")

    full_start_time = get_time_counter()
    consolidated_data: Dict[str, Any] = {
        "agent_root_key": selected_agent_key,
        "agent_name_root": agent_config["agent_name"],
    }

    # --- FLUXO 1: AGENTE GLOBAL (ROTEAMENTO/EXTRAÇÃO) ---
    st.subheader(f"1. Agente Global ({agente_destino}): Roteamento e Extração da Ficha")
    global_agent = GlobalAgentClass(files=[ficha_chamado_file])

    with st.spinner(f"Analisando Ficha do Chamado e Roteando ({agente_destino})..."):
        global_state_result = global_agent.process_document(config)

    # Extrair dados do resultado do Agente Global
    agente_destino_flow1 = global_state_result.get("agente_destino", agente_destino)
    ficha_data = global_state_result.get("extracted_data", {})
    template_prefix_global = global_state_result.get("template_prefix", "")

    st.success(
        f"Extração da Ficha Concluída! Destino final (confirmação): **{agente_destino_flow1}**"
    )

    # Verifica se as classes de sistema e final foram corretamente atribuídas
    if SistemaAgentClass is None or FinalAgentClass is None:
        st.error(
            f"Erro de configuração: Classes de Agente Sistema/Final não definidas após o roteamento."
        )
        return None

    # Preenche o consolidated_data com os dados extraídos
    consolidated_data["ficha_data"] = ficha_data
    consolidated_data["agente_destino"] = agente_destino_flow1
    consolidated_data["template_prefix"] = template_prefix_global
    sistema_data = {}

    # --- FLUXO 2: AGENTE SECUNDÁRIO (EXTRAÇÃO DE DADOS DAS TELAS) ---
    st.subheader(
        f"2. Agente Secundário ({agente_destino_flow1.split(' - ')[-1].strip()}): Extração de Dados das Telas"
    )

    if imagens_pdf_file is None:
        st.warning("PDF das Telas do Sistema não fornecido. Extração pulada.")
    else:
        system_agent = SistemaAgentClass(files=[imagens_pdf_file])

        with st.spinner(
            f"Processando PDF das Telas do Sistema para extrair dados do contrato..."
        ):
            sistema_state_result = system_agent.process_document(config)

        # A saída do Agente do Sistema geralmente está em 'extracted_data'
        sistema_data = sistema_state_result.get("extracted_data", {})
        st.success("Extração de Dados das Telas Concluída!")

    consolidated_data["sistema_data"] = sistema_data

    # --- FLUXO 3: AGENTE FINAL (GERAÇÃO DE E-MAIL) ---
    st.subheader(
        f"3. Agente Final ({agente_destino_flow1.split(' - ')[-1].strip()}): Geração de E-mail"
    )

    # Passa o Dicionário Consolidado
    final_agent = FinalAgentClass(consolidated_data)

    with st.spinner("Gerando resposta final e e-mail..."):
        final_state_result = final_agent.process_data(config)

    st.success("Geração de E-mail Concluída!")

    full_time_counter = calc_time_counter(full_start_time)

    final_result_data = final_state_result.get("result", {})

    final_response = {
        "agente_destino": final_state_result.get(
            "agente_destino", agente_destino_flow1
        ),
        "email_conteudo": final_state_result.get(
            "email_conteudo", final_result_data.get("email_conteudo", "N/A")
        ),
        "email_template_raw": final_state_result.get("email_template_raw", "N/A"),
        "ficha_data": ficha_data,
        "sistema_data": sistema_data,
        "elapsed_time": full_time_counter["elapsed_time"],
    }

    return final_response


def build_page(is_authenticated: bool = False):

    initialize_run_state()
    apply_custom_styles()

    selected_agent_key = st.session_state["selected_agent_type"]

    st.markdown("""
        <div class="header-container">
            <h1 style="margin:0;">Agente Ouvidoria</h1>
            <p style="opacity:0.9;">Processamento Inteligente de Chamados e Geração de Respostas</p>
        </div>
    """, unsafe_allow_html=True)

    with st.expander("ℹ️ Como usar este sistema", expanded=False):
        st.markdown("""
        1. 🤖 **Configuração:** Escolha o Agente Principal e, se necessário, o tipo de Sinistro.
        2. 📤 **Documentos:** Faça upload da Ficha (PDF) e das Telas do Sistema (Opcional).
        3. 🚀 **Análise:** O sistema irá rotear, extrair dados e redigir o e-mail de resposta.
        4. 📥 **Exportação:** Baixe o e-mail em Word ou os dados estruturados em CSV.
        
        **Dicas:**
        - Este agente analisa somente as fichas referentes à Ouvidoria. Fichas provenientes do SAC e da Central não serão analisadas de corretamente.
        - Caso os dados não sejam capturados, verifique se os documentos correspondem à opção selecionada. Se forem, clique em "Iniciar Análise e Roteamento" para reiniciar a captura.
        - Seu feedback é essencial! Caso encontre algum problema, utilize o sistema de avaliação ao final da página.     
        """)

    st.markdown('<p class="section-title">⚙️ Configuração do Agente</p>', unsafe_allow_html=True)

    # --- Seletor de Tipo de Agente (Opções consolidadas) ---
    st.selectbox(
        "Selecione o Agente de Destino Principal:",
        options=AGENT_OPTIONS,
        key="agent_type_selector",
        on_change=set_agent_and_reset_sinistro,
    )

    selected_agent_key = st.session_state["selected_agent_type"]

    is_sinistro = selected_agent_key == "Agente Sinistro"

    if is_sinistro:
        sinistro_options = [
            config["display_name"]
            for config in AGENT_MAPPING["Agente Sinistro"]["sub_agents"].values()
        ]

        st.markdown("##### 1. Escolha o Tipo de Sinistro (Previdência/VIDA):")

        st.radio(
            "Selecione o Tipo de Sinistro:",
            options=sinistro_options,
            key="sinistro_type_selector",
            horizontal=True,
            on_change=set_sinistro_chosen,
            # Usa um índice para evitar problemas de re-renderização
            index=(
                sinistro_options.index(st.session_state["sinistro_type_selector"])
                if st.session_state["sinistro_type_selector"] in sinistro_options
                else 0
            ),
        )

        if not st.session_state["sinistro_chosen"]:
            st.info(
                "Por favor, selecione um tipo de sinistro (Previdência ou VIDA) para continuar e carregar os documentos."
            )
            return

    show_document_section = (not is_sinistro) or (
        is_sinistro and st.session_state["sinistro_chosen"]
    )

    if show_document_section:

        step_number = "2." if is_sinistro else "1."
        st.markdown('<p class="section-title">📤 Entrada de Documentos</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            ficha_chamado_file = st.file_uploader(
                "Ficha do Chamado (PDF para Extração)",
                type=["pdf"],
                key="ficha_chamado_file",
            )

        with col2:
            imagens_pdf_file = st.file_uploader(
                "Telas do Sistema (PDF Contendo Imagens/Dados)",
                type=["pdf"],
                key="imagens_pdf_file",
            )

        st.markdown("---")

        is_resgate_unimplemented = (
            selected_agent_key == "Agente Resgate"
            and AGENT_MAPPING["Agente Resgate"]["global"] is None
        )

        botao = st.button(
            "▶️ Iniciar Análise e Roteamento",
            on_click=reset_run_state,
            disabled=(ficha_chamado_file is None) or is_resgate_unimplemented,
        )

        if is_resgate_unimplemented:
            st.warning(
                "O Agente Resgate ainda não está implementado. Selecione Comercialização ou Sinistro."
            )

        if botao and ficha_chamado_file:
            try:
                st.session_state["response"] = handle_ouvidoria_flow(
                    ficha_chamado_file,
                    imagens_pdf_file,
                    selected_agent_key,
                )
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento: {e}")
                st.exception(e)
                st.session_state["response"] = None

        if "response" in st.session_state and st.session_state["response"]:
            st.markdown("---")
            res = st.session_state["response"]
            display_response(res)

            feedback_key = f"feedback_{st.session_state['run_id']}"

            st.markdown("---")
        st.subheader("Avalie esta Análise")

        run_id = st.session_state['run_id']
        feedback_key = f"feedback_widget_{run_id}"

        # Verifica se já foi salvo para mostrar a mensagem de agradecimento
        if st.session_state.get(f"feedback_saved_{run_id}"):
            st.info("✅ Obrigado pelo seu feedback! Ele foi registrado em nosso banco de dados.")
        else:
            # Renderiza o componente de feedback
            score = st.feedback("thumbs", key=feedback_key)

            if score is not None:
                # Captura o nome do agente atual para salvar no log
                current_agent = st.session_state.get("selected_agent_type", "Desconhecido")

                if score == 0:
                    st.warning("Sentimos muito que o resultado não foi o esperado...")
                    justification = st.text_area(
                        "Descreva o erro:",
                        key=f"text_area_{run_id}"
                    )

                    if st.button("Enviar Justificativa", key=f"btn_submit_{run_id}"):
                        # Passando agent_name e justification
                        save_feedback(score=score, response_data=res, agent_name=current_agent, justification=justification)
                        st.rerun()

                # Caso: Feedback Positivo (Score 1) -> Salva direto
                else:
                    save_feedback(score=score, response_data=res, agent_name=current_agent)
                    st.rerun()


if __name__ == "__main__":
    build_page(is_authenticated=True)
