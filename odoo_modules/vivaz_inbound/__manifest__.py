{
    "name": "Inbound Sétima · Relatório de resultados v2",
    "summary": "Dashboard do Inbound Sétima (PRD v1.1): métricas corrigidas, leitura do período, "
               "acumulado fixo e configurações do relatório. Substitui o dashboard da v1 (arquivado).",
    "version": "19.0.2.1.0",
    "category": "Sales/CRM",
    "author": "Agência Vivaz",
    "license": "LGPL-3",
    # inbound_setima: menu "Inbound Sétima" e campos x_origem_inbound / x_meta_* (v1 intacta)
    "depends": ["crm", "mail", "calendar", "web", "inbound_setima"],
    "data": [
        "data/modelos.xml",
        "security/acessos.xml",
        "data/dados.xml",
        "views/views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vivaz_inbound/static/src/dashboard.scss",
            "vivaz_inbound/static/src/dashboard.xml",
            "vivaz_inbound/static/src/calc.js",
            "vivaz_inbound/static/src/data.js",
            "vivaz_inbound/static/src/dashboard.js",
            "vivaz_inbound/static/src/config.js",
        ],
    },
    "installable": True,
    "application": False,
}
