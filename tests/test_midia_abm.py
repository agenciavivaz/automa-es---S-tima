import datetime as dt

import atualizar_midia_abm as m


def test_linha_dia_chave_frente_e_numeros():
    v = m.linha_dia({
        "data": dt.datetime(2026, 11, 13), "campanha_urn": "urn:li:sponsoredCampaign:907279086",
        "campanha_nome": "Lista  + Comitê", "impressoes": 1402.0, "cliques": 5.0, "custo_brl": 108.789,
        "video_views": 348.0, "video_completos": "6", "coletado_em": dt.datetime(2026, 11, 26, 17, 29),
    })
    assert v["x_name"] == "2026-11-13|907279086"
    assert v["x_frente"] == "comite"
    assert v["x_campanha"] == "Lista + Comitê"
    assert v["x_impressoes"] == 1402 and v["x_custo"] == 108.79 and v["x_video_completos"] == 6
    assert v["x_cliques_lp"] == 0


def test_linha_dia_frente_educacao_outra_e_linha_vazia():
    assert m.linha_dia({"data": "2026-11-01", "campanha_urn": "urn:li:sponsoredCampaign:917108416"})["x_frente"] == "educacao"
    assert m.linha_dia({"data": "2026-11-01", "campanha_urn": "urn:li:sponsoredCampaign:1"})["x_frente"] == "outra"
    assert m.linha_dia({"data": None, "campanha_urn": "urn:li:sponsoredCampaign:1"}) is None


def test_linha_empresa_casa_pelo_nome_no_linkedin():
    contas = [{"id": 7, "name": "CNH Industrial", "x_abm_linkedin_empresa": "CNH; Case IH"}]
    idx = m.indice_contas(contas)
    v = m.linha_empresa({"periodo_inicio": dt.datetime(2026, 11, 17), "periodo_fim": dt.datetime(2026, 11, 23),
                         "empresa_urn": "urn:li:organization:4622", "empresa_nome": "Case IH",
                         "impressoes": 288.0, "cliques": 0}, idx)
    assert v["x_lead_id"] == 7 and v["x_name"] == "2026-11-17|urn:li:organization:4622"
    fora = m.linha_empresa({"periodo_inicio": "2026-11-17", "empresa_urn": "urn:li:organization:1",
                            "empresa_nome": "Volkswagen do Brasil"}, idx)
    assert fora["x_lead_id"] is False


def test_linhas_segmento_traduz_e_limita_cargos():
    cargos = {
        "periodo_inicio": "2026-09-21", "periodo_fim": "2026-11-26",
        "titulos": {"315": "Product Specialist", "999": "Unknown Title"},
        "frentes": {"comite": {
            "senioridade": [{"impressions": 10, "clicks": 1, "costInLocalCurrency": "5.5", "pivotValues": ["urn:li:seniority:6"]}],
            "funcao": [{"impressions": 8, "clicks": 0, "pivotValues": ["urn:li:function:15"]}],
            "cargo": [{"impressions": 5, "clicks": 0, "pivotValues": ["urn:li:title:315"]},
                      {"impressions": 4, "clicks": 0, "pivotValues": ["urn:li:title:123"]},
                      {"impressions": 3, "clicks": 0, "pivotValues": ["urn:li:title:999"]}],
        }},
    }
    linhas = {(l["x_dimensao"], l["x_valor_id"]): l for l in m.linhas_segmento(cargos)}
    assert linhas[("senioridade", "6")]["x_valor"] == "Diretor"
    assert linhas[("senioridade", "6")]["x_custo"] == 5.5
    assert linhas[("funcao", "15")]["x_valor"] == "Marketing"
    assert linhas[("cargo", "315")]["x_valor"] == "Especialista de produto"
    assert ("cargo", "123") not in linhas  # sem nome resolvido fica de fora
    assert linhas[("cargo", "999")]["x_valor"] == "Unknown Title"  # sem tradução mantém o inglês
