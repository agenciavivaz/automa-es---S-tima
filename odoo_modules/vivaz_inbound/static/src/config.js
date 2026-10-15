/** @odoo-module **/
// Configurações do relatório Inbound: um único item de menu que abre as quatro telas (§9.4).

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { MODELO } from "./data";

const OPCOES = [
    { key: "comentario", action: "vivaz_inbound.action_comentario", model: MODELO.comentario, icon: "fa-commenting-o",
      titulo: "Comentários do analista", texto: "Próximos passos da Vivaz exibidos na Leitura do período, por período." },
    { key: "campanha", action: "vivaz_inbound.action_campanha", model: MODELO.campanha, icon: "fa-tags",
      titulo: "Apelidos de campanha", texto: "Nome curto e cor fixa de cada campanha UTM, iguais no gráfico e na tabela." },
    { key: "meta", action: "vivaz_inbound.action_meta", model: MODELO.meta, icon: "fa-bullseye",
      titulo: "Metas por etapa", texto: "Taxa-alvo de conversão por etapa. Com meta, o funil passa a usar verde/vermelho." },
    { key: "ajuste", action: "vivaz_inbound.action_ajuste", model: MODELO.ajuste, icon: "fa-sliders",
      titulo: "Ajustes", texto: "Data de início da receita acumulada (vazio = primeiro contrato inbound)." },
];

export class VivazInboundConfig extends Component {
    static template = "vivaz_inbound.Config";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.opcoes = OPCOES;
        this.state = useState({ contagem: {} });
        onWillStart(async () => {
            const n = await Promise.all(OPCOES.map((o) =>
                this.orm.searchCount(o.model, [], { context: { active_test: false } }).catch(() => null)));
            OPCOES.forEach((o, i) => (this.state.contagem[o.key] = n[i]));
        });
    }

    abrir(o) {
        this.action.doAction(o.action);
    }
    abrirDashboard() {
        this.action.doAction("vivaz_inbound.action_dashboard_v2");
    }
}

registry.category("actions").add("vivaz_inbound_config", VivazInboundConfig);
