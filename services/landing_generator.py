import logging
import requests
import json
import os
import jinja2
from datetime import datetime
from anthropic import Anthropic
from io import BytesIO
import zipfile

logger = logging.getLogger("SaaSAutomation.LandingGenerator")

class LandingGenerator:
    """
    Gestisce la creazione e pubblicazione di landing page
    """
    
    def __init__(self, config):
        # Aggiungi API key per Claude
        self.claude_api_key = config.get("claude_api_key", "")
        
        # Template base per la landing page
        self.template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        os.makedirs(self.template_dir, exist_ok=True)
        
        # Crea il template di base se non esiste
        self._ensure_base_template()
        
        logger.info("LandingGenerator inizializzato")

    def create_landing_page(self, title, content, domain=None, project_name=None):
        """
        Prepara i dati per una landing page NextJS senza creare directory fisiche
        
        Args:
            title: Titolo della landing page
            content: Contenuti strutturati generati per la landing page
            domain: Nome di dominio (opzionale)
            project_name: Nome del progetto (opzionale)
            
        Returns:
            dict: Informazioni per la generazione dei file della landing page
        """
        logger.info(f"Preparazione dati per landing page: {title}")
        
        # Verifica il formato dei contenuti
        if isinstance(content, dict) and ("metadata" in content or "hero" in content):
            # Contenuti già in formato strutturato (nuovo formato JSON)
            structured_content = content
        else:
            # Converti il vecchio formato in quello nuovo
            structured_content = {
                "metadata": {
                    "title": title,
                    "description": f"Landing page per {title}, un SaaS innovativo"
                },
                "hero": {
                    "headline": content.get("headline", f"Benvenuto in {title}"),
                    "subheadline": content.get("subheadline", "La soluzione SaaS perfetta per le tue esigenze"),
                    "cta_primary": content.get("call_to_action", "Inizia Ora"),
                    "cta_secondary": "Scopri di più"
                },
                "features": [
                    {
                        "title": feature.get("title", "Funzionalità"),
                        "description": feature.get("description", "Descrizione della funzionalità"),
                        "icon": "chart"  # Icona predefinita
                    } for feature in content.get("features", [])
                ],
                "testimonials": [
                    {
                        "quote": content.get("testimonial", {}).get("text", "Testimonianza cliente"),
                        "author": content.get("testimonial", {}).get("author", "Cliente"),
                        "company": content.get("testimonial", {}).get("company", "Azienda"),
                        "role": "Cliente"
                    }
                ]
            }
        
        # Aggiungi il dominio alle informazioni
        if domain:
            structured_content["domain"] = domain
        
        # Usa il nome progetto passato come parametro o genera un nome adatto
        if project_name is None:
            project_name = title.lower().replace(" ", "-").replace("_", "-")
            project_name = ''.join(c for c in project_name if c.isalnum() or c == '-')
            if not project_name or len(project_name) < 3:
                project_name = "saas-landing-page"
        
        # Usa il nome progetto per la directory
        logger.info(f"Nome progetto utilizzato: {project_name}")
        
        # Ritorna le informazioni necessarie senza creare directory fisiche
        return {
            "content": structured_content,  # Contenuti strutturati per Next.js
            "project_name": project_name,   # Nome del progetto
            "title": title                  # Titolo della landing page
        }

    def prepare_landing_files(self, landing_page, saas_info=None):
        """
        Prepara i file per la landing page senza creare directory fisiche
        
        Args:
            landing_page: Oggetto contenente le informazioni sulla landing page
            saas_info: Informazioni aggiuntive sul SaaS
            
        Returns:
            dict: Dizionario con i file generati
        """
        logger.info("Preparazione file per la landing page")
        
        title = landing_page.get("title", "Landing Page")
        content = landing_page.get("content", {})
        
        # Estrai i dati dal contenuto generato
        metadata = content.get("metadata", {})
        page_title = metadata.get("title", title)
        page_description = metadata.get("description", f"Landing page per {title}")
        
        hero = content.get("hero", {})
        hero_headline = hero.get("headline", f"Scopri {title}")
        hero_subheadline = hero.get("subheadline", "La soluzione SaaS che stavi cercando")
        hero_cta_primary = hero.get("cta_primary", "Inizia Ora")
        hero_cta_secondary = hero.get("cta_secondary", "Scopri di più")
        
        features = content.get("features", [
            {"title": "Facile da usare", "description": "Interfaccia intuitiva che non richiede formazione specifica.", "icon": "settings"},
            {"title": "Altamente personalizzabile", "description": "Adatta la piattaforma alle tue esigenze specifiche.", "icon": "sliders"},
            {"title": "Supporto premium", "description": "Il nostro team è sempre disponibile per aiutarti.", "icon": "life-buoy"}
        ])
        
        testimonials = content.get("testimonials", [
            {"quote": f"Da quando abbiamo iniziato a usare {title}, la nostra produttività è aumentata del 30%.", 
             "author": "Cliente Soddisfatto", "company": "Azienda S.p.A.", "role": "CEO"},
            {"quote": "Un prodotto eccezionale con un supporto clienti straordinario.", 
             "author": "Utente Felice", "company": "Startup Innovativa", "role": "CTO"},
            {"quote": "Non posso più immaginare di lavorare senza questo strumento.", 
             "author": "Professionista", "company": "Consulenza Ltd", "role": "Manager"}
        ])
        
        pricing = content.get("pricing", [
            {"name": "Base", "price": "€9/mese", "description": "Perfetto per iniziare", "features": ["Feature 1", "Feature 2"], "cta": "Inizia gratis", "popular": False},
            {"name": "Pro", "price": "€29/mese", "description": "Per team in crescita", "features": ["Tutto del piano Base", "Feature 3", "Feature 4"], "cta": "Prova gratis", "popular": True},
            {"name": "Enterprise", "price": "Contattaci", "description": "Per grandi organizzazioni", "features": ["Tutto del piano Pro", "Feature 5", "Feature 6"], "cta": "Contattaci", "popular": False}
        ])
        
        cta_section = content.get("cta_section", {
            "headline": "Pronto a iniziare?",
            "subheadline": f"Unisciti a migliaia di utenti soddisfatti che usano {title} ogni giorno.",
            "cta": "Inizia ora"
        })
        
        footer = content.get("footer", {
            "tagline": f"{title} - La tua soluzione SaaS",
            "company_info": f"© {title} {datetime.now().year}. Tutti i diritti riservati."
        })
        
        # File generati (dizionario di percorsi e contenuti)
        files = {}
        
        # README.md
        files["README.md"] = f"""# {page_title}

{page_description}

## Sviluppo

```bash
npm run dev
```

Apri [http://localhost:3000](http://localhost:3000) nel tuo browser per vedere il risultato.
"""
        
        # vercel.json
        files["vercel.json"] = json.dumps({
            "version": 2,
            "framework": "nextjs",
            "buildCommand": "npm run build",
            "devCommand": "npm run dev",
            "installCommand": "npm install",
            "outputDirectory": ".next",
            "regions": ["iad1"],
            "public": True,
            "nodeVersion": "18.x"
        }, indent=2)
        
        # .nvmrc per specificare la versione Node
        files[".nvmrc"] = "18"
        
        # .node-version per sistemi che usano nodenv o altri gestori di versione
        files[".node-version"] = "18.17.0"
        
        # engines.json per Vercel
        files["engines.json"] = json.dumps({
            "node": "18.x"
        }, indent=2)
        
        # package.json
        files["package.json"] = json.dumps({
            "name": title.lower().replace(" ", "-"),
            "version": "0.1.0",
            "private": True,
            "engines": {
                "node": "18.x"
            },
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint"
            },
            "dependencies": {
                "next": "13.5.6",
                "react": "18.2.0",
                "react-dom": "18.2.0",
                "lucide-react": "^0.294.0"
            },
            "devDependencies": {
                "autoprefixer": "^10.4.16",
                "postcss": "^8.4.32",
                "tailwindcss": "^3.3.6"
            }
        }, indent=2)
        
        # Button.jsx
        files["components/ui/Button.jsx"] = """export function Button({
            children,
            variant = "default",
            size = "default",
            className = "",
            ...props
            }) {
            const variants = {
                default: "bg-blue-600 text-white hover:bg-blue-700",
                outline: "border border-blue-600 text-blue-600 hover:bg-blue-50",
                ghost: "text-blue-600 hover:bg-blue-50",
                secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200"
            };

            const sizes = {
                default: "h-10 px-4 py-2",
                sm: "h-8 px-3 py-1 text-sm",
                lg: "h-12 px-6 py-3 text-lg"
            };

            return (
                <button
                className={`inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
                {...props}
                >
                {children}
                </button>
            );
            }
            """
        
        # Placeholder SVG
        files["public/placeholder.svg"] = """<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#f0f0f0"/>
  <path d="M30,50 L70,50 M50,30 L50,70" stroke="#cccccc" stroke-width="4"/>
</svg>"""
        
        # Favicon
        files["public/favicon.ico"] = "" # File binario, da gestire nella versione finale
        
        # tailwind.config.js
        files["tailwind.config.js"] = """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Personalizza i colori qui
      },
    },
  },
  plugins: [],
}
"""
        
        # postcss.config.js
        files["postcss.config.js"] = """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""
        
        # globals.css
        files["app/globals.css"] = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""
        
        # layout.js
        files["app/layout.jsx"] = f"""import './globals.css'

