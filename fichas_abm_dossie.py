#!/usr/bin/env python3
"""
Ficha ABM nas Notas internas (crm.lead.description) das contas do ABM Sétima que
têm dossiê anexado mas ainda não têm a ficha.

A ficha segue o layout das contas já preparadas (ex.: Marcopolo S.A.): cabeçalho
escuro, chips de trilha/tier/segmento, tabela de gatilhos, modelo para o espelho
e objeção, caixa "Conferir antes do E1" e sugestão de 3 pessoas para a cadência.
O conteúdo foi resumido do dossiê de guerrilha de cada conta (04/11/2026); as
pessoas da cadência são as do comitê no Odoo.

Só grava em conta com description vazia (não sobrescreve ficha nem anotação).
Dry-run por padrão:
    python fichas_abm_dossie.py            # mostra o que faria
    python fichas_abm_dossie.py --aplicar  # grava
"""

import html
import os
import re
import sys

import requests

TRILHA = {"sem_config": "Sem configurador", "config_fraco": "Configurador fraco",
          "config_bom": "Configurador bom", "a_definir": "A definir"}
PAPEL_DESTAQUE = {"Decisor"}

ROTULO = "background-color:#f9fafb; padding:5px 8px; width:26%; color:#6b7280; vertical-align:top"
CHIP_TRILHA = "background-color:#fde8e2; color:#9a3412; padding:2px 8px; border-radius:10px; font-size:12px"
CHIP = "background-color:#f3f4f6; color:#374151; padding:2px 8px; border-radius:10px; font-size:12px"

