import logging
import requests

logger = logging.getLogger("SaaSAutomation.GitHubIntegration")

class GitHubIntegration:
    """
    Gestisce l'integrazione con GitHub per la creazione e configurazione di repository
    """
    
    def __init__(self, config):
        self.token = config["token"]
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        logger.info("GitHubIntegration inizializzato")
    
    def create_repository(self, name, refined_description=None, private=False):
        """
        Crea una nuova repository su GitHub
        
        Args:
            name: Nome della repository
            description: Descrizione della repository (opzionale)
            private: Se la repository deve essere privata (default: False)
            
        Returns:
            dict: Informazioni sulla repository creata
        """
        logger.info(f"Creazione repository GitHub: {name}")
        
        url = f"{self.base_url}/user/repos"
        data = {
            "name": name,
            "description": refined_description or f"{name}",
            "private": private,
            "auto_init": False,  # Cambiato da True a False
            "gitignore_template": "Node"
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code != 201:
            error_msg = f"Errore nella creazione della repository: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        repo_info = response.json()
        logger.info(f"Repository creata con successo: {repo_info['full_name']}")
        
        return {
            "id": repo_info["id"],
            "name": repo_info["name"],
            "full_name": repo_info["full_name"],
            "html_url": repo_info["html_url"],
            "clone_url": repo_info["clone_url"]
        }
    
    def configure_webhook(self, repo_name, webhook_url=None):
        """
        Configura un webhook per la repository
        
        Args:
            repo_name: Nome della repository
            webhook_url: URL del webhook (opzionale)
            
        Returns:
            dict: Informazioni sul webhook creato
        """
        logger.info(f"Configurazione webhook per repository: {repo_name}")
        
        # Se non viene fornito un URL webhook, utilizziamo l'URL di Vercel
        if webhook_url is None:
            webhook_url = "https://api.vercel.com/v1/integrations/github/webhook"
        
        url = f"{self.base_url}/repos/{self.get_username()}/{repo_name}/hooks"
        data = {
            "name": "web",
            "active": True,
            "events": ["push", "pull_request"],
            "config": {
                "url": webhook_url,
                "content_type": "json"
            }
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code != 201:
            error_msg = f"Errore nella configurazione del webhook: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        webhook_info = response.json()
        logger.info(f"Webhook configurato con successo: {webhook_info['id']}")
        
        return {
            "id": webhook_info["id"],
            "url": webhook_info["config"]["url"]
        }
    
    def get_username(self):
        """
        Ottiene il nome utente dell'account GitHub autenticato
        
        Returns:
            str: Nome utente GitHub
        """
        url = f"{self.base_url}/user"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            error_msg = f"Errore nell'ottenere le informazioni utente: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        return response.json()["login"]
    
    def add_file_to_repository(self, repo_name, file_path, file_content, commit_message=None):
        """
        Aggiunge un file alla repository GitHub
        
        Args:
            repo_name: Nome della repository
            file_path: Percorso del file all'interno della repository
            file_content: Contenuto del file
            commit_message: Messaggio di commit (opzionale)
            
        Returns:
            dict: Risposta dell'API
        """
        logger.info(f"Aggiunta file {file_path} al repository {repo_name}")
        
        if commit_message is None:
            commit_message = f"Aggiunta file {file_path}"
        
        # Debug: stampa il percorso completo per capire la struttura
        logger.info(f"Percorso file completo nella repository: {file_path}")
        
        import base64
        
        try:
            # Endpoint per creare o aggiornare un file
            url = f"{self.base_url}/repos/{self.get_username()}/{repo_name}/contents/{file_path}"
            
            # Verifica se il file esiste già
            sha = None
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    sha = response.json()["sha"]
                    logger.info(f"File {file_path} già esistente, verrà aggiornato")
            except Exception:
                # Il file non esiste, si procede con la creazione
                pass
            
            # Codifica il contenuto in base64
            content_bytes = file_content.encode("utf-8")
            content_base64 = base64.b64encode(content_bytes).decode("utf-8")
            
            # Crea il payload
            data = {
                "message": commit_message,
                "content": content_base64
            }
            
            # Aggiungi lo sha se il file esiste già
            if sha:
                data["sha"] = sha
            
            # Invia la richiesta
            response = requests.put(url, headers=self.headers, json=data)
            
            if response.status_code not in [200, 201]:
                error_msg = f"Errore nell'aggiunta del file: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            file_info = response.json()
            logger.info(f"File {file_path} aggiunto con successo")
            
            return {
                "path": file_path,
                "sha": file_info["content"]["sha"],
                "url": file_info["content"]["html_url"]
            }
        except Exception as e:
            error_msg = f"Errore nell'aggiunta del file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_repository(self, repo_name):
        """
        Ottiene informazioni su una repository
        
        Args:
            repo_name: Nome della repository
            
        Returns:
            dict: Informazioni sulla repository o None se non trovata
        """
        url = f"{self.base_url}/repos/{self.get_username()}/{repo_name}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            logger.warning(f"Repository {repo_name} non trovata: {response.text}")
            return None
        
        repo_info = response.json()
        return {
            "id": repo_info["id"],
            "name": repo_info["name"],
            "full_name": repo_info["full_name"],
            "html_url": repo_info["html_url"],
            "clone_url": repo_info["clone_url"]
        }
    