export const metadata = {{
  title: '{page_title}',
  description: '{page_description}',
}}

export default function RootLayout({{ children }}) {{
  return (
    <html lang="it">
      <body>{{children}}</body>
    </html>
  )
}}
"""
        
        # page.js - Utilizziamo i contenuti dinamici generati da ChatGPT qui
        files["app/page.jsx"] = f"""import {{ CheckCircle, Star, Clock, ArrowRight }} from 'lucide-react';
import {{ Button }} from '../components/ui/Button';

export default function Home() {{

  const features = {json.dumps(features)};
  const testimonials = {json.dumps(testimonials)};
  const pricing = {json.dumps(pricing)};
  const title = "{title}";
  const hero_headline = "{hero_headline}";
  const hero_subheadline = "{hero_subheadline}";
  const hero_cta_primary = "{hero_cta_primary}";
  const hero_cta_secondary = "{hero_cta_secondary}";
  const cta_headline = "{cta_section.get('headline', 'Pronto a iniziare?')}";
  const cta_subheadline = "{cta_section.get('subheadline', f'Unisciti a migliaia di utenti soddisfatti che usano {title} ogni giorno.')}";
  const cta_button = "{cta_section.get('cta', 'Inizia ora')}";
  const footer_tagline = "{footer.get('tagline', f'{title} - La tua soluzione SaaS')}";
  const footer_company_info = "{footer.get('company_info', f'© {title} {datetime.now().year}. Tutti i diritti riservati.')}";

  return (
    <main className="flex min-h-screen flex-col">
      {{/* Header */}}
      <header className="sticky top-0 z-40 w-full border-b bg-white">
        <div className="container flex h-16 items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-2 font-bold text-xl">
            {{title}}
          </div>
          <nav className="hidden md:flex gap-6">
            <a href="#features" className="text-sm font-medium hover:underline">
              Funzionalità
            </a>
            <a href="#testimonials" className="text-sm font-medium hover:underline">
              Testimonianze
            </a>
            <a href="#pricing" className="text-sm font-medium hover:underline">
              Prezzi
            </a>
          </nav>
          <div className="flex items-center gap-4">
            <Button variant="ghost">Accedi</Button>
            <Button>Registrati</Button>
          </div>
        </div>
      </header>

      {{/* Hero Section */}}
      <section className="w-full py-12 md:py-24 lg:py-32">
        <div className="container px-4 md:px-6">
          <div className="grid gap-6 lg:grid-cols-2 lg:gap-12 xl:gap-16">
            <div className="flex flex-col justify-center space-y-4">
              <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl lg:text-6xl">
                  {{hero_headline}}
                </h1>
                <p className="max-w-[600px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  {{hero_subheadline}}
                </p>
              </div>
              <div className="flex flex-col gap-2 min-[400px]:flex-row">
                <Button size="lg">{{hero_cta_primary}}</Button>
                <Button size="lg" variant="outline">{{hero_cta_secondary}}</Button>
              </div>
            </div>
            <div className="flex items-center justify-center">
              <img
                src="/placeholder.svg"
                alt="Hero Image"
                width="550"
                height="450"
                className="rounded-xl object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {{/* Features Section */}}
      <section id="features" className="w-full py-12 md:py-24 lg:py-32 bg-gray-50">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <div className="space-y-2">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">
                Funzionalità Principali
              </h2>
              <p className="max-w-[900px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                Scopri cosa rende {{title}} la soluzione perfetta per le tue esigenze.
              </p>
            </div>
          </div>
          <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4 mt-12">
            {{features.map((feature) => (
              <div className="flex flex-col items-start space-y-2 rounded-lg border p-6 shadow-sm">
                <div className="p-2 bg-blue-50 rounded-full">
                  <CheckCircle className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="text-lg font-bold">{{feature.title}}</h3>
                <p className="text-sm text-gray-500">
                  {{feature.description}}
                </p>
              </div>
            ))}}
          </div>
        </div>
      </section>

      {{/* Testimonials Section */}}
      <section id="testimonials" className="w-full py-12 md:py-24 lg:py-32">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <div className="space-y-2">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">
                Cosa Dicono i Nostri Clienti
              </h2>
              <p className="max-w-[900px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                Testimonianze di chi utilizza {{title}} ogni giorno.
              </p>
            </div>
          </div>
          <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 mt-12">
            {{testimonials.map((testimonial) => (
              <div className="flex flex-col items-start space-y-4 rounded-lg border p-6 shadow-sm">
                <div className="flex items-center">
                  <Star className="h-5 w-5 text-yellow-500" />
                  <Star className="h-5 w-5 text-yellow-500" />
                  <Star className="h-5 w-5 text-yellow-500" />
                  <Star className="h-5 w-5 text-yellow-500" />
                  <Star className="h-5 w-5 text-yellow-500" />
                </div>
                <p className="text-sm text-gray-500">"{{testimonial.quote}}"</p>
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-full bg-gray-200"></div>
                  <div>
                    <p className="text-sm font-medium">{{testimonial.author}}</p>
                    <p className="text-xs text-gray-500">{{testimonial.role}}, {{testimonial.company}}</p>
                  </div>
                </div>
              </div>
            ))}}
          </div>
        </div>
      </section>

      {{/* Pricing Section */}}
      <section id="pricing" className="w-full py-12 md:py-24 lg:py-32 bg-gray-50">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <div className="space-y-2">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">
                Piani e Prezzi
              </h2>
              <p className="max-w-[900px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                Scegli il piano più adatto alle tue esigenze.
              </p>
            </div>
          </div>
          <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 mt-12">
            {{pricing.map((plan) => (
              <div className={{`flex flex-col items-start space-y-4 rounded-lg border p-6 shadow-sm ${{plan.popular ? 'relative' : ''}}`}}>
                {{plan.popular && <div className="absolute -top-3 right-6 bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-bold">Popolare</div>}}
                <div className="space-y-2">
                  <h3 className="text-xl font-bold">{{plan.name}}</h3>
                  <p className="text-sm text-gray-500">{{plan.description}}</p>
                </div>
                <p className="text-3xl font-bold">{{plan.price}}</p>
                <ul className="grid gap-2 py-4">
                  {{plan.features.map((feature) => (
                    <li className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-blue-600" />
                      <span className="text-sm">{{feature}}</span>
                    </li>
                  ))}}
                </ul>
                <Button className="w-full">{{plan.cta}}</Button>
              </div>
            ))}}
          </div>
        </div>
      </section>

      {{/* CTA Section */}}
      <section className="w-full py-12 md:py-24 lg:py-32">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <div className="space-y-2">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">
                {{cta_headline}}
              </h2>
              <p className="max-w-[900px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                {{cta_subheadline}}
              </p>
            </div>
            <div className="flex flex-col gap-2 min-[400px]:flex-row">
              <Button size="lg">
                {{cta_button}}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </section>

      {{/* Footer */}}
      <footer className="w-full py-6 md:py-12 bg-gray-800 text-white">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <div className="space-y-2">
              <p className="text-lg font-medium">{{footer_tagline}}</p>
              <p className="text-sm text-gray-300">
                {{footer_company_info}}
              </p>
            </div>
            <div className="flex gap-4">
              <a href="#" className="text-sm hover:underline">Privacy Policy</a>
              <a href="#" className="text-sm hover:underline">Termini di Servizio</a>
              <a href="#" className="text-sm hover:underline">Contatti</a>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}}
"""
        
        # next.config.js
        files["next.config.js"] = """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = nextConfig
"""
        
        # Verifica che tutti i file essenziali siano presenti
        files = self._ensure_essential_nextjs_files(files, title)
        
        # Aggiungi i file generati con AI se disponibili
        if saas_info and saas_info.get("ai_improved", False):
            logger.info("Miglioramento dei file con AI")
            try:
                generated_files = self.refine_landing_with_ai(files, saas_info)
                return generated_files
            except Exception as e:
                logger.error(f"Errore durante il miglioramento con AI: {str(e)}")
                logger.info("Utilizzo dei file standard")
                return files
                
        return files
    
    def refine_landing_with_ai(self, generated_files, saas_info):
        """Utilizza Claude per migliorare la landing page esistente con suggerimenti di design e contenuto"""
        logger.info("Richiesta miglioramenti alla landing page tramite API Claude")
        
        if not self.claude_api_key:
            logger.warning("API key per Claude non configurata, saltando il miglioramento AI")
            return generated_files
        
        # Estrai il file principale del template
        page_jsx = generated_files.get("app/page.jsx", "")
        
        # Debug logging
        logger.debug(f"Lunghezza codice JSX: {len(page_jsx)} caratteri")
        
        # Usa la descrizione raffinata se disponibile, altrimenti usa quella originale
        description = saas_info.get('refined_description', saas_info.get('description', ''))
        logger.info(f"Utilizzo descrizione {'raffinata' if 'refined_description' in saas_info else 'originale'} per migliorare la landing page")
        
        try:
            logger.info("Inizializzazione client Anthropic...")
            client = Anthropic(api_key=self.claude_api_key)
            
            # Colore principale coerente con il brand SaaS
            brand_color = "#3b82f6"  # Blu di default
            saas_name = saas_info.get('name', 'SaaS')
            
            enhancement_prompt = f"""
                    # Miglioramento Landing Page Esistente

                    Sei un designer ed esperto sviluppatore React/Next.js. Ti fornisco il codice di una landing page esistente per un SaaS chiamato "{saas_name}" che si occupa di:

                    {description}

                    ## Compito
                    Il tuo compito è migliorare l'aspetto visivo e l'impatto di questa landing page esistente. NON creare una landing page completamente nuova, ma migliora quella fornita.

                    ## Codice Esistente
                    ```jsx
                    {page_jsx}
                    ```

                    ## Miglioramenti Richiesti
                    1. Migliora la palette colori mantenendo {brand_color} come colore primario, usando colori complementari per maggiore armonia visiva
                    2. Aggiungi effetti hover e transizioni fluide (max 300ms) per una migliore esperienza utente
                    3. Migliora la responsività e la leggibilità, soprattutto su dispositivi mobili
                    4. Aggiungi elementi visivi come icone, separatori o gradienti sottili dove appropriato
                    5. Ottimizza gli spazi, i margini e la tipografia per una migliore scansione visiva
                    6. Mantieni la stessa struttura generale delle sezioni e la logica dei componenti

                    ## Importante
                    - Conserva tutti i componenti e le funzionalità esistenti
                    - Non cambiare la logica del codice o il modo in cui i dati vengono passati
                    - Mantieni tutte le sezioni: header, hero, features, testimonials, pricing, CTA, footer
                    - Restituisci solo il codice JSX aggiornato, senza spiegazioni aggiuntive
                    - Assicurati che il codice sia completo e valido al 100%

                    ## Output
                    Restituisci SOLO il codice JSX completo del file app/page.jsx migliorato, senza commenti introduttivi o conclusivi.
                    """
            
            logger.info("Invio richiesta a Claude API per miglioramenti della landing page...")
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=8000,  # Aumentato per evitare troncamenti
                temperature=0.5,  # Temperatura più bassa per miglioramenti più conservativi
                messages=[
                    {"role": "user", "content": enhancement_prompt}
                ]
            )
            
            # Estrai il contenuto dalla risposta
            improved_jsx = response.content[0].text.strip()
            
            # Rimuovi eventuali delimitatori di markdown
            if improved_jsx.startswith("```jsx"):
                improved_jsx = improved_jsx[7:]
            elif improved_jsx.startswith("```"):
                improved_jsx = improved_jsx[3:]
            
            if improved_jsx.endswith("```"):
                improved_jsx = improved_jsx[:-3]
            
            improved_jsx = improved_jsx.strip()
            
            # Verifica che il contenuto sia valido
            if improved_jsx and "import" in improved_jsx and "export default" in improved_jsx:
                logger.info("Landing page migliorata con successo!")
                generated_files["app/page.jsx"] = improved_jsx
            else:
                logger.warning("Contenuto migliorato non valido, mantengo la versione originale")
                
        except Exception as e:
            logger.error(f"Errore durante il miglioramento della landing page: {str(e)}", exc_info=True)
            logger.info("Continuo con la versione originale della landing page")
        
        return generated_files
    
    def _ensure_base_template(self):
        """Crea il template di base se non esiste"""
        template_path = os.path.join(self.template_dir, "base_template.html")
        if not os.path.exists(template_path):
            # Crea un template base minimo
            with open(template_path, "w", encoding="utf-8") as f:
                f.write("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <meta name="description" content="{{ description }}">
    <style>
        /* Stili di base */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            color: #333;
        }
        .container {
            width: 90%;
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem;
        }
        header {
            background-color: #f8f9fa;
            padding: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .hero {
            padding: 3rem 0;
            background-color: #f1f5f9;
        }
        .btn {
            display: inline-block;
            padding: 0.5rem 1rem;
            background-color: #3b82f6;
            color: white;
            text-decoration: none;
            border-radius: 0.25rem;
            font-weight: 600;
        }
        .features {
            padding: 3rem 0;
        }
        footer {
            background-color: #333;
            color: white;
            padding: 2rem 0;
            margin-top: 2rem;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>{{ title }}</h1>
            <nav>
                <a href="#features">Funzionalità</a>
                <a href="#about">Chi siamo</a>
                <a href="#contact">Contatti</a>
            </nav>
        </div>
    </header>

    <section class="hero">
        <div class="container">
            <h2>{{ headline }}</h2>
            <p>{{ subheadline }}</p>
            <a href="#" class="btn">{{ call_to_action }}</a>
        </div>
    </section>

    <section id="features" class="features">
        <div class="container">
            <h2>Funzionalità principali</h2>
            <div class="features-grid">
                {% for feature in features %}
                <div class="feature">
                    <h3>{{ feature.title }}</h3>
                    <p>{{ feature.description }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>

    <footer>
        <div class="container">
            <p>&copy; {{ year }} {{ title }}. Tutti i diritti riservati.</p>
        </div>
    </footer>
</body>
</html>
""")
            logger.info("Creato template base per la landing page")

    def _ensure_essential_nextjs_files(self, files, project_name):
        """
        Verifica che tutti i file essenziali per un progetto Next.js siano presenti
        
        Args:
            files: Dizionario con i file generati
            project_name: Nome del progetto
            
        Returns:
            dict: Dizionario aggiornato con i file essenziali aggiunti se mancanti
        """
        logger.info("Verifica dei file essenziali per Next.js")
        
        # Lista dei file essenziali
        essential_files = [
            "package.json",
            "next.config.js",
            "app/page.jsx",
            "app/layout.jsx",
            "app/globals.css",
            "tailwind.config.js",
            "postcss.config.js",
            ".nvmrc",
            "vercel.json"
        ]
        
        for file in essential_files:
            if file not in files:
                logger.warning(f"File essenziale mancante: {file}, creazione automatica...")
                
                # Crea i file mancanti con contenuti predefiniti
                if file == "package.json":
                    files[file] = json.dumps({
                        "name": project_name.lower().replace(" ", "-"),
                        "version": "0.1.0",
                        "private": True,
                        "engines": {"node": "18.x"},
                        "scripts": {
                            "dev": "next dev",
                            "build": "next build",
                            "start": "next start"
                        },
                        "dependencies": {
                            "next": "13.5.6",
                            "react": "18.2.0",
                            "react-dom": "18.2.0"
                        },
                        "devDependencies": {
                            "autoprefixer": "^10.4.16",
                            "postcss": "^8.4.32",
                            "tailwindcss": "^3.3.6"
                        }
                    }, indent=2)
                elif file == "next.config.js":
                    files[file] = "/** @type {import('next').NextConfig} */\nmodule.exports = {reactStrictMode: true};"
                elif file == "app/page.jsx":
                    files[file] = "export default function Home() {\n  return <div>Welcome to Next.js!</div>;\n};"
                elif file == "app/layout.jsx":
                    files[file] = "export default function RootLayout({ children }) {\n  return (\n    <html lang=\"it\">\n      <body>{children}</body>\n    </html>\n  );\n};"
                elif file == "app/globals.css":
                    files[file] = "@tailwind base;\n@tailwind components;\n@tailwind utilities;"
                elif file == "tailwind.config.js":
                    files[file] = "module.exports = {\n  content: [\n    './app/**/*.{js,jsx,ts,tsx}',\n    './components/**/*.{js,jsx,ts,tsx}',\n  ],\n  theme: {\n    extend: {},\n  },\n  plugins: [],\n};"
                elif file == "postcss.config.js":
                    files[file] = "module.exports = {\n  plugins: {\n    tailwindcss: {},\n    autoprefixer: {}\n  }\n};"
                elif file == ".nvmrc":
                    files[file] = "18"
                elif file == "vercel.json":
                    files[file] = json.dumps({
                        "version": 2,
                        "framework": "nextjs",
                        "buildCommand": "npm run build",
                        "outputDirectory": ".next"
                    }, indent=2)
        
        return files