FICHAS = {
    "Scania Group": {
        "segmento": "caminhões e ônibus",
        "gatilho": ("Lançamento da gama Super 11 litros (390 e 430 cv, câmbio Opticruise G25) e cabines renovadas "
                    "das linhas P, G, R e S na 25ª Fenatran, no São Paulo Expo · 09 a 13/11/2026",
                    "dm.com.br, autopapo.com.br e canaldiesel.com.br (out/2026)"),
        "reserva": ("Silvio Renan Souza assume a direção de Vendas de Soluções em 01/10/2026: liderança comercial "
                    "nova, e o configurador como ferramenta de venda consultiva",
                    "AutoData 01/10/2026"),
        "site": ("A Scania tem o Scania Configurator 3D na Bélgica e na Austrália (2024), mas não encontramos "
                 "versão brasileira. A página do Brasil não abriu na pesquisa: validar no navegador."),
        "espelho": ("Super 11 L 4x2 (cavalo, cabine R)",
                    "é o lançamento da Fenatran e o modelo de maior volume da nova gama, alternando 390/430 cv, "
                    "cabine e cores, com vista do interior renovado. Entregar na semana seguinte à feira (16 a 20/11)."),
        "objecao": ("A matriz define o configurador",
                    "o configurador europeu e o australiano não cobrem a gama brasileira (Super 11 L, linha a gás e "
                    "biometano, versões locais). O espelho mostra isso, e o twin pode alimentar a ferramenta global."),
        "conferir": [
            "Validar no navegador se existe configurador da Scania para o Brasil antes do E1.",
            "Fenatran vai até 13/11: mandar o E1 depois da feira, com o espelho do Super 11 L.",
            "Patricia Acioli (sponsor) e Marcus Minholi (compras) só entram depois da reunião com marketing de produto.",
        ],
        "cadencia": ["Rogerio Segala", "Marcio Furlan", "Jacksom Santos"],
    },
    "AGCO Corporation": {
        "segmento": "agro e construção",
        "gatilho": ("Ciclo de lançamentos da AGCO no Brasil: MF 9S (a maior série da Massey Ferguson no país, até "
                    "425 cv) na Agrishow 2026 e estreia da MF no segmento de 35 a 85 cv em 2026 (parceria SDF). "
                    "Próxima vitrine: Agrishow 2027, de 26 a 30/04, com conteúdo pronto no 1º trimestre",
                    "jumasa.com.br (Agrishow 2026); bloomberglinea.com.br; agrishow.com.br"),
        "reserva": ("Expodireto 2026: Fendt 800 Vario de 5ª geração (até 343 cv), MF 4700 e MF 7718 em novas "
                    "versões · mar/2026",
                    "fendt.com (09/04/2026); paginarural.com.br"),
        "site": ("Não encontramos configurador online de trator das marcas AGCO no Brasil. Os sites de Massey "
                 "Ferguson, Valtra e Fendt não abriram na pesquisa: validar os três."),
        "espelho": ("Massey Ferguson MF 9S",
                    "carro-chefe da Agrishow 2026 e maior trator da marca no Brasil: potências, rodado e cabine, "
                    "com cena de campo. Em máquina grande o realismo impressiona."),
        "objecao": ("O agricultor compra na concessionária, não no site",
                    "por isso mesmo: o configurador e o 3D vão para o tablet do vendedor, o estande e o anúncio "
                    "local de cada revenda das três marcas."),
        "conferir": [
            "Validar os configuradores de Massey Ferguson, Valtra e Fendt no navegador antes do E1.",
            "Thiago Carmona de Paula (Dealer Performance Manager Fendt/Valtra) visitou a página da Sétima e "
            "ainda está fora do comitê: avaliar a inclusão. Não citar a visita.",
        ],
        "cadencia": ["Breno Cavalcanti", "Jose Viscardi", "Fernanda Teixeira"],
    },
    "John Deere": {
        "segmento": "agro e construção",
        "gatilho": ("Casa John Deere 2026: série 8R (até 634 cv), linha 5M, trator 3041E, colheitadeira S4 para "
                    "pequenos e médios produtores e plataforma CR. Próxima vitrine: Agrishow 2027, de 26 a 30/04",
                    "deere.com.br (sala de imprensa, abr/2026); revistacultivar.com.br"),
        "reserva": ("Vaga de Technical Information Specialist (Technical Writer) em Indaiatuba: investimento em "
                    "conteúdo técnico e pós-venda · 30/10/2026",
                    "Apollo · careers.deere.com"),
        "site": ("Não encontramos configurador online de máquinas da John Deere para o Brasil. O site deere.com.br "
                 "não abriu na pesquisa: validar se há “monte o seu”."),
        "espelho": ("Colheitadeira S4 (300 e 400)",
                    "feita para o Brasil, lançamento de 2026 e voltada a um público novo (pequeno e médio produtor) "
                    "que precisa ver a máquina antes de ir à revenda. Cena de lavoura em terreno acidentado, com "
                    "plataforma e cabine."),
        "objecao": ("Temos time global de design e 3D",
                    "a Sétima produz em escala para a América Latina, com versões, cenas e linguagem locais, a "
                    "partir dos dados de engenharia que vocês já têm."),
        "conferir": [
            "Tier B no dossiê: não há lançamento específico anunciado para os próximos meses.",
            "Rodrigo Bonato (VP Latam) entra só depois do interesse de marketing. Silvana Arend (Instituto John "
            "Deere) fica fora desta fase.",
        ],
        "cadencia": ["Valerio Junior", "Adilson Butzke", "Ewerton Machado"],
    },
    "Stellantis South America": {
        "segmento": "carros",
        "gatilho": ("Fiat Argo X, primeiro carro inédito de Betim no plano FaSTLAne 2030: apresentação comercial em "
                    "meados de novembro e chegada às lojas em 01/12/2026, no ano dos 50 anos da Fiat no Brasil",
                    "mixvale.com.br (22/10/2026); otempo.com.br (30/09/2026)"),
        "reserva": ("Adriana Girão assume como Head de Marketing e Comunicação de Marca em 04/05/2026, e a liderança "
                    "de Peugeot e Citroën é unificada em out/2026",
                    "AutoData 04/05/2026 e edição 437 (out/2026)"),
        "site": ("A Fiat já tem configurador online (a imprensa registrou modelos saindo dele). Validar formato e "
                 "qualidade (2D ou 3D, interior, celular). Não achamos informação sobre os de Peugeot e Citroën."),
        "espelho": ("Fiat Argo X",
                    "versão topo, cores de lançamento e assinatura de luz em X, pronto até 01/12. É o lançamento do "
                    "ano e o concorrente direto do VW Tera, o nosso case."),
        "objecao": ("Já temos configurador",
                    "o espelho mostra a diferença na prática: o mesmo carro com realismo NGI, interior e velocidade "
                    "no celular. A demo é a comparação lado a lado."),
        "conferir": [
            "Trilha provisória: o dossiê indica configurador fraco (a Fiat tem configurador). Validar no site "
            "e ajustar o campo Trilha antes do E1.",
            "Jeep, Ram e Leapmotor têm contas próprias no ABM e ficam fora desta abordagem.",
            "Adriana Girão (sponsor) só depois do interesse da Fiat. Adriana Orlandelli e João Veloso não "
            "abordar a frio.",
        ],
        "cadencia": ["Hugo Domingues", "Paula Salerno", "Lucas Fonseca"],
    },
    "Grupo Yamaha Brasil": {
        "segmento": "motos",
        "gatilho": ("Rogério Castillo preencheu o formulário da Sétima em 01/11/2026 (anúncio do Instagram para "
                    "cargos de marketing). A conta está em Conversa: responder ao interesse dele e propor o espelho",
                    "Odoo · lead de inbound #21631 e sinal na conta (uso interno: não citar o anúncio)"),
        "reserva": ("Lançamento da ZR Hybrid Connected (R$ 13.990, 3 cores), a moto mais barata da marca e scooter "
                    "híbrida · abr a mai/2026",
                    "global.yamaha-motor.com e vrum.com.br (abr/2026)"),
        "site": ("Não encontramos “monte sua moto” nem 360° no site brasileiro. O yamaha-motor.com.br não abriu na "
                 "pesquisa: validar antes da conversa. A Honda, líder, já testa configurador 3D no exterior."),
        "espelho": ("ZR Hybrid Connected",
                    "lançamento de 2026, de volume e com tecnologia nova, nas 3 cores (Moon Silver, Magma Red e "
                    "Midnight Black), com 360° e cena urbana. Alternativa premium: MT-07 Connected. Levar na "
                    "primeira conversa com o Rogério."),
        "objecao": ("Já temos AlmapBBDO e FutureBrand",
                    "a Sétima entra como parceira técnica das duas: o twin vira matéria-prima para campanha e "
                    "branding, e o ativo fica com a Yamaha."),
        "conferir": [
            "Conta em Conversa: a tarefa de contato em até 1h útil está atrasada desde 01/11. Retomar com o "
            "Rogério antes de qualquer cadência.",
            "Confirmar cargo e área do Rogério Castillo: no Odoo ele está como Training Instructor.",
        ],
        "cadencia": ["Rogério Castillo", "Giovana Vale", "Erin Usui"],
    },
    "Zeekr International": {
        "segmento": "carros",
        "gatilho": ("Pré-venda do Zeekr 7X Premium 2027 a partir de R$ 378 mil (100 kWh, 421 cv, 800 V) · jun/2026",
                    "AutoData e conexaoto.com.br (23/06/2026)"),
        "reserva": ("Novas lojas em Belo Horizonte, Campinas e Brasília com grupos parceiros: cada inauguração pede "
                    "material local · 2026",
                    "conexaoautomotivabr.com (fev/2026); paraibabusiness.com.br"),
        "site": ("O configurador global da Zeekr é bom (trilha no Odoo). Validar a versão brasileira. O ângulo não "
                 "é configurador, e sim volume de conteúdo local com um time de 2 pessoas em marketing."),
        "espelho": ("Cena de campanha do 7X Premium",
                    "em cenário brasileiro (Avenida Paulista à noite ou estrada da Serra), com 3 peças derivadas: "
                    "OOH, social e loja. Não usar configurador espelho."),
        "objecao": ("O conteúdo vem da matriz",
                    "a matriz não produz cenas brasileiras nem peças de inauguração de loja; o twin local completa o "
                    "que vem da China."),
        "conferir": [
            "Tier B no dossiê: avaliar se vale a cadência agora ou despriorizar.",
            "Comitê de só 3 pessoas: mapear o analista ou coordenador de marketing do time de 2.",
            "Marcos Cardellini está sem e-mail no Odoo: abordar pelo LinkedIn.",
        ],
        "cadencia": ["Diego Borghi", "Marcus Pires", "Marcos Cardellini"],
    },
    "Grupo CAOA": {
        "segmento": "carros",
        "gatilho": ("As versões Prime e PHEV do CAOA Changan CS55 chegam às lojas com fila de 60 dias e sem carro de "
                    "test-drive do PHEV · 30/10/2026",
                    "piranot.com.br (30/10/2026)"),
        "reserva": ("Lançamento do CS55 (Prime R$ 144.990, Infinity R$ 154.990, Ultra Hybrid PHEV R$ 189.990), "
                    "produzido em Anápolis · 15/09/2026",
                    "gurudoscarros.com.br (15/09/2026); autoentusiastas.com.br"),
        "site": ("Não encontramos configurador 3D da CAOA Changan. Os sites caoa.com.br e caoachangan.com.br não "
                 "abriram na pesquisa: validar."),
        "espelho": ("CAOA Changan CS55",
                    "nas 3 versões (Prime, Infinity e Ultra Hybrid PHEV), com interior e detalhe do sistema híbrido. "
                    "É o lançamento mais recente, com fila e sem test-drive do PHEV: o 3D faz o papel do test-drive "
                    "visual."),
        "objecao": ("A Changan da China já tem as imagens",
                    "as versões flex de Anápolis são do Brasil; o twin local mostra exatamente o carro vendido aqui, "
                    "com cores e versões daqui."),
        "conferir": [
            "Jan Telecki (Marketing & Communications Director, decisor prioridade 1 no dossiê) está cadastrado na "
            "conta CAOA Chery, não aqui. Ele já preencheu o formulário da Sétima em mai/2026: decidir em qual "
            "conta ele entra na cadência.",
            "A CAOA Chery tem conta própria no ABM. A agência é a Baila desde mar/2026: posicionar como parceira técnica.",
        ],
        "cadencia": ["Andreza Paz", "Eduardo Berteloni", "Cassiana Hamada"],
    },
}


