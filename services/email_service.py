import logging
import requests
import time

logger = logging.getLogger("SaaSAutomation.EmailService")

class EmailService:
    """
    Gestisce la configurazione dei servizi email SMTP
    """
    
    def __init__(self, config):
        self.provider = config["provider"]
        self.api_key = config["api_key"]
        
        # Seleziona l'endpoint API in base al provider
        if self.provider.lower() == "sendgrid":
            self.base_url = "https://api.sendgrid.com/v3"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        elif self.provider.lower() == "mailgun":
            self.base_url = "https://api.mailgun.net/v3"
            self.auth = ("api", self.api_key)
        else:
            raise ValueError(f"Provider email non supportato: {self.provider}")
        
        logger.info(f"EmailService inizializzato con provider: {self.provider}")
    
    def setup_smtp(self, domain, contact_email):
        """
        Configura il servizio SMTP per il dominio
        
        Args:
            domain: Il nome di dominio
            contact_email: Email di contatto
            
        Returns:
            dict: Configurazione SMTP
        """
        logger.info(f"Configurazione SMTP per dominio: {domain}")
        
        # Modalità di simulazione per test
        if self.provider.lower() == "mockprovider" or domain.endswith("test.com"):
            logger.info(f"Simulazione configurazione email per {domain}")
            return {
                "domain": domain,
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "smtp_username": "simulated_user",
                "smtp_password": "simulated_password",
                "dns_records": []
            }
        
        if self.provider.lower() == "sendgrid":
            # Aggiungi dominio a SendGrid
            domain_url = f"{self.base_url}/whitelabel/domains"
            domain_data = {
                "domain": domain,
                "subdomain": "mail",
                "default": True,
                "automatic_security": True
            }
            
            response = requests.post(domain_url, headers=self.headers, json=domain_data)
            
            if response.status_code not in [201, 200]:
                error_msg = f"Errore nella configurazione del dominio SendGrid: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            domain_id = response.json()["id"]
            
            # Ottieni i record DNS da configurare
            dns_url = f"{self.base_url}/whitelabel/domains/{domain_id}"
            dns_response = requests.get(dns_url, headers=self.headers)
            
            if dns_response.status_code != 200:
                error_msg = f"Errore nell'ottenere i record DNS: {dns_response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            dns_records = dns_response.json()["dns"]
            
            # Configura API Key dedicata
            api_key_url = f"{self.base_url}/api_keys"
            api_key_data = {
                "name": f"SMTP Key for {domain}",
                "scopes": ["mail.send"]
            }
            
            api_key_response = requests.post(api_key_url, headers=self.headers, json=api_key_data)
            
            if api_key_response.status_code != 201:
                error_msg = f"Errore nella creazione della API key: {api_key_response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            smtp_key = api_key_response.json()["api_key"]
            
            logger.info(f"SMTP configurato con successo per {domain}")
            
            return {
                "domain": domain,
                "smtp_server": "smtp.sendgrid.net",
                "smtp_port": 587,
                "smtp_username": "apikey",
                "smtp_password": smtp_key,
                "dns_records": dns_records
            }
            
        elif self.provider.lower() == "mailgun":
            # Aggiungi dominio a Mailgun
            domain_url = f"{self.base_url}/domains"
            domain_data = {
                "name": domain,
                "smtp_password": self._generate_password()
            }
            
            response = requests.post(domain_url, auth=self.auth, data=domain_data)
            
            if response.status_code != 200:
                error_msg = f"Errore nella configurazione del dominio Mailgun: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            domain_info = response.json()["domain"]
            receiving_records = domain_info["receiving_dns_records"]
            sending_records = domain_info["sending_dns_records"]
            
            logger.info(f"SMTP configurato con successo per {domain}")
            
            return {
                "domain": domain,
                "smtp_server": "smtp.mailgun.org",
                "smtp_port": 587,
                "smtp_username": f"postmaster@{domain}",
                "smtp_password": domain_data["smtp_password"],
                "dns_records": receiving_records + sending_records
            }
    
    def send_test_email(self, to_email):
        """
        Invia un'email di test per verificare la configurazione
        
        Args:
            to_email: Indirizzo email destinatario
            
        Returns:
            bool: True se l'invio è riuscito
        """
        logger.info(f"Invio email di test a: {to_email}")
        
        if self.provider.lower() == "sendgrid":
            url = f"{self.base_url}/mail/send"
            data = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}]
                    }
                ],
                "from": {"email": "test@example.com", "name": "SaaS Automation"},
                "subject": "Test Email - SaaS Automation",
                "content": [
                    {
                        "type": "text/plain",
                        "value": "Questa è un'email di test dal sistema di automazione SaaS."
                    },
                    {
                        "type": "text/html",
                        "value": "<p>Questa è un'email di test dal sistema di automazione SaaS.</p>"
                    }
                ]
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code not in [200, 202]:
                error_msg = f"Errore nell'invio dell'email di test: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info("Email di test inviata con successo")
            return True
            
        elif self.provider.lower() == "mailgun":
            url = f"{self.base_url}/sandbox.mailgun.org/messages"
            data = {
                "from": "SaaS Automation <test@sandbox.mailgun.org>",
                "to": to_email,
                "subject": "Test Email - SaaS Automation",
                "text": "Questa è un'email di test dal sistema di automazione SaaS.",
                "html": "<p>Questa è un'email di test dal sistema di automazione SaaS.</p>"
            }
            
            response = requests.post(url, auth=self.auth, data=data)
            
            if response.status_code != 200:
                error_msg = f"Errore nell'invio dell'email di test: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info("Email di test inviata con successo")
            return True
    
    def _generate_password(self, length=16):
        """
        Genera una password casuale sicura
        
        Args:
            length: Lunghezza della password
            
        Returns:
            str: Password generata
        """
        import random
        import string
        
        characters = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        return ''.join(random.choice(characters) for _ in range(length))