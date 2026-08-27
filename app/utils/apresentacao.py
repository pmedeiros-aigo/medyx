"""apresentacao, os textos institucionais que acompanham todo número.

Substitui o antigo utils/ui.py (Streamlit): aqui ficam só as funções PURAS que
montam rótulo, período, carimbo e linha de justificativa. Nenhum widget,
nenhum framework, a API serve estas strings como JSON e o front vanilla as
imprime. Léxico: LEXICO_PRODUTO.md (linguagem de processo, nunca de pessoa).

Regra: estas funções FORMATAM o que os motores calcularam; nenhuma delas
calcula ou decide nada (Lei 1).
"""
from __future__ import annotations

import pandas as pd

import config

_MESES_PT = ("jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez")


def mes_ano(data: str) -> str:
    """'2025-05-01' -> 'mai/25' (abreviação em português, independente de locale)."""
    ts = pd.Timestamp(data)
    return f"{_MESES_PT[ts.month - 1]}/{ts.strftime('%y')}"


def rotulo_exibicao(area: str) -> str:
    """Nome da área na TELA. O CSV da classificação fala a língua do pipeline.

    Tradução, não renomeação: o motor continua carimbando "GO", e nada do que
    foi calibrado sobre esse rótulo precisa ser revalidado. Área sem tradução
    definida sai como está — o mapa é exceção, não obrigação.
    """
    return config.ROTULOS_AREA.get(area, area)


def perfil_area(area: str) -> str | None:
    """A linha que diz o que distingue esta área das vizinhas, para o `title`
    da opção do seletor. `None` quando não há caracterização definida."""
    return config.PERFIS_AREA.get(area)


def rotulo_area(area: str, n_comparaveis: int, n_total: int) -> str:
    """Rótulo da área no seletor: nome, n comparáveis / total (+ grupo pequeno).

    COMPARÁVEIS, não "elegíveis": é a mesma palavra do chip de recorte e da
    estatística do cabeçalho, e o mesmo conjunto (quem tem volume para sustentar
    comparação). Um número, uma palavra — antes o 58 aparecia como "elegíveis" no
    seletor, "comparáveis" no chip com 63, e ninguém sabia se eram dois recortes
    ou dois nomes para um.
    """
    if area == config.AREA_INDEFINIDA:
        return f"{rotulo_exibicao(area)} ({n_total})"
    rotulo = f"{rotulo_exibicao(area)} · {n_comparaveis} comparáveis / {n_total}"
    if n_comparaveis < config.N_MINIMO_P75:
        rotulo += " · grupo pequeno"
    return rotulo


def subtitulo_area(n_total: int, rotulo_janela: str,
                   janela_ini: str, janela_fim: str) -> str:
    """Subtítulo do cabeçalho da página: '64 cooperados na área'.

    A JANELA saiu daqui (14/ago): ela ganhou controle próprio na faixa de
    filtros, que mostra o intervalo escolhido a poucos centímetros acima. A
    linha repetia, com outra grafia, o que o seletor já dizia — e ainda
    reaparecia no carimbo de proveniência, no rodapé. Três vezes a mesma
    informação numa tela só.

    Os argumentos de janela continuam na assinatura de propósito: a linha volta
    a carregá-los se a página um dia for exportada sem o chassi (PDF), onde o
    seletor não existe para dizer o período.
    """
    return f"{n_total} cooperado{'' if n_total == 1 else 's'} na área"


def periodo_texto(rotulo_janela: str, janela_ini: str, janela_fim: str) -> str:
    """Período colado em todo número: '· 12m · mai/25–abr/26'."""
    return f"· {rotulo_janela} · {mes_ano(janela_ini)}–{mes_ano(janela_fim)}"


def carimbo_proveniencia(janela_ini: str, janela_fim: str, base: str,
                         gatilho: str, alvo: str, confianca: float) -> str:
    """Carimbo do rodapé, governança visível como texto, em toda resposta."""
    return (
        f"pipeline {config.PIPELINE_VERSAO} · "
        f"dados {mes_ano(janela_ini)}–{mes_ano(janela_fim)} · {base} · "
        f"classificação {config.CLASSIFICACAO_VERSAO} · "
        f"gatilho {gatilho} · alvo {alvo} · confiança {confianca:.0%}"
    )


