#!/usr/bin/env python3
"""
Comitê do ABM Sétima × Apollo: quem saiu da empresa e quem acabou de chegar.

Dois modos (--modo):

trocas   (semanal) — contatos que o Apollo marcou com troca de emprego.
         Quem é do comitê de uma conta do ABM NÃO sai do comitê: ganha a
         marcação "Saiu da empresa" (x_abm_saiu), a data, o tipo de destino e
         para onde foi, e deixa a cadência. As automações já ignoram quem
         saiu (cadência, tarefas e contagens). Na conta: nota no chatter e,
         se era decisor/influenciador-chave, tarefa para o gestor revisar o
         comitê. Se a pessoa foi para outra conta do ABM, ou para a agência
         que atende uma conta, vira oportunidade (nota + tarefa na conta).

exportar (semanal, antes de "trocas") — salva no Apollo, como contato, quem
         está no comitê do Odoo e ainda não existe lá (lista "Comite -
         montadoras - ABM"). Sem isso o Apollo não monitora a troca de
         emprego dessas pessoas. Só cria quem falta: contato que já existe no
         Apollo nunca é reenviado, porque o envio sobrescreveria dados mais
         novos (ex.: o cargo novo de quem trocou de emprego). Criar contato
         não gasta crédito; há um limite diário de criação no Apollo.

lideres  (mensal) — diretores, heads, VPs e C-levels no Brasil, nas contas do
         ABM, com poucos dias no cargo atual. Liderança nova é gatilho de
         abordagem: tarefa para o gestor avaliar incluir no comitê.

As duas buscas do Apollo usadas aqui não gastam crédito. A chave vai no
header X-Api-Key. Só o monitoramento de trocas depende de o contato estar
salvo no Apollo.
"""

import argparse
import datetime as dt
import logging
import os
import re
import sys
import unicodedata

import requests
from dotenv import load_dotenv

from odoo.client import cliente_operacional

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
APOLLO_BASE = "https://api.apollo.io/api/v1"
APOLLO_TIMEOUT = 60
ABM_TEAM_ID = int(os.environ.get("ABM_TEAM_ID", "20"))
ESTAGIOS_FORA = [95, 96]  # Descartada, Cliente – expansão
DIAS_NO_CARGO = int(os.environ.get("APOLLO_DIAS_NO_CARGO", "45"))
SENIORIDADES = ["c_suite", "vp", "director", "head"]
DRY_RUN = os.environ.get("DRY_RUN", "false").strip().lower() in ("1", "true", "sim", "yes")

PAPEIS_CHAVE = ("Decisor", "Influenciador-chave")
LISTA_COMITE = os.environ.get("APOLLO_LISTA_COMITE", "Comite - montadoras - ABM")
EXPORTAR_MAX = int(os.environ.get("APOLLO_EXPORTAR_MAX", "500"))
TIPO_ATIVIDADE = "abm_setima.act_rotina"
MARCA_LIDER = "Apollo pessoa "

# Agências que atendem montadoras (o nome da empresa nova basta para saber
# que é agência; a marca atendida sai do cargo, ex.: "Head of Social | @Ford").
AGENCIAS = {
    "vml", "vmly&r", "wunderman thompson", "ogilvy", "publicis", "leo burnett", "leo",
    "africa", "africa creative", "dm9", "havas", "dentsu", "mccann", "fcb", "grey",
    "innocean", "betc", "betc havas", "almapbbdo", "almap bbdo", "lew'lara", "lew lara",
    "wieden+kennedy", "artplan", "talent", "gut", "david", "monks", "media.monks",
    "accenture song", "jussi", "jüssi", "isobar", "r/ga", "rga", "tbwa", "omd", "starcom",
    "zenith", "mindshare", "wavemaker", "spark foundry", "initiative", "um", "ipg",
}

# Palavras de cargo que interessam à Sétima (comprador de conteúdo 3D/CGI).
CARGOS_RELEVANTES = (
    "marketing", "marca", "brand", "comunica", "communication", "produto", "product",
    "digital", "content", "conteudo", "media", "midia", "experience", "experiencia",
    "cx", "presidente", "president", "ceo", "diretor geral", "managing director",
    "country manager", "lexus", "racing",
)
CARGOS_COMPRAS = ("compras", "procurement", "purchas", "sourcing")
# Áreas que não compram conteúdo 3D/CGI, mesmo com palavra relevante no cargo.
CARGOS_FORA = ("hr ", " hr", "rh", "human", "recursos humanos", "legal", "juridic", "financ",
               "security", "seguranca", "ehs", "software", " it ", "head of it", "powertrain")
