import type { Metadata } from 'next';
import Script from 'next/script';
import './globals.css';

const GTM_ID = process.env.NEXT_PUBLIC_GTM_ID ?? 'GTM-TSGKH6D2';

export const metadata: Metadata = {
  title: 'Calculadora de ROI NGI | Sétima',
  description:
    'Descubra quanto sua empresa economizaria por ano trocando produção tradicional de conteúdo por digital twins 3D. Resultado em menos de 90 segundos, sem cadastro.',
  openGraph: {
    title: 'Quanto você economizaria com NGI? | Sétima',
    description:
      'Calcule a economia anual de trocar ensaio fotográfico por digital twin. Sem cadastro para ver o resultado.',
    type: 'website',
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        {/* GTM já implantado pela Sétima — encaminha para o sGTM e a Meta CAPI. */}
        <Script id="gtm" strategy="afterInteractive">
          {`(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','${GTM_ID}');`}
        </Script>
        <noscript>
          <iframe
            src={`https://www.googletagmanager.com/ns.html?id=${GTM_ID}`}
            height="0"
            width="0"
            style={{ display: 'none', visibility: 'hidden' }}
          />
        </noscript>
        {children}
      </body>
    </html>
  );
}
