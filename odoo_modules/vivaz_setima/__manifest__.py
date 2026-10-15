{
    "name": "Sétima · Resultado comercial",
    "summary": "Menu CRM / Sétima: pipeline da equipe Pipeline Sétima e dashboard de resultado "
               "(receita, ticket, clientes, projetos, tipo de projeto, vendedores e pipeline).",
    "version": "19.0.1.0.0",
    "category": "Sales/CRM",
    "author": "Agência Vivaz",
    "license": "LGPL-3",
    "depends": ["crm", "web"],
    "data": ["views/views.xml"],
    "assets": {
        "web.assets_backend": [
            "vivaz_setima/static/src/dashboard.scss",
            "vivaz_setima/static/src/dashboard.xml",
            "vivaz_setima/static/src/calc.js",
            "vivaz_setima/static/src/data.js",
            "vivaz_setima/static/src/dashboard.js",
        ],
    },
    "installable": True,
    "application": False,
}
