import logging
import openai
import json
import re



logger = logging.getLogger(__name__)

class ChatGPTIntegration:
    def __init__(self, config):
        self.api_key = config['api_key']
        openai.api_key = self.api_key

    def generate_landing_content(self, name, description, tone="professional"):
        """
        Genera contenuti per la landing page utilizzando ChatGPT
        
        Args:
            name: Nome del SaaS
            description: Descrizione breve del SaaS
            tone: Tono dei contenuti (professional, friendly, technical)
            
        Returns:
            dict: Contenuti generati per la landing page
        """
        logger.info(f"Generazione contenuti per landing page: {name}")

        # Crea il prompt per la generazione dei contenuti
        prompt = self._create_landing_prompt(name, description, tone)
        logger.info(f"Prompt generato: {prompt}")
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sei un copywriter esperto nella creazione di landing page efficaci per SaaS."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content_json = response.choices[0].message.content
            logger.info(f"Contenuto generato: {content_json}")
            
            # Tenta di analizzare il JSON restituito
            try:
                # Rimuovi delimitatori di markdown se presenti
                if content_json.startswith("```json"):
                    # Trova la prima occorrenza di newline dopo ```json
                    first_newline = content_json.find("\n")
                    if first_newline != -1:
                        content_json = content_json[first_newline+1:]
                    
                    # Rimuovi l'ultimo ``` se presente
                    if content_json.endswith("```"):
                        content_json = content_json[:-3].strip()
                
                # Converti la stringa JSON in un dizionario Python
                content = json.loads(content_json)
                logger.info("Contenuti generati con successo")
                return content
                
            except json.JSONDecodeError as e:
                error_msg = f"Errore nella decodifica JSON: {str(e)}"
                logger.error(error_msg)
                # Se il contenuto non è un JSON valido, prova una analisi manuale
                content = {"headline": name, "subheadline": description}
                return content
            
        except Exception as e:
            error_msg = f"Errore nella generazione dei contenuti: {str(e)}"
            logger.error(error_msg)
            
            # Fallback con contenuti di base
            return self._fallback_content(name, description)
        
    def _refine_description(self, description):
        """
        ottiene una descrizione del SaaS piu dettagliata partendo da quella breve dell' utente utilizzando ChatGPT
        """
        logger.info(f"Raffinazione descrizione: {description}")
        
        prompt = f"""
        Descrizione del SaaS: {description}
        
        Per il seguente SaaS, crea una descrizione più dettagliata.
        Assicurati di includere tutti i punti salienti e le funzionalità principali. focalizzati sui problemi che risolve e sui benefici che offre e sul perche i clienti dovrebbero sceglierlo rispetto ai concorrenti.
        
        Descrizione del SaaS:
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sei un copywriter esperto nella creazione di descrizioni accattivanti per SaaS."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )   
            refined_description = response.choices[0].message.content.strip()
            logger.info(f"Descrizione raffinata: {refined_description}")
            return refined_description
        
        except Exception as e:
            error_msg = f"Errore nella raffinazione della descrizione: {str(e)}"
            logger.error(error_msg)
            return description
        

    def _create_landing_prompt(self, name, description, tone):
        """
        Crea un prompt per la generazione di contenuti della landing page
        
        Args:
            name: Nome del SaaS
            description: Descrizione del SaaS
            tone: Tono dei contenuti
            
        Returns:
            str: Prompt per ChatGPT
        """
        return f"""
        Genera contenuti dettagliati per una landing page moderna e professionale per un SaaS chiamato "{name}".
        
        Descrizione del SaaS: {description}
        
        Tono desiderato: {tone}
        
        Includi i seguenti elementi in formato JSON:
        
        1. "metadata": Informazioni base
           - "title": Titolo della pagina (includi il nome del SaaS)
           - "description": Meta descrizione SEO
        
        2. "hero": Sezione principale
           - "headline": Un titolo principale accattivante (massimo 10 parole)
           - "subheadline": Un sottotitolo che espande il titolo (massimo 20 parole)
           - "cta_primary": Testo per il pulsante principale di call-to-action
           - "cta_secondary": Testo per il pulsante secondario (opzionale)
        
        3. "features": Array di 4 funzionalità principali, ciascuna con:
           - "title": Titolo della funzionalità
           - "description": Breve descrizione (2-3 frasi)
           - "icon": Suggerimento per un'icona (es. "chart", "users", "clock", ecc.)
        
        4. "testimonials": Array di 3 testimonianze, ciascuna con:
           - "quote": Testo della testimonianza
           - "author": Nome del cliente
           - "company": Azienda del cliente
           - "role": Ruolo del cliente
        
        5. "pricing": Array di 3 piani di prezzo, ciascuno con:
           - "name": Nome del piano (es. "Base", "Pro", "Enterprise")
           - "price": Prezzo mensile
           - "description": Breve descrizione
           - "features": Array di stringhe con funzionalità incluse
           - "cta": Testo del pulsante
           - "popular": Booleano se è il piano consigliato
        
        6. "cta_section": Sezione finale call-to-action
           - "headline": Titolo della sezione
           - "subheadline": Sottotitolo
           - "cta": Testo del pulsante
        
        7. "footer": Informazioni per il footer
           - "tagline": Breve slogan
           - "company_info": Informazioni sull'azienda
        
        Rispondi SOLO con un oggetto JSON valido e ben formattato contenente questi campi, senza spiegazioni o commenti aggiuntivi.
        """
        
    def _fallback_content(self, name, description):
        """
        Genera contenuti di base per la landing page in caso di fallimento dell'API
        
        Args:
            name: Nome del SaaS
            description: Descrizione del SaaS
            
        Returns:
            dict: Contenuti base per la landing page
        """
        logger.info(f"Generazione contenuti di fallback per: {name}")
        
        # Crea un dizionario strutturato con i contenuti minimi
        return {
            "metadata": {
                "title": f"{name} - La tua soluzione SaaS",
                "description": f"Landing page per {name}, un SaaS innovativo"
            },
            "hero": {
                "headline": f"Benvenuto in {name}",
                "subheadline": "La soluzione SaaS perfetta per le tue esigenze",
                "cta_primary": "Inizia Ora",
                "cta_secondary": "Scopri di più"
            },
            "features": [
                {
                    "title": "Facile da usare",
                    "description": "Interfaccia intuitiva che non richiede formazione specifica.",
                    "icon": "settings"
                },
                {
                    "title": "Altamente personalizzabile",
                    "description": "Adatta la piattaforma alle tue esigenze specifiche.",
                    "icon": "sliders"
                },
                {
                    "title": "Supporto premium",
                    "description": "Il nostro team è sempre disponibile per aiutarti.",
                    "icon": "life-buoy"
                }
            ],
            "testimonials": [
                {
                    "quote": f"Da quando abbiamo iniziato a usare {name}, la nostra produttività è aumentata del 30%.",
                    "author": "Cliente Soddisfatto",
                    "company": "Azienda S.p.A.",
                    "role": "CEO"
                }
            ],
            "pricing": [
                {
                    "name": "Base",
                    "price": "€9/mese",
                    "description": "Perfetto per iniziare",
                    "features": ["Feature 1", "Feature 2"],
                    "cta": "Inizia gratis",
                    "popular": False
                },
                {
                    "name": "Pro",
                    "price": "€29/mese",
                    "description": "Per team in crescita",
                    "features": ["Tutto del piano Base", "Feature 3", "Feature 4"],
                    "cta": "Prova gratis",
                    "popular": True
                }
            ],
            "cta_section": {
                "headline": "Pronto a iniziare?",
                "subheadline": f"Unisciti a migliaia di utenti soddisfatti che usano {name} ogni giorno.",
                "cta": "Inizia ora"
            }
        }
        
        