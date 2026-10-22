import json, re, unicodedata
from collections import Counter, defaultdict
d = json.load(open('comites.json')); P = d['P']; pid = {int(k): v for k, v in d['pid'].items()}
norm = lambda s: unicodedata.normalize('NFKD', (s or '').lower()).encode('ascii', 'ignore').decode()
R = lambda *ws: re.compile(r'(' + '|'.join(ws) + r')')
MKT = R(r'marketing', r'\bmkt', r'comunica', r'communication', r'\bbrand', r'\bmarca', r'publicidade', r'advertis', r'propaganda',
        r'conteudo', r'content', r'e-?commerce', r'\bcrm\b', r'\bcx\b', r'customer experience', r'experiencia do cliente', r'\bux\b',
        r'\bmidia', r'\bmedia\b', r'eventos', r'relacoes publicas', r'imprensa', r'\bpr\b', r'digital marketing', r'marketing digital')
LIDER = R(r'\bcmo\b', r'chief marketing', r'\bvp\b', r'\bvice\b', r'diretor', r'diretora', r'director', r'\bhead\b', r'chefe', r'superintend')
GERENTE = R(r'gerente', r'manager', r'supervis', r'\blead\b', r'leader', r'lider')
JUNIOR = R(r'coorden', r'coordinat', r'especialista', r'specialist', r'analista', r'analyst', r'assistente', r'assistant', r'estagi', r'intern', r'trainee', r'consultor')
EXEC = R(r'\bceo\b', r'presidente', r'president', r'chief executive', r'diretor geral', r'diretora geral', r'general manager', r'general director',
         r'managing director', r'country manager', r'\bowner\b', r'fundador', r'founder', r'\bcoo\b', r'chief operating', r'diretor executivo', r'dir\. presidente', r'\bcfo\b', r'chief financial')
COMPRAS = R(r'compras', r'purchas', r'procure', r'suprimento', r'sourcing', r'buyer', r'comprador')
FIN = R(r'financ', r'controller', r'controladoria', r'\bcfo\b', r'contab', r'tesour', r'fiscal')
COM = R(r'sales', r'vendas', r'comercial', r'commercial', r'business development', r'negocios', r'dealer', r'concession', r'frota', r'fleet', r'channel', r'key account')
PROD = R(r'\bproduct\b', r'\bprodutos?\b', r'planejamento de produto')
DIGI = R(r'digital', r'e-?commerce', r'\bweb\b', r'\bsite\b', r'\bux\b', r'\bcx\b')


def nova(p):
    f = norm(p['function']); area = p['x_abm_area'] or ''
    eh_mkt = bool(MKT.search(f)) or area == 'Marketing'
    if re.search(r'estagi|\bintern\b|trainee|aprendiz|comunicacao interna|internal comm', f):
        return ('Usuário/Ponto de entrada', 3, 'estágio ou comunicação interna')
    if p['x_abm_prioridade'] == 9 and p['x_abm_papel'] == 'Fora':
        return ('Fora', 9, 'mantido')
    if eh_mkt and not EXEC.search(f) or (eh_mkt and LIDER.search(f)):
        if LIDER.search(f) or p['x_abm_senioridade'] in ('C suite', 'Vp', 'Director', 'Head'):
            return ('Decisor', 1, 'líder de marketing')
        if JUNIOR.search(f) or p['x_abm_senioridade'] in ('Entry', 'Intern'):
            return ('Influenciador', 2, 'marketing operacional')
        if GERENTE.search(f) or p['x_abm_senioridade'] in ('Manager', 'Senior'):
            return ('Influenciador-chave', 2, 'gerente de marketing')
        return ('Influenciador', 2, 'marketing operacional')
    if COMPRAS.search(f) or area == 'Compras/Procurement':
        return ('Aprovador', 3, 'compras')
    if FIN.search(f) or area == 'Financeiro/Controladoria':
        return ('Aprovador', 3, 'financeiro')
    if EXEC.search(f) or p['x_abm_senioridade'] in ('C suite', 'Owner') or (area == 'Outros' and p['x_abm_senioridade'] in ('Vp', 'Director')):
        return ('Aprovador', 3, 'alta gestão')
    if COM.search(f) or area == 'Comercial/Vendas':
        return ('Aprovador', 3, 'comercial')
    if DIGI.search(f) and (LIDER.search(f) or GERENTE.search(f)):
        return ('Influenciador-chave', 2, 'digital/site')
    if PROD.search(f) or area == 'Produto':
        if LIDER.search(f) or p['x_abm_senioridade'] in ('Director', 'Head', 'Vp'):
            return ('Influenciador-chave', 2, 'liderança de produto')
        return ('Influenciador', 3, 'produto')
    if area == 'Engenharia/Design' and re.search(r'design', f):
        return ('Influenciador', 3, 'design')
    return (p['x_abm_papel'] or 'Usuário/Ponto de entrada', 3 if p['x_abm_prioridade'] != 9 else 9, 'sem mudança')


res = []
for p in P:
    papel, pr, motivo = nova(p)
    res.append(dict(p, novo_papel=papel, nova_prio=pr, motivo=motivo, conta=pid[p['parent_id'][0]]))
# Fallback: conta sem líder de marketing -> o gerente de marketing mais sênior vira Decisor.
SENR = {'C suite': 0, 'Vp': 1, 'Owner': 1, 'Head': 2, 'Director': 2, 'Manager': 3, 'Senior': 4, 'Entry': 5}
por_conta = defaultdict(list)
for r in res:
    por_conta[r['conta']].append(r)
for conta, rs in por_conta.items():
    if any(r['novo_papel'] == 'Decisor' for r in rs):
        continue
    cand = [r for r in rs if r['motivo'] == 'gerente de marketing']
    if cand:
        NICHO = r'supervis|coorden|lexus|gazoo|marine|financeir|financial|aftersales|pos.?venda|trade|evento|endomarketing|esg|treinamento|growth'
        cand.sort(key=lambda r: (SENR.get(r['x_abm_senioridade'], 6), 1 if re.search(NICHO, norm(r['function'])) else 0,
                                 0 if re.search(r'senior|\bsr\b', norm(r['function'])) else 1,
                                 0 if r['x_email_status'] in ('Verificado', 'Válido') else 1, r['name']))
        cand[0].update(novo_papel='Decisor', nova_prio=1, motivo='gerente de marketing mais sênior (sem diretor)')
json.dump(res, open('reclass.json', 'w'), ensure_ascii=False)
