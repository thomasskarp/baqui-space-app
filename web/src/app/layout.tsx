import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { URL_SITIO } from "./sitio";

const TITULO = "Baqui · El estado de los caminos rurales, visto desde el satélite";
const DESCRIPCION =
  "Baqui muestra si un camino rural está transitable después de la lluvia, con el radar NISAR de la NASA, que ve a través de las nubes.";

export const metadata: Metadata = {
  metadataBase: new URL(URL_SITIO),
  title: TITULO,
  description: DESCRIPCION,
  alternates: { canonical: "/" },
  openGraph: { type: "website", locale: "es_AR", url: "/", siteName: "BAQUI", title: TITULO, description: DESCRIPCION },
  twitter: { card: "summary_large_image", title: TITULO, description: DESCRIPCION },
};

export const viewport: Viewport = {
  themeColor: "#060a13",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body>
        {/* Sin JavaScript no corre el revelado al hacer scroll: que se vea todo igual */}
        <noscript>
          <style>{`.reveal{opacity:1;transform:none}`}</style>
        </noscript>
        {children}
      </body>
    </html>
  );
}