def e(texto):
    return html.escape(texto, quote=False)


def montar(conta, f, contatos):
    linhas_tabela = []

    def linha(rotulo, sub, corpo):
        sub_html = '<br><span style="font-size:11px">%s</span>' % sub if sub else ""
        linhas_tabela.append(
            '<tr><td style="%s">%s%s</td><td style="padding:5px 8px">%s</td></tr>' % (ROTULO, rotulo, sub_html, corpo))

    fonte = lambda t: '<br><span style="color:#6b7280; font-size:12px">%s</span>' % e(t)
    linha("🎯 Gatilho principal", "1ª linha do E1", e(f["gatilho"][0]) + fonte(f["gatilho"][1]))
    linha("🔁 Gatilho de reserva", "abertura do E3", e(f["reserva"][0]) + fonte(f["reserva"][1]))
    linha("🔎 Observação do site", "", e(f["site"]))
    linha("🧩 Modelo para o espelho", "", "<b>%s</b> · %s" % (e(f["espelho"][0]), e(f["espelho"][1])))
    linha("🛡️ Objeção provável", "", "<b>%s</b><br>→ %s" % (e(f["objecao"][0]), e(f["objecao"][1])))

    pessoas = []
    for nome in f["cadencia"]:
        p = next(c for c in contatos if c["name"] == nome)
        papel = p["x_abm_papel"] or "—"
        cor = ("background-color:#fde8e2; color:#9a3412" if papel in PAPEL_DESTAQUE
               else "background-color:#f3f4f6; color:#374151")
        cargo = re.sub(r"\s+", " ", p["function"] or "").strip()
        pessoas.append(
            '<tr><td style="padding:4px 8px"><b>%s</b> — %s</td>'
            '<td style="padding:4px 8px"><span style="%s; padding:1px 6px; border-radius:8px; font-size:11px">%s</span></td>'
            '<td style="padding:4px 8px; color:#6b7280; font-size:12px">e-mail %s</td></tr>'
            % (e(p["name"]), e(cargo), cor, e(papel), e(p["x_email_status"] or "não informado")))

    validado = conta["x_abm_comite_validado_em"]
    validado = "%s/%s" % (validado[8:10], validado[5:7]) if validado else "—"
    return (
        '<div style="background-color:#1f2937; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; '
        'font-size:14px">📋 FICHA ABM · %s <span style="font-weight:normal; color:#d1d5db">· 04/11/2026</span></div>'
        '<p style="margin:6px 0 10px"><span style="%s">Trilha: %s</span> <span style="%s">Tier %s</span> '
        '<span style="%s">%s</span></p>'
        '<table style="width:100%%; border-collapse:collapse; border:1px solid #e5e7eb; margin-bottom:10px">%s</table>'
        '<div style="background-color:#fff7d6; color:#713f12; padding:8px 12px; border-radius:6px; margin-bottom:10px">'
        '⚠️ <b>Conferir antes do E1</b><ul style="margin:4px 0 0; padding-left:18px">%s</ul></div>'
        '<p style="font-weight:bold; margin:0 0 4px">👥 Sugestão para a cadência <span style="font-weight:normal; '
        'color:#6b7280; font-size:12px">(comitê revisado em %s · confirmar e marcar “Na cadência” no contato)</span></p>'
        '<table style="width:100%%; border-collapse:collapse; border:1px solid #e5e7eb; margin-bottom:10px">%s</table>'
        '<p style="margin:0; color:#6b7280; font-size:12px">Fontes, raio-x, objeções e ângulo completo: dossiê anexo '
        '(campo ABM · Dossiê).</p>'
        % (e(conta["name"]), CHIP_TRILHA, TRILHA.get(conta["x_abm_trilha"], "A definir"), CHIP,
           conta["x_abm_tier"] or "—", CHIP, e(f["segmento"]), "".join(linhas_tabela),
           "".join("<li>%s</li>" % e(i) for i in f["conferir"]), validado, "".join(pessoas))
    )