def linha_justificativa(area: str, n_comparaveis: int, base: str,
                        gatilho_efetivo: str | None, alvo: str,
                        n_em_revisao: int = 0) -> dict:
    """'Contra quem, em que base, sob que régua' — em dois níveis.

    Uma linha de justificativa por PÁGINA, não uma por componente. E ela só
    carrega, à vista, o que não está visível em outro lugar da tela:

      resumo   área · n · base · classificação
      detalhes gatilho, referência, exclusões por sub-perfil, referência de doc

    Gatilho e referência saíram do resumo porque já estão nos chips do topo e no
    bloco Análise da barra lateral; repeti-los numa terceira superfície não
    informa, só empurra o resto da frase para fora do campo de leitura.
    """
    exclusoes = " · ".join(
        f"{flag.removeprefix('sub_').replace('_', ' ')} em {area_regra}"
        for flag, area_regra, _ in config.EXCLUSOES_SUBPERFIL
    )
    gatilho_txt = gatilho_efetivo if gatilho_efetivo else "não aplicável (grupo pequeno)"
    return {
        # Sem a versão da classificação: o status de homologação é GOVERNANÇA, e
        # o lugar dela é o banner da página e o carimbo de proveniência, não a
        # linha que diz contra quem se compara. Repetida aqui, empurrava para
        # fora do campo de leitura justamente o que a linha existe para dizer.
        "resumo": f"Comparado com: {area} · n={n_comparaveis} comparáveis · {base}",
        "detalhes": [
            {"rotulo": "Gatilho", "valor": gatilho_txt},
            {"rotulo": "Referência de adequação", "valor": alvo},
            {"rotulo": "Excluídos da construção da referência",
             "valor": f"pares de sub-perfil: {exclusoes}"},
            # A fila de triagem clínica passa a ser contável na tela. Antes só
            # aparecia quem já estava fora da construção da referência, e três
            # dos quatro casos da fila não apareciam em lugar nenhum.
            {"rotulo": "Classificação em revisão",
             "valor": ("nenhum cooperado desta área" if not n_em_revisao else
                       f"{n_em_revisao} cooperado"
                       f"{'s' if n_em_revisao != 1 else ''} na fila de triagem "
                       "clínica; a classificação está sob revisão, o número não")},
        ],
    }


def traduzir_percentil(rotulo_posicao: str) -> str:
    """'P98' -> 'acima de 98% dos cooperados da área'.

    Ajuste 2 do handoff: percentil nunca viaja sem tradução. Mas a tradução é
    PRECISA, não aproximada: "9 em cada 10" arredondava P92 e P98 para a mesma
    frase, e é entre eles que a conversa com o médico acontece. E o léxico do
    produto diz PARES, não "colegas": o peer group é uma construção do método,
    não uma relação social.

    Rótulo que não é percentil (posto descritivo) volta sem tradução.
    """
    if not rotulo_posicao.startswith("P") or not rotulo_posicao[1:].isdigit():
        return ""
    return f"acima de {int(rotulo_posicao[1:])}% dos cooperados da área"


_MES_CURTO = ("jan", "fev", "mar", "abr", "mai", "jun",
              "jul", "ago", "set", "out", "nov", "dez")


def rotulo_intervalo(ini_mes: str, fim_mes: str) -> str:
    """'2025-05','2026-04' -> 'mai/2025 a abr/2026'.

    O rótulo da janela vai para a faixa de critérios, o carimbo de proveniência
    e o cabeçalho. AAAA-MM é forma de máquina: numa tela que um auditor lê em
    voz alta numa reunião, mês por extenso é o mínimo.
    """
    def _um(am: str) -> str:
        ano, mes = am.split("-")
        # ANO INTEIRO, não abreviado: numa base que vai crescer para vários
        # anos, "mai/25" obriga o leitor a completar o século de cabeça, e a
        # tela é lida em voz alta em reunião.
        return f"{_MES_CURTO[int(mes) - 1]}/{ano}"
    return f"{_um(ini_mes)} a {_um(fim_mes)}"
