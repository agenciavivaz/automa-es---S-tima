#!/usr/bin/env python3
"""
Teste das automações ABM (seção 6 da spec), numa conta fictícia.

1. Cria "ABM · Teste" (equipe ABM, domínio teste-abm.invalid) com 4 contatos
   fictícios (decisor, influenciador, usuário, fora do ICP).
2. Durante o teste, as atividades vão para o gestor (Diego), não para a SDR.
3. Ativa as regras A1–A16 SÓ para os registros de teste (filtro temporário).
4. Percorre o roteiro e confere cada resultado. As regras por data (A3, A9,
   A13, A14) são executadas manualmente sobre a conta de teste.
5. Confere que nenhum e-mail foi gerado (mail.mail / notificações por e-mail).
6. SEMPRE (try/finally): desativa as regras, restaura os filtros e o SDR,
   apaga os registros de teste.

Uso: APLICAR=true python abm/testar_automacoes_abm_setima.py
"""

import ast
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from criar_visoes_abm_setima import APLICAR, MODULO, odoo, ref  # noqa: E402

DOMINIO = "teste-abm.invalid"
# Equipe do lead de "formulário" simulado: tem de ser uma que o sincronismo com
# o DataCrazy NÃO lê (ele só lê 16 e 17), senão viraria WhatsApp de verdade.
EQUIPE_FORA_DATACRAZY = 4  # Pipeline Sétima
SEM_SEGUIR = {"mail_create_nosubscribe": True, "mail_auto_subscribe_no_notify": True}
resultados = []


def checar(passo, esperado, obtido, ok):
    resultados.append((passo, esperado, obtido, "PASSOU" if ok else "FALHOU"))
    print(f"[{'OK' if ok else 'XX'}] {passo}: {obtido}")


def ler(model, ids, campos):
    return odoo(model, "read", ids=ids if isinstance(ids, list) else [ids], fields=campos)


def atividades(lead_id):
    return odoo("mail.activity", "search_read",
                domain=[["res_model", "=", "crm.lead"], ["res_id", "=", lead_id]],
                fields=["summary", "activity_type_id", "date_deadline", "x_abm_partner_id", "user_id"],
                order="date_deadline, id")


def rodar_acao(chave, model, ids):
    auto = ref(f"{MODULO}.auto_{chave}")
    srv = ler("base.automation", auto, ["action_server_ids"])[0]["action_server_ids"]
    odoo("ir.actions.server", "run", ids=srv,
         context={"active_model": model, "active_ids": ids, "active_id": ids[0]})


def contar_emails(desde, lead_ids, partner_ids):
    mails = odoo("mail.mail", "search_count", domain=[["create_date", ">=", desde]])
    notif = odoo("mail.notification", "search_count", domain=[
        ["notification_type", "=", "email"], ["mail_message_id.create_date", ">=", desde],
        "|", "&", ["mail_message_id.model", "=", "crm.lead"], ["mail_message_id.res_id", "in", lead_ids],
        "&", ["mail_message_id.model", "=", "res.partner"], ["mail_message_id.res_id", "in", partner_ids]])
    return mails, notif


