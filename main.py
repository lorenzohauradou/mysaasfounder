import logging
import os
import sys
from datetime import datetime
import time

from config import load_config
from services.domain_manager import DomainManager
from services.email_service import EmailService
from services.chatgpt_integration import ChatGPTIntegration
from services.github_integration import GitHubIntegration
from services.landing_generator import LandingGenerator
from services.vercel_integration import VercelIntegration


# Configurazione del logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = f"{log_dir}/saas_automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("SaaSAutomation")

class SaaSAutomationAgent:
    def __init__(self):
        self.config = load_config()
        
        # Debug per verificare la configurazione di Vercel
        vercel_config = self.config.get("vercel", {})
        vercel_token = vercel_config.get("token", "")
        if vercel_token:
            token_preview = vercel_token[:5] + "..." if len(vercel_token) > 5 else "invalid"
            logger.info(f"Token Vercel caricato con successo: {token_preview}")
        else:
            logger.error("Token Vercel non trovato nella configurazione!")
            
        # Inizializzazione dei servizi
        self.domain_manager = DomainManager(self.config["domain"])
        self.email_service = EmailService(self.config["email"])
        self.github = GitHubIntegration(self.config["github"])
        self.chatgpt = ChatGPTIntegration(self.config["openai"])
        self.landing_generator = LandingGenerator({
            "claude_api_key": self.config["claude"]["api_key"]
        })
        self.vercel = VercelIntegration(self.config["vercel"])

        logger.info("Tutti i moduli sono stati inizializzati")

    def create_saas(self, saas_info):
        """
        Crea un nuovo SaaS sulla base delle informazioni fornite 'saas_info'
        """
        logger.info(f"Creazione di un nuovo SaaS con le seguenti informazioni: {saas_info}")
        
        # 1. Acquisto dominio
        logger.info("Acquisto dominio")
        domain_result = self.domain_manager.purchase_domain(saas_info["domain"])
        logger.info(f"dominio acquistato: {domain_result}")
        if not domain_result:
            logger.error("Errore durante l'acquisto del dominio")
            return False
        
        # 2. Configurazione Email SMTP
        logger.info("Configurazione servizio email")
        email_config = self.email_service.setup_smtp(
            domain=saas_info['domain'],
            contact_email=saas_info['email']
        )
        logger.info(f"email configurata: {email_config}")
        #logger.info("Invio email di test")
        #self.email_service.send_test_email(saas_info['email'])

        # 3. Creazione Repository GitHub
        logger.info(f"Creazione repository GitHub: {saas_info['name']}")
        repo_info = self.github.create_repository(
            name=saas_info['name'],
            refined_description=saas_info['description']  # Uso la descrizione originale, verrà raffinata dall'API GitHub
        )
        logger.info(f"Configurazione webhook GitHub per {repo_info['full_name']}")
        self.github.configure_webhook(repo_info['name'])
        
        # 4. Genera la descrizione raffinata con OpenAI
        logger.info(f"Generazione descrizione raffinata con OpenAI")
        refined_description = self.chatgpt._refine_description(saas_info['description'])
        saas_info['refined_description'] = refined_description
        logger.info(f"Descrizione raffinata: {refined_description}")
        
        # 5. Generazione contenuti Landing Page con openai
        logger.info(f"Generazione contenuti con openai")
        landing_content = self.chatgpt.generate_landing_content(
            name=saas_info['name'],
            description=saas_info['refined_description']
        )
        logger.info(f"contenuti generati: {landing_content}")

        # 6. Creazione landing page con Next.js
        logger.info(f"Creazione landing page")
        landing_page = self.landing_generator.create_landing_page(
            title=saas_info['name'],
            content=landing_content,
            domain=saas_info['domain'],
            project_name=saas_info['name'].lower().replace(" ", "-")
        )

        # 7. Preparazione dei file
        # Aggiunta flag per attivare il miglioramento AI
        saas_info["ai_improved"] = True
        landing_files = self.landing_generator.prepare_landing_files(
            landing_page=landing_page,
            saas_info=saas_info
        )

        # 8. Commit dei file su github
        logger.info(f"Caricamento file su GitHub")
        for file_path, file_content in landing_files.items():
            self.github.add_file_to_repository(
                repo_name=saas_info['name'],
                file_path=file_path,
                file_content=file_content,
                commit_message=f"Aggiunta {file_path}"
            )
        
        # 9. Deployment su Vercel
        logger.info(f"Deployment del progetto su Vercel (con build e push automatico)")
        github_username = self.github.get_username()
        
        # Aggiungiamo un po' di tempo di attesa per assicurarci che GitHub abbia processato tutti i commit
        logger.info("Attesa di 15 secondi per assicurarsi che GitHub abbia processato tutti i commit...")
        time.sleep(15)
        
        try:
            vercel_deployment = self.vercel.deploy_from_github(
                github_repo_owner=github_username,
                github_repo_name=saas_info['name'],
                domain=saas_info['domain']
            )
            
            if vercel_deployment["success"]:
                logger.info(f"Deployment su Vercel completato con successo: {vercel_deployment['deployment_url']}")
                saas_info["deployment_url"] = vercel_deployment['deployment_url']
                
                # Link di accesso rapido per il monitoraggio manuale
                saas_info["vercel_dashboard_url"] = f"https://vercel.com/{github_username}/{saas_info['name']}/deployments"
                logger.info(f"Monitoraggio deployment: {saas_info['vercel_dashboard_url']}")
                
                # 10. Se è stato configurato un dominio personalizzato, configura i record DNS
                if "custom_domain" in vercel_deployment and vercel_deployment["custom_domain"]:
                    logger.info(f"Dominio personalizzato configurato: {vercel_deployment['custom_domain']['domain']}")
                    
                    # Ottieni i record DNS necessari da Vercel
                    if "dns_records" in vercel_deployment["custom_domain"]:
                        dns_records = vercel_deployment["custom_domain"]["dns_records"]
                        
                        # Aggiungiamo i record DNS standard per Vercel se non sono già inclusi
                        standard_records = [
                            {
                                "type": "A",
                                "name": "@",
                                "value": "76.76.21.21",
                                "ttl": 3600
                            },
                            {
                                "type": "CNAME",
                                "name": "www",
                                "value": f"{saas_info['domain']}",
                                "ttl": 3600
                            }
                        ]
                        
                        # Combina i record standard con quelli forniti da Vercel
                        all_records = standard_records + dns_records
                        
                        # Configura i record DNS
                        logger.info(f"Configurazione {len(all_records)} record DNS per {saas_info['domain']}")
                        dns_result = self.domain_manager.configure_dns(saas_info['domain'], all_records)
                        
                        if dns_result:
                            logger.info(f"Configurazione DNS completata con successo")
                            saas_info["dns_configured"] = True
                        else:
                            logger.error(f"Errore nella configurazione DNS")
                            saas_info["dns_configured"] = False
            else:
                logger.error(f"Errore durante il deployment su Vercel: {vercel_deployment.get('error', 'Errore sconosciuto')}")
                # Salva comunque l'URL di Vercel per verifica manuale
                saas_info["vercel_dashboard_url"] = f"https://vercel.com/{github_username}/{saas_info['name']}/deployments"
                logger.info(f"Verificare manualmente il deployment: {saas_info['vercel_dashboard_url']}")
        except Exception as e:
            logger.error(f"Eccezione durante il deployment su Vercel: {str(e)}")
            logger.info(f"Verificare manualmente il progetto su GitHub: https://github.com/{github_username}/{saas_info['name']}")

        return True

def main():
    agent = SaaSAutomationAgent()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saas_info = {
    "name": "financial-planner",
    "domain": f"financialplanner{timestamp}.com",
    "description": "Una piattaforma innovativa per pianificare il tuo futuro finanziario",
    "email": "lorenzooradu@gmail.com"
    }
    result = agent.create_saas(saas_info)

    if result:
        logger.info("Il SaaS è stato creato con successo")
        if "deployment_url" in saas_info:
            logger.info(f"La landing page è disponibile all'indirizzo: {saas_info['deployment_url']}")
        if saas_info.get("dns_configured", False):
            logger.info(f"Il dominio personalizzato {saas_info['domain']} è stato configurato con successo")
    else:
        logger.error("Si è verificato un errore durante la creazione del SaaS")

if __name__ == "__main__":
    main()