COMPRAS_FORA = ("direct material", "material direto", "air", "ocean", "logist", "parts", "pecas", "raw")

STOP = {"do", "da", "de", "dos", "das", "brasil", "brazil", "group", "grupo", "s", "a",
        "sa", "s.a", "ltda", "motors", "motor", "corporation", "company", "inc", "the",
        "america", "south", "latam", "international", "global", "e", "&", "cars", "vans"}


# ---------------------------------------------------------------------------
# Regras (puras, testadas em tests/test_apollo_comite.py)
# ---------------------------------------------------------------------------

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9&@/+. ]", " ", s)).strip()


def tokens(s):
    return {t for t in re.split(r"[\s/.,|()\-@]+", norm(s)) if t and t not in STOP and len(t) > 1}


def norm_linkedin(u):
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^(www\.|[a-z]{2}\.)", "", u)
    return re.sub(r"%[0-9a-f]{2}", "", u).rstrip("/")


def conta_por_nome(nome, contas, excluir=None):
    """Conta do ABM cujo nome casa com `nome` por palavra distintiva. Ambíguo → None."""
    alvo = tokens(nome)
    if not alvo:
        return None
    melhores, nota = [], 0
    for c in contas:
        if excluir and c["id"] == excluir:
            continue
        nomes = [c["name"]] + [x for x in (c.get("x_abm_linkedin_empresa") or "").split(";") if x.strip()]
        pontos = max(len(alvo & tokens(n)) for n in nomes)
        if pontos > nota:
            melhores, nota = [c], pontos
        elif pontos and pontos == nota:
            melhores.append(c)
    return melhores[0] if nota and len(melhores) == 1 else None


def conta_por_dominio(dominio, contas, excluir=None):
    d = (dominio or "").lower().strip()
    if not d:
        return None
    for c in contas:
        if excluir and c["id"] == excluir:
            continue
        doms = [c.get("x_abm_dominio") or ""] + re.split(r"[;,\s]+", c.get("x_abm_dominios_extra") or "")
        if d in {x.strip().lower() for x in doms if x.strip()}:
            return c
    return None


def marca_no_cargo(cargo, contas):
    """Marca atendida citada no cargo (ex.: '... | @Ford' → Ford Brasil)."""
    m = re.search(r"@\s*([A-Za-z0-9][\w&\- ]{1,30})", cargo or "")
    if m:
        c = conta_por_nome(m.group(1), contas)
        if c:
            return c
    return None


def classificar_destino(evento, conta_antiga, contas):
    """(tipo, texto, conta_alvo). conta_alvo é a conta do ABM que ganha a oportunidade."""
    nova = (evento.get("new_organization_name") or "").strip()
    cargo = (evento.get("title") or "").strip()
    if not nova:
        return "desconhecido", "Destino não identificado pelo Apollo", None
    texto = nova + (" · " + cargo if cargo else "")
    alvo = (conta_por_dominio(evento.get("new_organization_domain"), contas, excluir=conta_antiga["id"])
            or conta_por_nome(nova, contas, excluir=conta_antiga["id"]))
    if alvo:
        return "conta_abm", "%s (conta do ABM: %s)" % (texto, alvo["name"]), alvo
    if tokens(nova) & tokens(conta_antiga["name"]):
        return "grupo", "%s (mesmo grupo de %s)" % (texto, conta_antiga["name"]), None
    if norm(nova) in AGENCIAS or "@" in cargo:
        marca = marca_no_cargo(cargo, contas)
        contexto = "assumiu na agência %s" % nova + (", atendendo %s" % marca["name"] if marca else "")
        return "agencia", "%s (%s)" % (texto, contexto), marca
    return "fora", texto, None


