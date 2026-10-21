{
    "name": "ABM BrandSpot · Dashboard",
    "summary": "Painel estratégico do ABM BrandSpot: sinais, atividades, contas e estúdio interno.",
    "version": "19.0.1.0.0",
    "category": "Sales/CRM",
    "author": "Agência Vivaz",
    "license": "LGPL-3",
    "depends": ["crm", "mail", "web"],
    "data": ["views/dashboard_action.xml"],
    "assets": {
        "web.assets_backend": [
            "abm_brandspot_dashboard/static/src/abm_dashboard.scss",
            "abm_brandspot_dashboard/static/src/abm_dashboard.xml",
            "abm_brandspot_dashboard/static/src/abm_dashboard.js",
        ],
    },
    "installable": True,
    "application": False,
}