def cliente():
    url = re.sub(r"/odoo$", "", os.environ["ODOO_URL"].strip().rstrip("/"))
    headers = {"Authorization": "Bearer " + os.environ["ODOO_API_KEY"].strip(),
               "X-Odoo-Database": os.environ["ODOO_DB"].strip(), "Content-Type": "application/json"}

    def call(model, method, **kw):
        r = requests.post(f"{url}/json/2/{model}/{method}", headers=headers, json=kw, timeout=60)
        if r.status_code != 200:
            raise SystemExit(f"[HTTP {r.status_code}] {model}.{method}: {r.text[:500]}")
        return r.json()

    return call


def main(aplicar):
    call = cliente()
    contas = call("crm.lead", "search_read",
                  domain=[["team_id", "=", 20], ["name", "in", list(FICHAS)]],
                  fields=["name", "description", "partner_id", "x_abm_trilha", "x_abm_tier",
                          "x_abm_comite_validado_em", "x_abm_dossie_url"])
    print("== %s" % ("APLICANDO" if aplicar else "DRY-RUN (use --aplicar para gravar)"))
    for conta in contas:
        texto = re.sub(r"<[^>]+>", "", conta["description"] or "").strip()
        if texto:
            print("[pula] %s: Notas internas já preenchidas" % conta["name"])
            continue
        contatos = call("res.partner", "search_read", domain=[["parent_id", "=", conta["partner_id"][0]]],
                        fields=["name", "function", "x_abm_papel", "x_email_status"])
        ficha = montar(conta, FICHAS[conta["name"]], contatos)
        print("[ficha] %s (%s caracteres)" % (conta["name"], len(ficha)))
        if aplicar:
            call("crm.lead", "write", ids=[conta["id"]], vals={"description": ficha})
    faltam = set(FICHAS) - {c["name"] for c in contas}
    if faltam:
        print("Contas não encontradas: " + ", ".join(sorted(faltam)))


if __name__ == "__main__":
    main("--aplicar" in sys.argv[1:])
