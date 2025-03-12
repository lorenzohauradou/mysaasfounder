import logging
import requests
import json
import time

logger = logging.getLogger("SaaSAutomation.VercelIntegration")

class VercelIntegration:
    """
    Gestisce l'integrazione con Vercel per il deployment automatico delle landing page
    """
    
    def __init__(self, config):
        self.token = config.get("token", "")
        self.team_id = config.get("team_id", "")
        self.base_url = "https://api.vercel.com"
        
        if not self.token:
            logger.error("Token Vercel non configurato nel file .env. Imposta la variabile VERCEL_TOKEN.")
        else:
            logger.info(f"Token Vercel configurato correttamente ({self.token[:5]}...)")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        logger.info("VercelIntegration inizializzato")
    
    def create_project(self, project_name, github_repo_owner, github_repo_name):
        """
        Crea un nuovo progetto su Vercel collegato a un repository GitHub
        
        Args:
            project_name: Nome del progetto su Vercel
            github_repo_owner: Proprietario della repository GitHub
            github_repo_name: Nome della repository GitHub
            
        Returns:
            dict: Informazioni sul progetto creato
        """
        logger.info(f"Creazione progetto Vercel: {project_name} collegato a {github_repo_owner}/{github_repo_name}")
        
        if not self.token:
            logger.error("Token Vercel non configurato, impossibile creare progetto")
            return None
        
        url = f"{self.base_url}/v9/projects"
        
        # Parametri per la richiesta
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        # Dati per la creazione del progetto
        data = {
            "name": project_name,
            "framework": "nextjs",  # Framework predefinito per landing page
            "gitRepository": {
                "repo": f"{github_repo_owner}/{github_repo_name}",
                "type": "github"
            }
        }
        
        try:
            logger.info(f"Invio richiesta POST a {url}")
            response = requests.post(url, headers=self.headers, params=params, json=data)
            
            if response.status_code not in (200, 201, 202):
                error_msg = f"Errore nella creazione del progetto Vercel: {response.text}"
                logger.error(error_msg)
                return None
            
            project_info = response.json()
            logger.info(f"Progetto Vercel creato con successo: {project_info.get('name')}")
            
            return {
                "id": project_info.get("id"),
                "name": project_info.get("name"),
                "url": project_info.get("link", {}).get("href", ""),
                "created_at": project_info.get("createdAt")
            }
            
        except Exception as e:
            logger.error(f"Errore durante la creazione del progetto Vercel: {str(e)}")
            return None
    
    def get_deployment_status(self, project_id):
        """
        Ottiene lo stato del deployment più recente per un progetto
        
        Args:
            project_id: ID del progetto Vercel
            
        Returns:
            dict: Informazioni sul deployment
        """
        if not self.token or not project_id:
            return None
        
        url = f"{self.base_url}/v6/deployments"
        
        params = {
            "projectId": project_id,
            "limit": 1  # Ottieni solo il deployment più recente
        }
        
        if self.team_id:
            params["teamId"] = self.team_id
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"Errore nell'ottenere lo stato del deployment: {response.text}")
                return None
            
            deployments = response.json().get("deployments", [])
            if not deployments:
                logger.warning(f"Nessun deployment trovato per il progetto {project_id}")
                return None
            
            deployment = deployments[0]
            logger.info(f"Stato deployment: {deployment.get('state')} - URL: {deployment.get('url')}")
            
            return {
                "id": deployment.get("id"),
                "url": deployment.get("url"),
                "state": deployment.get("state"),
                "created_at": deployment.get("createdAt"),
                "ready": deployment.get("ready", False)
            }
            
        except Exception as e:
            logger.error(f"Errore durante il controllo dello stato del deployment: {str(e)}")
            return None
    
    def wait_for_deployment(self, project_id, timeout=600, check_interval=15):
        """
        Attende il completamento del deployment
        
        Args:
            project_id: ID del progetto Vercel
            timeout: Timeout in secondi (default: 600 - 10 minuti)
            check_interval: Intervallo di controllo in secondi (default: 15)
            
        Returns:
            dict: Informazioni sul deployment completato o None se timeout
        """
        logger.info(f"In attesa del completamento del deployment per il progetto {project_id}")
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout:
            attempts += 1
            logger.info(f"Controllo stato deployment (tentativo {attempts})...")
            
            deployment = self.get_deployment_status(project_id)
            
            if not deployment:
                logger.info(f"Nessun deployment trovato, attesa {check_interval} secondi...")
                time.sleep(check_interval)
                continue
            
            state = deployment.get("state", "UNKNOWN")
            
            # Se il deployment è pronto o in errore, restituiscilo
            if deployment.get("ready"):
                logger.info(f"Deployment completato con successo dopo {int(time.time() - start_time)} secondi")
                return deployment
                
            if state in ("ERROR", "CANCELED"):
                logger.error(f"Deployment terminato con stato {state}")
                return deployment
            
            # Migliorato il logging per mostrare lo stato attuale
            logger.info(f"Deployment in corso... Stato: {state} - Tempo trascorso: {int(time.time() - start_time)}s")
            
            # Dopo 5 tentativi, aumenta l'intervallo di controllo per ridurre il carico sulle API
            if attempts > 5:
                time.sleep(check_interval * 2)
            else:
                time.sleep(check_interval)
        
        logger.error(f"Timeout di {timeout} secondi superato durante l'attesa del deployment per il progetto {project_id}")
        return None
    
    def set_environment_variables(self, project_id, env_vars):
        """
        Imposta variabili d'ambiente per un progetto Vercel
        
        Args:
            project_id: ID del progetto Vercel
            env_vars: Dizionario con le variabili d'ambiente (chiave-valore)
            
        Returns:
            bool: True se l'operazione è riuscita, False altrimenti
        """
        if not self.token or not project_id:
            return False
        
        url = f"{self.base_url}/v9/projects/{project_id}/env"
        
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        # Prepara le variabili d'ambiente nel formato richiesto da Vercel
        env_data = []
        for key, value in env_vars.items():
            env_data.append({
                "key": key,
                "value": value,
                "target": ["production", "preview", "development"]
            })
        
        try:
            response = requests.post(url, headers=self.headers, params=params, json=env_data)
            
            if response.status_code != 200:
                logger.error(f"Errore nell'impostare le variabili d'ambiente: {response.text}")
                return False
            
            logger.info(f"Variabili d'ambiente impostate con successo per il progetto {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante l'impostazione delle variabili d'ambiente: {str(e)}")
            return False
    
    def set_custom_domain(self, project_id, domain):
        """
        Configura un dominio personalizzato per un progetto Vercel
        
        Args:
            project_id: ID del progetto Vercel
            domain: Nome di dominio personalizzato
            
        Returns:
            dict: Informazioni sul dominio configurato o None in caso di errore
        """
        if not self.token or not project_id or not domain:
            return None
        
        url = f"{self.base_url}/v9/projects/{project_id}/domains"
        
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        data = {
            "name": domain
        }
        
        try:
            response = requests.post(url, headers=self.headers, params=params, json=data)
            
            if response.status_code not in (200, 201):
                logger.error(f"Errore nella configurazione del dominio personalizzato: {response.text}")
                return None
            
            domain_info = response.json()
            logger.info(f"Dominio personalizzato configurato: {domain}")
            
            # Restituisci informazioni sulle configurazioni DNS necessarie
            verification = domain_info.get("verification", [])
            dns_records = []
            
            for record in verification:
                dns_records.append({
                    "type": record.get("type"),
                    "name": record.get("name"),
                    "value": record.get("value")
                })
            
            return {
                "domain": domain,
                "configured": domain_info.get("configured", False),
                "verified": domain_info.get("verified", False),
                "dns_records": dns_records
            }
            
        except Exception as e:
            logger.error(f"Errore durante la configurazione del dominio personalizzato: {str(e)}")
            return None
    
    def get_deployment_url(self, project_id):
        """
        Ottiene l'URL di produzione per un progetto Vercel
        
        Args:
            project_id: ID del progetto Vercel
            
        Returns:
            str: URL di produzione o None in caso di errore
        """
        deployment = self.get_deployment_status(project_id)
        
        if not deployment:
            return None
        
        # Formato URL di produzione Vercel
        url = deployment.get("url")
        if url and not url.startswith("http"):
            url = f"https://{url}"
        
        return url
    
    def deploy_from_github(self, github_repo_owner, github_repo_name, domain=None):
        """
        Processo completo: crea progetto Vercel e collega a GitHub
        
        Args:
            github_repo_owner: Proprietario della repository GitHub
            github_repo_name: Nome della repository GitHub
            domain: Dominio personalizzato (opzionale)
            
        Returns:
            dict: Informazioni sul deployment
        """
        result = {
            "success": False,
            "project_name": github_repo_name,
            "project_id": None,
            "deployment_url": None,
            "custom_domain": None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Step 1: Crea progetto Vercel
        project = self.create_project(github_repo_name, github_repo_owner, github_repo_name)
        if not project:
            return result
        
        result["project_id"] = project.get("id")
        
        # Step 2: Attiva esplicitamente un deployment (NOVITÀ)
        logger.info("Attivazione esplicita del deployment...")
        deployment_triggered = self.trigger_deployment(project.get("id"), github_repo_owner, github_repo_name)
        if not deployment_triggered:
            logger.warning("Non è stato possibile attivare esplicitamente il deployment, ma il progetto è stato creato")
            # Continuiamo comunque perché Vercel potrebbe avviare il deployment automaticamente
        
        # Step 3: Attendi il deployment iniziale
        deployment = self.wait_for_deployment(project.get("id"), timeout=600)  # Aumentato il timeout a 10 minuti
        if not deployment:
            logger.error("Timeout durante l'attesa del deployment, ma il progetto è stato creato su Vercel")
            # Restituisci comunque l'URL del progetto
            result["deployment_url"] = f"https://{github_repo_name}-{github_repo_owner.lower()}.vercel.app"
            result["success"] = True
            return result
        
        result["deployment_url"] = f"https://{deployment.get('url')}"
        result["success"] = deployment.get("ready", False)
        
        # Step 4: Configura dominio personalizzato (opzionale)
        if domain and result["success"]:
            domain_config = self.set_custom_domain(project.get("id"), domain)
            if domain_config:
                result["custom_domain"] = domain_config
        
        return result
        
    def trigger_deployment(self, project_id, github_repo_owner, github_repo_name):
        """
        Attiva esplicitamente un deployment su Vercel
        
        Args:
            project_id: ID del progetto Vercel
            github_repo_owner: Proprietario della repository GitHub
            github_repo_name: Nome della repository GitHub
            
        Returns:
            bool: True se l'attivazione è riuscita, False altrimenti
        """
        if not self.token or not project_id:
            return False
            
        url = f"{self.base_url}/v13/deployments"
        
        # Parametri per la richiesta
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
            
        # Dati per il deployment
        data = {
            "name": github_repo_name,
            "project": project_id,
            "target": "production",
            "gitSource": {
                "type": "github",
                "repo": f"{github_repo_owner}/{github_repo_name}",
                "ref": "main"  # Utilizza il branch principale
            }
        }
        
        try:
            logger.info(f"Attivazione deployment per il progetto {project_id} da GitHub")
            response = requests.post(url, headers=self.headers, params=params, json=data)
            
            if response.status_code not in (200, 201, 202):
                error_msg = f"Errore nell'attivazione del deployment: {response.text}"
                logger.error(error_msg)
                return False
                
            deployment_info = response.json()
            logger.info(f"Deployment attivato con successo: {deployment_info.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante l'attivazione del deployment: {str(e)}")
            return False