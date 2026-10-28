"""Regras da rotina de comitê (trocas de emprego e lideranças novas). Sem rede."""

import pytest

import sincronizar_apollo_comite_abm as sync

CONTAS = [
    {"id": 1, "name": "Ford Brasil", "x_abm_dominio": "ford.com", "x_abm_dominios_extra": "ford.com.br", "x_abm_linkedin_empresa": "Ford Brasil"},
    {"id": 2, "name": "Nissan do Brasil", "x_abm_dominio": "nissan.com.br", "x_abm_dominios_extra": "", "x_abm_linkedin_empresa": "Nissan do Brasil"},
    {"id": 3, "name": "Jetour Brasil", "x_abm_dominio": "jetourbr.com", "x_abm_dominios_extra": "", "x_abm_linkedin_empresa": "Jetour"},
    {"id": 4, "name": "Stellantis South America", "x_abm_dominio": "stellantis.com", "x_abm_dominios_extra": "", "x_abm_linkedin_empresa": "Stellantis South America"},
    {"id": 5, "name": "Volvo Cars", "x_abm_dominio": "volvocars.com", "x_abm_dominios_extra": "", "x_abm_linkedin_empresa": "Volvo Cars"},
    {"id": 6, "name": "Volvo Trucks", "x_abm_dominio": "volvotrucks.com.br", "x_abm_dominios_extra": "", "x_abm_linkedin_empresa": "Volvo Trucks"},
    {"id": 7, "name": "Renault do Brasil", "x_abm_dominio": "renault.com", "x_abm_dominios_extra": "", "x_abm_linkedin_empresa": "Renault do Brasil"},
]
FORD, NISSAN, STELLANTIS = CONTAS[0], CONTAS[1], CONTAS[3]


@pytest.mark.parametrize("evento,conta,tipo,alvo", [
    ({"new_organization_name": "IAB Brasil", "title": "Counselor"}, STELLANTIS, "fora", None),
    ({"new_organization_name": "Ford Motor Company", "title": "Governance Analyst"}, FORD, "grupo", None),
    ({"new_organization_name": "Nissan Motor Corporation", "title": "Purchasing Region Manager"}, NISSAN, "grupo", None),
    ({"new_organization_name": "VML", "title": "Head of Social Media, Content & Influence | @Ford"}, FORD, "agencia", "Ford Brasil"),
    ({"new_organization_name": "Jetour Brasil", "title": "Executive Manager"}, STELLANTIS, "conta_abm", "Jetour Brasil"),
    ({"new_organization_name": "Qualquer", "new_organization_domain": "jetourbr.com"}, FORD, "conta_abm", "Jetour Brasil"),
    ({"new_organization_name": None}, FORD, "desconhecido", None),
])
def test_classificar_destino(evento, conta, tipo, alvo):
    t, texto, c = sync.classificar_destino(evento, conta, CONTAS)
    assert t == tipo
    assert (c["name"] if c else None) == alvo
    if tipo == "agencia":
        assert "assumiu na agência VML, atendendo Ford Brasil" in texto


def test_nome_ambiguo_nao_escolhe_conta():
    assert sync.conta_por_nome("Volvo Group", CONTAS) is None
    assert sync.conta_por_nome("Renault Group", CONTAS)["name"] == "Renault do Brasil"
    assert sync.conta_por_nome("Stellantis", CONTAS)["name"] == "Stellantis South America"


COMITE = [
    {"id": 10, "name": "Debora Dauanny", "email": "debora.dauanny@stellantis.com", "x_linkedin_url": "",
     "parent_id": [99, "Stellantis South America"]},
    {"id": 11, "name": "Lucas Rondelli", "email": False, "x_linkedin_url": "https://br.linkedin.com/in/lucasrondelli/",
     "parent_id": [98, "Ford Brasil"]},
    {"id": 12, "name": "Luciano Rocha", "email": False, "x_linkedin_url": "", "parent_id": [97, "Volvo Construction Equipment"]},
]