def achar_no_comite(contato, comite, conta_antiga_nome):
    """Contato do Apollo → parceiro do comitê (e-mail, LinkedIn ou nome + conta)."""
    emails = {(contato.get("email") or "").lower()} | {
        (e.get("email") or "").lower() for e in contato.get("contact_emails") or []}
    emails.discard("")
    li = norm_linkedin(contato.get("linkedin_url"))
    nome = norm(contato.get("name"))
    conta = tokens(conta_antiga_nome)
    por_nome = None
    for p in comite:
        if p.get("email") and p["email"].lower() in emails:
            return p
        if li and norm_linkedin(p.get("x_linkedin_url")) == li:
            return p
        if nome and norm(p["name"]) == nome and conta & tokens(p["parent_id"][1] if p.get("parent_id") else ""):
            por_nome = p
    return por_nome


def chaves_contato(nome, email, empresa):
    """Chaves de identidade: e-mail e nome + palavra distintiva da empresa."""
    ch = set()
    if email:
        ch.add("e:" + email.strip().lower())
    n = norm(nome)
    for t in tokens(empresa):
        if n:
            ch.add("n:%s|%s" % (n, t))
    return ch


def a_exportar(comite, contatos_apollo):
    """Pessoas do comitê do Odoo que ainda não existem no Apollo."""
    existentes = set()
    for c in contatos_apollo:
        emails = [c.get("email")] + [e.get("email") for e in c.get("contact_emails") or []]
        for e in emails:
            existentes |= chaves_contato(None, e, "")
        existentes |= chaves_contato(c.get("name"), None, c.get("organization_name") or (c.get("account") or {}).get("name"))
    saida = []
    for p in comite:
        if p.get("x_abm_saiu") or not p.get("conta") or not (p.get("name") or "").strip():
            continue
        empresa = (p["conta"].get("x_abm_linkedin_empresa") or "").split(";")[0].strip() or p["conta"]["name"]
        if chaves_contato(p["name"], p.get("email"), empresa) & existentes:
            continue
        if chaves_contato(p["name"], None, p["conta"]["name"]) & existentes:
            continue
        partes = p["name"].strip().split(" ", 1)
        vals = {"first_name": partes[0], "last_name": partes[1] if len(partes) > 1 else "",
                "organization_name": empresa, "label_names": [LISTA_COMITE]}
        if p.get("email") and "@" in p["email"]:
            vals["email"] = p["email"].strip()
        if p.get("function"):
            vals["title"] = p["function"]
        dominio = (p["conta"].get("x_abm_dominio") or "").strip()
        if dominio:
            vals["website_url"] = "https://" + dominio
        saida.append(vals)
    return saida


def cargo_relevante(cargo):
    c = " %s " % norm(cargo)
    if any(k in c for k in CARGOS_FORA):
        return None
    if any(k in c for k in CARGOS_RELEVANTES):
        return "marketing"
    if any(k in c for k in CARGOS_COMPRAS) and not any(k in c for k in COMPRAS_FORA):
        return "compras"
    return None


def ja_no_comite(pessoa, comite_da_conta):
    """Primeiro nome igual e sobrenome compatível com o mascarado do Apollo (ex.: 'Ro***a')."""
    primeiro = norm(pessoa.get("first_name"))
    masc = pessoa.get("last_name_obfuscated") or pessoa.get("last_name") or ""
    ini, fim = (norm(masc.split("*")[0]), norm(masc.split("*")[-1])) if "*" in masc else (norm(masc), "")
    for p in comite_da_conta:
        partes = norm(p["name"]).split(" ")
        if partes and partes[0] == primeiro:
            resto = partes[1:]
            if not ini or any(s.startswith(ini) and s.endswith(fim) for s in resto):
                return p
    return None


# ---------------------------------------------------------------------------
# Apollo
# ---------------------------------------------------------------------------

def _post(session, chave, caminho, corpo):
    r = session.post(APOLLO_BASE + caminho, json=corpo, timeout=APOLLO_TIMEOUT,
                     headers={"X-Api-Key": chave, "Content-Type": "application/json", "Cache-Control": "no-cache"})
    if r.status_code == 401:
        raise SystemExit("Apollo recusou a chave (401). Confira o secret APOLLO_API_KEY.")
    if r.status_code == 403:
        raise SystemExit("Apollo negou acesso (403) a %s: confira se a chave é mestre." % caminho)
    r.raise_for_status()
    return r.json()