def main():
    if not APLICAR:
        print("Este teste cria e apaga registros de teste. Rode com APLICAR=true.")
        return
    team_id = int(odoo("ir.config_parameter", "get_param", key="abm.team_id"))
    sdr_original = odoo("ir.config_parameter", "get_param", key="abm.sdr_user_id")
    gestor = int(odoo("ir.config_parameter", "get_param", key="abm.gestor_user_id"))
    st = {k: ref(f"{MODULO}.stage_{k}") for k in (
        "alvo", "aquecendo", "engajada", "em_cadencia", "conversa", "reuniao_agendada", "nutricao")}
    regras = {k: ref(f"{MODULO}.auto_{k}") for k in (
        "a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a11", "a12", "a13", "a14", "a15", "a16")}
    originais = {k: ler("base.automation", v, ["filter_domain", "active"])[0] for k, v in regras.items()}
    if any(o["active"] for o in originais.values()):
        raise SystemExit("Há regras ABM ativas: o teste só roda com todas desativadas.")

    desde = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    base_mails, _ = contar_emails(desde, [0], [0])
    criados = {"leads": [], "partners": []}

    try:
        odoo("ir.config_parameter", "set_param", key="abm.sdr_user_id", value=str(gestor))

        # ------------------------------------------------------------ dados
        empresa = odoo("res.partner", "create", context=SEM_SEGUIR, vals_list=[{
            "name": "ABM · Teste (empresa)", "is_company": True}])[0]
        criados["partners"].append(empresa)
        base_c = {"parent_id": empresa, "type": "contact", "x_abm_li_conexao": "nao_enviado",
                  "x_abm_na_cadencia": False, "x_abm_optout": False}
        c = odoo("res.partner", "create", context=SEM_SEGUIR, vals_list=[
            {**base_c, "name": "Teste Decisor", "function": "Diretor de Marketing", "x_abm_papel": "Decisor",
             "x_abm_prioridade": 1, "email": f"decisor@{DOMINIO}", "x_email_status": "Verificado",
             "phone": "+55 11 90000-0001", "x_linkedin_url": "https://www.linkedin.com/in/teste-decisor"},
            {**base_c, "name": "Teste Influenciador", "function": "Gerente de Produto", "x_abm_papel": "Influenciador",
             "x_abm_prioridade": 2, "email": f"influ@{DOMINIO}", "x_email_status": "Verificado"},
            {**base_c, "name": "Teste Usuário", "function": "Analista", "x_abm_papel": "Usuário/Ponto de entrada",
             "x_abm_prioridade": 3, "email": f"usuario@{DOMINIO}", "x_email_status": "Verificado"},
            {**base_c, "name": "Teste Fora", "function": "Compliance", "x_abm_papel": "Fora",
             "x_abm_prioridade": 9, "email": f"fora@{DOMINIO}"},
        ])
        criados["partners"] += c
        decisor, influ, usuario, _fora = c
        lead = odoo("crm.lead", "create", context=SEM_SEGUIR, vals_list=[{
            "name": "ABM · Teste", "type": "opportunity", "team_id": team_id, "partner_id": empresa,
            "stage_id": st["aquecendo"], "user_id": gestor, "x_abm_dominio": DOMINIO,
            "x_abm_trilha": "a_definir", "x_abm_cadencia_status": "nao_iniciada", "x_abm_onda": 0,
            "x_abm_link_email": "https://www.setima.cc/PT?utm_content=teste"}])[0]
        criados["leads"].append(lead)
        seguidores = odoo("mail.followers", "search_read", domain=[["res_model", "=", "crm.lead"], ["res_id", "=", lead]],
                          fields=["partner_id"])
        if seguidores:
            odoo("crm.lead", "message_unsubscribe", ids=[lead], partner_ids=[s["partner_id"][0] for s in seguidores])
        print(f"Conta de teste #{lead}, empresa #{empresa}, contatos {c}")

        # ---------------------------------------- ativa só para o teste
        restricoes = {k: ("id", "=", lead) for k in regras}
        restricoes.update({"a11": ("parent_id", "=", empresa), "a12": ("parent_id", "=", empresa),
                           "a13": ("x_lead_id", "=", lead), "a15": ("email_from", "ilike", DOMINIO)})
        for k, auto in regras.items():
            dom = ast.literal_eval(originais[k]["filter_domain"] or "[]")
            odoo("base.automation", "write", ids=[auto],
                 vals={"filter_domain": repr([restricoes[k]] + dom), "active": True})

        F = ["stage_id", "x_abm_score", "x_abm_faixa", "x_abm_preparacao", "x_abm_cadencia_status",
             "x_abm_onda", "x_abm_cadencia_inicio"]

        # a) Alvo → volta para a fila (A1)
        odoo("crm.lead", "write", ids=[lead], vals={"stage_id": st["alvo"]})
        r = ler("crm.lead", lead, F)[0]
        checar("a · Mover para Alvo (A1)", "preparação = Na fila", r["x_abm_preparacao"], r["x_abm_preparacao"] == "fila")

        # b) sinal de 30 pontos → Engajada + Iniciar cadência (A2)
        sinal_dm = odoo("x_abm_sinal", "create", vals_list=[{
            "x_name": "Teste DM", "x_lead_id": lead, "x_partner_id": influ, "x_tipo": "li_dm_resposta"}])[0]
        r = ler("crm.lead", lead, F)[0]
        acts = atividades(lead)
        ok = r["x_abm_score"] == 30 and r["x_abm_faixa"] == "engajada" and r["stage_id"][0] == st["engajada"] \
            and any(a["activity_type_id"][1] == "ABM · Iniciar cadência" for a in acts)
        checar("b · Sinal 'Respondeu DM' (A2)", "score 30, Engajada, tarefa Iniciar cadência",
               f"score {r['x_abm_score']}, {r['x_abm_faixa']}, {r['stage_id'][1]}, {len(acts)} tarefa(s)", ok)

        # c) Em cadência → onda 1 (A5)
        odoo("crm.lead", "write", ids=[lead], vals={"stage_id": st["em_cadencia"]})
        r = ler("crm.lead", lead, F)[0]
        acts = [a for a in atividades(lead) if (a["summary"] or "").startswith("[Cadência]")]
        pessoas = {a["x_abm_partner_id"][0] for a in acts if a["x_abm_partner_id"]}
        na_cad = [p["id"] for p in ler("res.partner", c, ["x_abm_na_cadencia"]) if p["x_abm_na_cadencia"]]
        datas = sorted({a["date_deadline"] for a in acts})
        fim_de_semana = [d for d in datas if datetime.date.fromisoformat(d).weekday() >= 5]
        tem_ligacao = any("Ligação" in (a["summary"] or "") or "WhatsApp" in (a["summary"] or "") for a in acts)
        ok = r["x_abm_cadencia_status"] == "ativa" and r["x_abm_onda"] == 1 and set(na_cad) == {decisor, influ} \
            and pessoas == {decisor, influ} and all(a["x_abm_partner_id"] for a in acts) \
            and not fim_de_semana and not tem_ligacao and len(acts) == 16
        checar("c · Mover para Em cadência (A5)",
               "onda 1; decisor+influenciador; 8 tarefas cada; só e-mail/LinkedIn; dias úteis",
               f"{len(acts)} tarefas p/ {len(pessoas)} pessoas, {datas[0]}→{datas[-1]}, "
               f"fim de semana: {len(fim_de_semana)}, ligação/WhatsApp: {tem_ligacao}", ok)

        # c2) onda 2 (A14): com resposta recente não faz nada; sem resposta, entra o usuário
        rodar_acao("a14", "crm.lead", [lead])
        r = ler("crm.lead", lead, F)[0]
        checar("c2 · Onda 2 com resposta recente (A14)", "não muda nada", f"onda {r['x_abm_onda']}", r["x_abm_onda"] == 1)
        ontem = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        odoo("x_abm_sinal", "write", ids=[sinal_dm], vals={"x_data": ontem})
        rodar_acao("a14", "crm.lead", [lead])
        r = ler("crm.lead", lead, F)[0]
        u_acts = [a for a in atividades(lead) if a["x_abm_partner_id"] and a["x_abm_partner_id"][0] == usuario]
        checar("c3 · Onda 2 sem resposta (A14)", "onda 2; usuário entra com 8 tarefas",
               f"onda {r['x_abm_onda']}, {len(u_acts)} tarefas do usuário", r["x_abm_onda"] == 2 and len(u_acts) == 8)

        # d) conexão aceita pelo decisor (A11) → sinal, pós-conexão, asset para o gestor
        odoo("res.partner", "write", ids=[decisor], vals={"x_abm_li_conexao": "aceito"})
        acts = atividades(lead)
        pos = [a for a in acts if "pós-conexão" in (a["summary"] or "")]
        asset = [a for a in acts if a["activity_type_id"][1] == "ABM · Preparar asset"]
        sinais = odoo("x_abm_sinal", "search_read", domain=[["x_lead_id", "=", lead], ["x_tipo", "=", "li_conexao_aceita"]], fields=["id"])
        ok = len(sinais) == 1 and len(pos) == 1 and len(asset) == 1 and asset[0]["user_id"][0] == gestor
        checar("d · Decisor aceitou conexão (A11)", "sinal +15; mensagem pós-conexão; asset p/ gestor",
               f"sinais {len(sinais)}, pós-conexão {len(pos)}, asset {len(asset)} ({asset[0]['user_id'][1] if asset else '-'})", ok)

        # d2) asset pronto (A16) → enviar ao decisor conectado
        odoo("crm.lead", "write", ids=[lead], vals={"x_abm_asset_url": "https://exemplo.invalid/asset"})
        env_asset = [a for a in atividades(lead) if "Enviar asset" in (a["summary"] or "")]
        checar("d2 · Asset pronto (A16)", "tarefa 'Enviar asset – Teste Decisor'",
               [a["summary"] for a in env_asset], len(env_asset) == 1 and "Teste Decisor" in env_asset[0]["summary"])

        # e) opt-out do influenciador (A12)
        antes = len([a for a in atividades(lead) if a["x_abm_partner_id"] and a["x_abm_partner_id"][0] == influ])
        odoo("res.partner", "write", ids=[influ], vals={"x_abm_optout": True})
        depois = len([a for a in atividades(lead) if a["x_abm_partner_id"] and a["x_abm_partner_id"][0] == influ])
        cad = ler("res.partner", influ, ["x_abm_na_cadencia"])[0]["x_abm_na_cadencia"]
        checar("e · Opt-out do influenciador (A12)", "tarefas dele canceladas; sai da cadência",
               f"{antes} → {depois} tarefas; na cadência: {cad}", antes > 0 and depois == 0 and not cad)

        # f) e-mail recebido do decisor (A10) → sinal +30 → quente → ligação/WhatsApp (A4)
        odoo("crm.lead", "message_post", ids=[lead], context=SEM_SEGUIR, body="Olá, tenho interesse. (teste)",
             message_type="email", author_id=decisor, email_from=f"decisor@{DOMINIO}",
             subject="Re: teste", subtype_xmlid="mail.mt_comment")
        r = ler("crm.lead", lead, F)[0]
        acts = atividades(lead)
        classificar = [a for a in acts if a["activity_type_id"][1] == "ABM · Classificar resposta"]
        quente = [a for a in acts if (a["summary"] or "").startswith("[Quente]")]
        checar("f · E-mail recebido (A10)", "sinal +30; tarefa Classificar resposta",
               f"score {r['x_abm_score']}, classificar {len(classificar)}", len(classificar) == 1 and r["x_abm_score"] >= 75)
        checar("f2 · Conta quente (A4)", "ligação hoje + WhatsApp p/ quem tem telefone",
               [a["summary"] for a in quente], r["x_abm_faixa"] == "quente" and len(quente) == 2)

        # g) Conversa → cancela cadência (A6) + agendar reunião (A7)
        odoo("crm.lead", "write", ids=[lead], vals={"stage_id": st["conversa"]})
        acts = atividades(lead)
        r = ler("crm.lead", lead, F)[0]
        cad = [a for a in acts if (a["summary"] or "").startswith("[Cadência]")]
        agendar = [a for a in acts if a["activity_type_id"][1] == "ABM · Agendar reunião"]
        checar("g · Mover para Conversa (A6+A7)", "tarefas [Cadência] canceladas; Agendar reunião",
               f"[Cadência] restantes {len(cad)}, agendar {len(agendar)}, status {r['x_abm_cadencia_status']}",
               not cad and len(agendar) == 1 and r["x_abm_cadencia_status"] == "pausada")

        # g2) Reunião agendada (A8)
        odoo("crm.lead", "write", ids=[lead], vals={"stage_id": st["reuniao_agendada"]})
        prep = [a for a in atividades(lead) if a["activity_type_id"][1] == "ABM · Preparar reunião"]
        checar("g2 · Mover para Reunião agendada (A8)", "tarefa Preparar reunião", len(prep), len(prep) == 1)

        # h) formulário de conta-alvo fora da equipe ABM (A15)
        inbound = odoo("crm.lead", "create", context=SEM_SEGUIR, vals_list=[{
            "name": "Teste formulário", "type": "lead", "team_id": EQUIPE_FORA_DATACRAZY,
            "email_from": f"x@{DOMINIO}", "contact_name": "Pessoa Formulário"}])[0]
        criados["leads"].append(inbound)
        form = odoo("x_abm_sinal", "search_read", domain=[["x_lead_id", "=", lead], ["x_tipo", "=", "formulario"]], fields=["id"])
        lig = [a for a in atividades(lead) if "Formulário" in (a["summary"] or "")]
        checar("h · Lead de formulário com domínio da conta (A15)", "sinal +50 e ligação urgente na conta ABM",
               f"sinais {len(form)}, ligação {len(lig)}", len(form) == 1 and len(lig) == 1)

        # i) regras por data, executadas à mão
        sinais = [s["id"] for s in odoo("x_abm_sinal", "search_read", domain=[["x_lead_id", "=", lead]], fields=["id"])]
        rodar_acao("a13", "x_abm_sinal", sinais)
        r = ler("crm.lead", lead, F)[0]
        checar("i · Sinais expiram (A13)", "score 0, fria", f"score {r['x_abm_score']}, {r['x_abm_faixa']}",
               r["x_abm_score"] == 0 and r["x_abm_faixa"] == "fria")
        odoo("crm.lead", "write", ids=[lead], vals={"stage_id": st["em_cadencia"]})
        rodar_acao("a9", "crm.lead", [lead])
        r = ler("crm.lead", lead, F)[0]
        checar("i2 · 35 dias sem sinal (A9 → A6)", "Nutrição; cadência concluída",
               f"{r['stage_id'][1]}, {r['x_abm_cadencia_status']}",
               r["stage_id"][0] == st["nutricao"] and r["x_abm_cadencia_status"] == "concluida")
        odoo("crm.lead", "write", ids=[lead], vals={"stage_id": st["aquecendo"]})
        rodar_acao("a3", "crm.lead", [lead])
        r = ler("crm.lead", lead, F)[0]
        checar("i3 · 21 dias aquecendo (A3)", "Engajada", r["stage_id"][1], r["stage_id"][0] == st["engajada"])

        # ------------------------------------------------ nenhum e-mail
        mails, notif = contar_emails(desde, criados["leads"], criados["partners"])
        checar("j · Nenhum e-mail gerado", "0 mail.mail e 0 notificação por e-mail",
               f"mail.mail novos: {mails - base_mails}, notificações por e-mail: {notif}",
               mails - base_mails == 0 and notif == 0)

    finally:
        for k, auto in regras.items():
            odoo("base.automation", "write", ids=[auto],
                 vals={"active": False, "filter_domain": originais[k]["filter_domain"]})
        odoo("ir.config_parameter", "set_param", key="abm.sdr_user_id", value=sdr_original)
        ativos = odoo("base.automation", "search_count", domain=[["id", "in", list(regras.values())], ["active", "=", True]])
        acts = odoo("mail.activity", "search", domain=[
            "|", "&", ["res_model", "=", "crm.lead"], ["res_id", "in", criados["leads"] or [0]],
            "&", ["res_model", "=", "res.partner"], ["res_id", "in", criados["partners"] or [0]]])
        if acts:
            odoo("mail.activity", "unlink", ids=acts)
        if criados["leads"]:
            odoo("crm.lead", "unlink", ids=criados["leads"])
        if criados["partners"]:
            odoo("res.partner", "unlink", ids=criados["partners"][::-1])
        print(f"\nLimpeza: regras ativas agora = {ativos}; SDR restaurado = {sdr_original}; "
              f"apagados {len(criados['leads'])} lead(s) e {len(criados['partners'])} contato(s).")

    print("\n| Passo | Esperado | Obtido | Resultado |\n|---|---|---|---|")
    for p, e, o, s in resultados:
        print(f"| {p} | {e} | {o} | {s} |")


if __name__ == "__main__":
    main()