def test_achar_no_comite_por_email_linkedin_e_nome():
    assert sync.achar_no_comite({"email": "Debora.Dauanny@stellantis.com"}, COMITE, "x")["id"] == 10
    assert sync.achar_no_comite({"linkedin_url": "http://www.linkedin.com/in/lucasrondelli"}, COMITE, "x")["id"] == 11
    assert sync.achar_no_comite({"name": "Luciano Rocha"}, COMITE, "Volvo Construction Equipment")["id"] == 12
    assert sync.achar_no_comite({"name": "Luciano Rocha"}, COMITE, "Ford Brasil") is None


def test_ja_no_comite_com_sobrenome_mascarado():
    assert sync.ja_no_comite({"first_name": "Luciano", "last_name_obfuscated": "Ro***a"}, COMITE)["id"] == 12
    assert sync.ja_no_comite({"first_name": "Luciano", "last_name_obfuscated": "Go***s"}, COMITE) is None


@pytest.mark.parametrize("cargo,esperado", [
    ("Head of Marketing | Latam Importers", "marketing"),
    ("Presidente e Diretor Geral", "marketing"),
    ("Head of Procurement", "compras"),
    ("Legal Director", None),
    ("HR Director South America - Quality, Design and HR HRBP", None),
    ("Head of Purchasing Direct Material", None),
    ("Head of Lexus & Gazoo Racing Brazil", "marketing"),
])
def test_cargo_relevante(cargo, esperado):
    assert sync.cargo_relevante(cargo) == esperado


class _Saida:
    def __init__(self):
        self.acoes = []

    def contato(self, pid, vals, rotulo):
        self.acoes.append(("contato", pid, vals))

    def nota(self, conta, corpo):
        self.acoes.append(("nota", conta["id"], corpo))

    def tarefa(self, conta, resumo, nota=""):
        self.acoes.append(("tarefa", conta["id"], resumo))


def test_troca_marca_saida_sem_tirar_do_comite_e_avisa_decisor():
    comite = [dict(COMITE[1], conta=FORD, x_abm_papel="Decisor", x_abm_prioridade=1, x_abm_saiu=False)]
    contato = {"linkedin_url": "linkedin.com/in/lucasrondelli", "contact_job_change_event": {
        "old_account_name": "Ford Brasil", "new_organization_name": "VML",
        "title": "Head of Social | @Ford", "created_at": "2026-09-19T04:18:44Z"}}
    s = _Saida()
    assert sync.processar_trocas([contato], CONTAS, comite, s) == 1
    vals = s.acoes[0][2]
    assert vals["x_abm_saiu"] and vals["x_abm_destino_tipo"] == "agencia" and vals["x_abm_na_cadencia"] is False
    assert vals["x_abm_saiu_em"] == "2026-09-19"
    assert any(a[0] == "tarefa" and "revisar comitê" in a[2] for a in s.acoes)
    assert any(a[0] == "tarefa" and "[Oportunidade]" in a[2] for a in s.acoes)


def test_troca_ja_marcada_nao_repete():
    comite = [dict(COMITE[0], conta=STELLANTIS, x_abm_saiu=True)]
    s = _Saida()
    contato = {"email": "debora.dauanny@stellantis.com", "contact_job_change_event": {"new_organization_name": "IAB"}}
    assert sync.processar_trocas([contato], CONTAS, comite, s) == 0 and not s.acoes


def test_troca_ignorada_quando_odoo_ja_tem_a_pessoa_na_conta_nova():
    jetour = CONTAS[2]
    comite = [{"id": 20, "name": "Reinaldo Siffert", "email": "r@jetourbr.com", "x_linkedin_url": "",
               "parent_id": [96, "Jetour Brasil"], "conta": jetour, "x_abm_saiu": False}]
    contato = {"email": "r@jetourbr.com", "contact_job_change_event": {
        "old_account_name": "Stellantis South America", "new_organization_name": "Jetour Brasil"}}
    s = _Saida()
    assert sync.processar_trocas([contato], CONTAS, comite, s) == 0 and not s.acoes


def test_mesmo_contato_duas_vezes_grava_uma():
    comite = [dict(COMITE[0], conta=STELLANTIS, x_abm_saiu=False, x_abm_papel="Influenciador")]
    contato = {"email": "debora.dauanny@stellantis.com", "contact_job_change_event": {
        "old_account_name": "Stellantis South America", "new_organization_name": "IAB Brasil"}}
    s = _Saida()
    assert sync.processar_trocas([contato, contato], CONTAS, comite, s) == 1
