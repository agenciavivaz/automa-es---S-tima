import { describe, expect, it } from 'vitest';
import { calcularScore, classificarEmail, exigeToqueComercial } from '../scoring';
import type { ScoringInput } from '../scoring';

const base: ScoringInput = {
  skusAno: 0,
  economiaCalculada: 0,
  setor: 'outro',
  email: 'alguem@gmail.com',
  cargo: '',
  informouReceita: false,
};

describe('classificarEmail', () => {
  it('reconhece provedores gratuitos', () => {
    expect(classificarEmail('a@gmail.com')).toBe('gratuito');
    expect(classificarEmail('a@HOTMAIL.com')).toBe('gratuito');
    expect(classificarEmail('a@yahoo.com.br')).toBe('gratuito');
    expect(classificarEmail('a@outlook.com')).toBe('gratuito');
  });

  it('trata o resto como corporativo', () => {
    expect(classificarEmail('joao@vw.com.br')).toBe('corporativo');
    expect(classificarEmail('maria@embraer.com')).toBe('corporativo');
  });

  it('e-mail sem domínio não vira corporativo', () => {
    expect(classificarEmail('semarroba')).toBe('gratuito');
  });
});

describe('calcularScore', () => {
  it('lead sem nenhum sinal fica em Tier C', () => {
    const r = calcularScore(base);
    expect(r.score).toBe(0);
    expect(r.tier).toBe('C');
    expect(exigeToqueComercial(r.tier)).toBe(false);
  });

  it('pontua faixas de SKU sem cumular as duas faixas', () => {
    expect(calcularScore({ ...base, skusAno: 50 }).score).toBe(30);
    expect(calcularScore({ ...base, skusAno: 49 }).score).toBe(20);
    expect(calcularScore({ ...base, skusAno: 19 }).score).toBe(0);
  });

  it('pontua faixas de economia sem cumular as duas faixas', () => {
    expect(calcularScore({ ...base, economiaCalculada: 500_000 }).score).toBe(25);
    expect(calcularScore({ ...base, economiaCalculada: 499_999 }).score).toBe(15);
    expect(calcularScore({ ...base, economiaCalculada: 149_999 }).score).toBe(0);
  });

  it('pontua setor prioritário', () => {
    expect(calcularScore({ ...base, setor: 'automotivo' }).score).toBe(20);
    expect(calcularScore({ ...base, setor: 'maquinas_agro' }).score).toBe(20);
    expect(calcularScore({ ...base, setor: 'moda' }).score).toBe(0);
  });

  it('pontua e-mail corporativo, cargo decisor e passo 4', () => {
    expect(calcularScore({ ...base, email: 'j@vw.com.br' }).score).toBe(15);
    expect(calcularScore({ ...base, cargo: 'Gerente de Marketing' }).score).toBe(10);
    expect(calcularScore({ ...base, cargo: 'Head of Brand' }).score).toBe(10);
    expect(calcularScore({ ...base, cargo: 'Estagiário' }).score).toBe(0);
    expect(calcularScore({ ...base, informouReceita: true }).score).toBe(10);
  });

  it('Tier A: gerente de montadora com volume e economia altos', () => {
    const r = calcularScore({
      skusAno: 120,
      economiaCalculada: 1_200_000,
      setor: 'automotivo',
      email: 'gerente@vw.com.br',
      cargo: 'Gerente de Marketing',
      informouReceita: true,
    });
    expect(r.score).toBe(110);
    expect(r.tier).toBe('A');
    expect(exigeToqueComercial(r.tier)).toBe(true);
    expect(r.emailTipo).toBe('corporativo');
  });

  it('Tier B na faixa 40-69', () => {
    const r = calcularScore({ ...base, skusAno: 60, email: 'x@empresa.com.br' });
    expect(r.score).toBe(45);
    expect(r.tier).toBe('B');
    expect(exigeToqueComercial(r.tier)).toBe(false);
  });

  it('curioso com e-mail pessoal e volume baixo não chega ao BDR', () => {
    const r = calcularScore({
      skusAno: 3,
      economiaCalculada: 12_000,
      setor: 'outro',
      email: 'curioso@gmail.com',
      cargo: 'Freelancer',
      informouReceita: false,
    });
    expect(r.tier).toBe('C');
    expect(exigeToqueComercial(r.tier)).toBe(false);
  });

  it('fronteiras de tier', () => {
    // 70 = A: SKUs ≥ 50 (30) + economia ≥ 500k (25) + corporativo (15)
    const a = calcularScore({
      ...base,
      skusAno: 50,
      economiaCalculada: 500_000,
      email: 'x@empresa.com',
    });
    expect(a.score).toBe(70);
    expect(a.tier).toBe('A');

    // 40 = B: SKUs 20-49 (20) + economia 150k-499k (15) + ... nada = 35 → C
    const c = calcularScore({ ...base, skusAno: 20, economiaCalculada: 150_000 });
    expect(c.score).toBe(35);
    expect(c.tier).toBe('C');
  });

  it('detalha os componentes da nota', () => {
    const r = calcularScore({ ...base, skusAno: 100, setor: 'automotivo' });
    expect(r.detalhe).toEqual([
      { criterio: 'SKUs/ano ≥ 50', pontos: 30 },
      { criterio: 'Setor prioritário (automotivo / máquinas-agro)', pontos: 20 },
    ]);
  });
});
