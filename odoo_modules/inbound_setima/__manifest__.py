{
    "name": "Inbound Sétima · Pipeline",
    "summary": "Menu CRM / Inbound Sétima: pipeline e dashboard de resultados no padrão visual do ABM.",
    "version": "19.0.1.4.0",
    "category": "Sales/CRM",
    "author": "Agência Vivaz",
    "license": "LGPL-3",
    "depends": ["crm", "mail", "web", "abm_setima_dashboard"],
    "data": ["views/inbound_views.xml"],
    "assets": {
        "web.assets_backend": [
            "inbound_setima/static/src/inbound_dashboard.scss",
            "inbound_setima/static/src/inbound_dashboard.xml",
            "inbound_setima/static/src/inbound_dashboard.js",
        ],
    },
    "installable": True,
    "application": False,
}
