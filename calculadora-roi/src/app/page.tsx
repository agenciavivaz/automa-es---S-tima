import Link from 'next/link';

const CLIENTES = ['Volkswagen', 'VWCO', 'Embraer', 'iFood', 'Nubank', 'Mercado Livre'];

export default function Landing() {
  return (
    <main className="mx-auto px-6 py-16 md:py-24" style={{ maxWidth: 'var(--max-width)' }}>
      <p className="eyebrow mb-6">Calculadora de ROI · NGI</p>

      <h1 className="display mb-8 text-5xl md:text-7xl">
        Quanto você economiza
        <br />
        gerando infinitas peças
        <br />
        com o mesmo 3D.
      </h1>

      <p className="mb-10 max-w-2xl text-lg" style={{ color: 'var(--setima-muted)' }}>
        Um digital twin substitui o ensaio fotográfico que se repete a cada cor, versão, mercado e
        campanha. Calcule em menos de 90 segundos quanto isso representa no seu budget anual —
        sem cadastro para ver o resultado.
      </p>

      <Link href="/calculadora" className="cta">
        Calcular minha economia <span aria-hidden>→</span>
      </Link>

      <section className="mt-20">
        <p className="eyebrow mb-6">Quem já produz assim</p>
        <ul className="flex flex-wrap gap-x-8 gap-y-4">
          {CLIENTES.map((c) => (
            <li key={c} className="display text-xl" style={{ color: 'var(--setima-muted)' }}>
              {c}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-20 grid gap-6 md:grid-cols-3">
        <Prova numero="+66%" texto="de engajamento com experiências 3D interativas" />
        <Prova numero="+9%" texto="em vendas nas mesmas experiências" />
        <Prova numero="+60" texto="projetos em 2025 economizando milhões frente à produção tradicional" />
      </section>

      <section className="mt-20 max-w-2xl">
        <h2 className="display mb-6 text-3xl">Como o cálculo funciona</h2>
        <ol className="grid gap-5 text-sm" style={{ color: 'var(--setima-muted)' }}>
          <li>
            <strong style={{ color: 'var(--setima-fg)' }}>1. Seu custo hoje.</strong> Diárias de
            produção, refação de ensaio por variação, adaptação por mercado e pós-produção de cada
            peça.
          </li>
          <li>
            <strong style={{ color: 'var(--setima-fg)' }}>2. Seu custo com NGI.</strong> A criação
            dos digital twins no ano 1, e o desdobramento de cada nova peça a partir deles.
          </li>
          <li>
            <strong style={{ color: 'var(--setima-fg)' }}>3. A diferença.</strong> Economia anual,
            payback do twin em meses e projeção de três anos — com os números que você informou.
          </li>
        </ol>
        <p className="mt-8 text-xs" style={{ color: 'var(--setima-muted)' }}>
          Os resultados são estimativas baseadas em benchmarks de mercado e na base de projetos da
          Sétima. Não constituem proposta comercial.
        </p>
      </section>
    </main>
  );
}

function Prova({ numero, texto }: { numero: string; texto: string }) {
  return (
    <div className="card">
      <p className="font-display text-5xl" style={{ color: 'var(--setima-accent)' }}>
        {numero}
      </p>
      <p className="mt-3 text-sm" style={{ color: 'var(--setima-muted)' }}>
        {texto}
      </p>
    </div>
  );
}