def buscar_trocas(chave, *, session=None):
    session = session or requests.Session()
    contatos, pagina = [], 1
    while True:
        d = _post(session, chave, "/contacts/search", {"contact_job_changed": True, "page": pagina, "per_page": 100})
        filtros = {b.get("signal_field_name") for b in d.get("breadcrumbs") or []}
        if "contact_job_changed" not in filtros:
            raise SystemExit("A API do Apollo não aplicou o filtro de troca de emprego; nada foi gravado.")
        lote = d.get("contacts") or []
        contatos.extend(lote)
        if pagina >= ((d.get("pagination") or {}).get("total_pages") or 0) or not lote:
            return contatos
        pagina += 1


def buscar_contatos(chave, *, session=None):
    """Todos os contatos salvos no Apollo (busca grátis, 100 por página)."""
    session = session or requests.Session()
    contatos, pagina = [], 1
    while True:
        d = _post(session, chave, "/contacts/search", {"page": pagina, "per_page": 100})
        lote = d.get("contacts") or []
        contatos.extend(lote)
        if pagina >= ((d.get("pagination") or {}).get("total_pages") or 0) or not lote:
            return contatos
        pagina += 1


def criar_contatos(chave, contatos, *, session=None):
    """Cria em lotes de 100. Para no primeiro erro (ex.: limite diário) e devolve o que criou."""
    session = session or requests.Session()
    criados, sem_pessoa = 0, 0
    for i in range(0, len(contatos), 100):
        try:
            d = _post(session, chave, "/contacts/bulk_create", {"contacts": contatos[i:i + 100]})
        except requests.HTTPError as exc:
            log.warning("Criação interrompida no lote %s (%s): o restante entra na próxima execução.",
                        i // 100 + 1, exc.response.status_code if exc.response is not None else exc)
            break
        novos = (d.get("created_contacts") or d.get("contacts") or []) + (d.get("existing_contacts") or [])
        criados += len(novos)
        sem_pessoa += sum(1 for c in novos if not c.get("person_id"))
    return criados, sem_pessoa


def buscar_lideres(chave, dominios, dias, *, session=None):
    session = session or requests.Session()
    pessoas, pagina = [], 1
    while True:
        d = _post(session, chave, "/mixed_people/api_search", {
            "q_organization_domains_list": dominios,
            "person_locations": ["Brazil"],
            "person_seniorities": SENIORIDADES,
            "person_days_in_current_title_range": {"max": dias},
            "page": pagina, "per_page": 100,
        })
        total = d.get("total_entries") or (d.get("pagination") or {}).get("total_entries") or 0
        # Trava: sem o filtro de tempo no cargo a busca traria milhares de pessoas.
        if total > 1000:
            raise SystemExit("Busca de lideranças voltou %s pessoas: filtro ignorado? Nada foi gravado." % total)
        lote = d.get("people") or []
        pessoas.extend(lote)
        if len(pessoas) >= total or not lote:
            return pessoas
        pagina += 1


# ---------------------------------------------------------------------------
# Odoo
# ---------------------------------------------------------------------------

def carregar(odoo):
    contas = odoo.search_read(
        "crm.lead", [["team_id", "=", ABM_TEAM_ID], ["stage_id", "not in", ESTAGIOS_FORA]],
        ["id", "name", "partner_id", "x_abm_dominio", "x_abm_dominios_extra", "x_abm_linkedin_empresa"])
    por_empresa = {c["partner_id"][0]: c for c in contas if c["partner_id"]}
    comite = odoo.search_read(
        "res.partner", [["parent_id", "in", list(por_empresa)]],
        ["id", "name", "email", "function", "parent_id", "x_linkedin_url", "x_abm_papel",
         "x_abm_prioridade", "x_abm_saiu", "x_abm_na_cadencia"])
    for p in comite:
        p["conta"] = por_empresa.get(p["parent_id"][0])
    gestor = odoo.search_read("ir.config_parameter", [["key", "=", "abm.gestor_user_id"]], ["value"])
    return contas, comite, int(gestor[0]["value"]) if gestor else False


def dia_util(d):
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


class Saida:
    """Acumula as escritas para o modo DRY_RUN poder só listar."""

    def __init__(self, odoo, gestor):
        self.odoo, self.gestor, self.acoes = odoo, gestor, []

    def contato(self, pid, vals, rotulo):
        self.acoes.append(("contato", rotulo, vals))
        if not DRY_RUN:
            self.odoo.write("res.partner", [pid], vals)

    def nota(self, conta, corpo):
        self.acoes.append(("nota", conta["name"], corpo))
        if not DRY_RUN:
            self.odoo.call("crm.lead", "message_post", {
                "ids": [conta["id"]], "body": corpo, "message_type": "comment", "subtype_xmlid": "mail.mt_note"})

    def tarefa(self, conta, resumo, nota=""):
        self.acoes.append(("tarefa", conta["name"], resumo))
        if not DRY_RUN and self.gestor:
            self.odoo.call("crm.lead", "activity_schedule", {
                "ids": [conta["id"]], "act_type_xmlid": TIPO_ATIVIDADE,
                "date_deadline": dia_util(dt.date.today() + dt.timedelta(days=1)).isoformat(),
                "summary": resumo, "note": nota, "user_id": self.gestor})


def processar_trocas(contatos, contas, comite, saida):
    novos = 0
    for ct in contatos:
        ev = ct.get("contact_job_change_event") or {}
        if not ev or ev.get("is_dismissed"):
            continue
        antiga = ev.get("old_account_name") or ev.get("old_organization_name") or ct.get("organization_name") or ""
        p = achar_no_comite(ct, comite, antiga)
        if not p or not p.get("conta"):
            continue
        if p.get("x_abm_saiu"):
            continue
        conta = p["conta"]
        nomes_conta = tokens(conta["name"]) | tokens(conta.get("x_abm_linkedin_empresa"))
        # A troca precisa ter saído da conta onde a pessoa está no comitê. Se o
        # Odoo já tem a pessoa na conta nova (comitê atualizado à mão), não é saída.
        if antiga and not tokens(antiga) & nomes_conta:
            continue
        tipo, texto, alvo = classificar_destino(ev, conta, contas)
        quando = (ev.get("created_at") or dt.date.today().isoformat())[:10]
        saida.contato(p["id"], {"x_abm_saiu": True, "x_abm_saiu_em": quando, "x_abm_destino_tipo": tipo,
                                "x_abm_destino": texto[:250], "x_abm_na_cadencia": False}, p["name"])
        papel = p.get("x_abm_papel") or "sem papel"
        saida.nota(conta, "🚪 <b>%s</b> (%s, %s) saiu da empresa (detectado pelo Apollo em %s). Para onde foi: %s. "
                          "Continua no comitê com a marcação <i>Saiu da empresa</i> e não entra mais na cadência." % (
                              p["name"], papel, p.get("function") or "-", quando, texto))
        if papel in PAPEIS_CHAVE or p.get("x_abm_prioridade") == 1:
            saida.tarefa(conta, "[Comitê] %s saiu – %s – revisar comitê" % (papel, p["name"]),
                         "<p>%s saiu. Destino: %s.</p><p>Ver quem assume a função e incluir no comitê.</p>" % (p["name"], texto))
        if alvo and tipo in ("conta_abm", "agencia"):
            if tipo == "conta_abm":
                resumo = "[Oportunidade] %s (ex-%s) chegou à conta – avaliar incluir no comitê" % (p["name"], conta["name"])
            else:
                resumo = "[Oportunidade] %s atende a conta pela agência – avaliar como porta de entrada" % p["name"]
            if alvo["id"] != conta["id"]:
                saida.nota(alvo, "🔁 <b>%s</b>, que era do comitê de %s, agora: %s." % (p["name"], conta["name"], texto))
            saida.tarefa(alvo, resumo, "<p>%s</p>" % texto)
        p["x_abm_saiu"] = True  # o mesmo contato pode vir duas vezes na busca
        novos += 1
    return novos


def processar_lideres(pessoas, contas, comite, ja_avisados, saida, dias):
    novos = 0
    for ps in pessoas:
        org = (ps.get("organization") or {}).get("name") or ""
        conta = conta_por_nome(org, contas)
        if not conta:
            log.info("Liderança sem conta única no ABM: %s (%s)", ps.get("first_name"), org)
            continue
        if ps.get("id") in ja_avisados:
            continue
        relev = cargo_relevante(ps.get("title"))
        if not relev:
            continue
        nome = "%s %s" % (ps.get("first_name") or "", ps.get("last_name_obfuscated") or ps.get("last_name") or "")
        if ja_no_comite(ps, [p for p in comite if p.get("conta") and p["conta"]["id"] == conta["id"]]):
            continue
        marca = MARCA_LIDER + (ps.get("id") or "")
        saida.nota(conta, "🆕 Liderança nova (até %s dias no cargo): <b>%s</b> – %s. Não está no comitê. %s" % (
            dias, nome.strip(), ps.get("title") or "-", marca))
        saida.tarefa(conta, "[Comitê] Nova liderança%s: %s – %s" % (
            " (compras)" if relev == "compras" else "", nome.strip(), ps.get("title") or "-"),
            "<p>Assumiu o cargo há até %s dias: momento de rever fornecedores. Buscar o nome completo no "
            "LinkedIn/Apollo, enriquecer e avaliar incluir no comitê.</p><p>%s</p>" % (dias, marca))
        novos += 1
    return novos


def lideres_ja_avisados(odoo, conta_ids):
    msgs = odoo.search_read("mail.message", [["model", "=", "crm.lead"], ["res_id", "in", conta_ids],
                                             ["body", "ilike", MARCA_LIDER]], ["body"])
    return {m.group(1) for x in msgs for m in [re.search(re.escape(MARCA_LIDER) + r"([a-f0-9]{24})", x["body"] or "")] if m}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["trocas", "lideres", "exportar"], required=True)
    args = ap.parse_args()
    chave = os.environ.get("APOLLO_API_KEY", "").strip()
    if not chave:
        raise SystemExit("APOLLO_API_KEY não definida.")
    url = os.environ.get("ODOO_URL", "").strip().rstrip("/")
    os.environ["ODOO_URL"] = re.sub(r"/odoo$", "", url)

    odoo = cliente_operacional(somente_leitura=DRY_RUN)
    contas, comite, gestor = carregar(odoo)
    saida = Saida(odoo, gestor)
    log.info("%s contas do ABM, %s pessoas no comitê%s", len(contas), len(comite), " — DRY_RUN" if DRY_RUN else "")

    if args.modo == "exportar":
        existentes = buscar_contatos(chave)
        faltam = a_exportar(comite, existentes)
        log.info("Apollo: %s contato(s) salvos; %s pessoa(s) do comitê ainda fora do Apollo", len(existentes), len(faltam))
        for v in faltam[:15]:
            log.info("exportar → %s %s (%s)", v["first_name"], v["last_name"], v["organization_name"])
        lote = faltam[:EXPORTAR_MAX]
        if DRY_RUN:
            log.info("DRY_RUN: nada criado no Apollo (%s seriam criados nesta execução).", len(lote))
            return
        criados, sem_pessoa = criar_contatos(chave, lote)
        log.info("Criados no Apollo: %s (lista %s). Sem vínculo com o cadastro de pessoas do Apollo: %s "
                 "(estes não terão troca de emprego monitorada).", criados, LISTA_COMITE, sem_pessoa)
        return
    if args.modo == "trocas":
        contatos = buscar_trocas(chave)
        log.info("Apollo: %s contato(s) com troca de emprego", len(contatos))
        n = processar_trocas(contatos, contas, comite, saida)
    else:
        dominios = sorted({d.strip().lower() for c in contas
                           for d in [c.get("x_abm_dominio") or ""] + re.split(r"[;,\s]+", c.get("x_abm_dominios_extra") or "")
                           if d.strip()})
        pessoas = buscar_lideres(chave, dominios, DIAS_NO_CARGO)
        log.info("Apollo: %s liderança(s) com até %s dias no cargo", len(pessoas), DIAS_NO_CARGO)
        n = processar_lideres(pessoas, contas, comite, lideres_ja_avisados(odoo, [c["id"] for c in contas]),
                              saida, DIAS_NO_CARGO)

    for tipo, alvo, info in saida.acoes:
        log.info("%s → %s: %s", tipo, alvo, re.sub(r"<[^>]+>", "", str(info))[:220])
    log.info("%s%s registro(s) novo(s), %s escrita(s).", "DRY_RUN: " if DRY_RUN else "", n, len(saida.acoes))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log.exception("Falha na sincronização do comitê Apollo → Odoo")
        sys.exit(1)
