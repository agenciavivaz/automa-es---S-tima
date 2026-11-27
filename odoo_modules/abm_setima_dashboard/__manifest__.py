{
    "name": "ABM Sétima · Dashboard",
    "summary": "Painel estratégico do ABM Sétima: cobertura, engajamento LinkedIn, sinais de intenção e contas.",
    "version": "19.0.3.2.0",
    "category": "Sales/CRM",
    "author": "Agência Vivaz",
    "license": "LGPL-3",
    "depends": ["crm", "mail", "web"],
    "data": ["views/midia_fields.xml", "views/dashboard_action.xml"],
    "assets": {
        "web.assets_backend": [
            "abm_setima_dashboard/static/src/abm_dashboard.scss",
            "abm_setima_dashboard/static/src/abm_dashboard.xml",
            "abm_setima_dashboard/static/src/abm_dashboard.js",
        ],
    },
    "installable": True,
    "application": False,
}
