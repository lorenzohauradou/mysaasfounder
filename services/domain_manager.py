import logging
import requests
import time

logger = logging.getLogger("SaaSAutomation.DomainManager")

class DomainManager:
    """
    Gestisce l'acquisto e la configurazione dei domini
    """
    
    def __init__(self, config):
        self.provider = config["provider"]
        self.api_key = config["api_key"]
        self.api_secret = config["api_secret"]
        
        # Seleziona l'endpoint API in base al provider
        if self.provider.lower() == "godaddy":
            # self.base_url = "https://api.godaddy.com/v1"  # URL di produzione
            self.base_url = "https://api-ote.godaddy.com/v1"  # URL dell'ambiente OTE
            
        elif self.provider.lower() == "namecheap":
            self.base_url = "https://api.namecheap.com/xml.response"
        else:
            raise ValueError(f"Provider di domini non supportato: {self.provider}")
        
        logger.info(f"DomainManager inizializzato con provider: {self.provider}")
        
    def purchase_domain(self, domain_name):
        """
        Acquista un dominio tramite l'API del provider
        
        Args:
            domain_name: Il nome di dominio da acquistare
            
        Returns:
            dict: Informazioni sul dominio acquistato
        """
        logger.info(f"Tentativo di acquisto dominio: {domain_name}")
        
        # Implementazione specifica per GoDaddy
        if self.provider.lower() == "godaddy":
            headers = {
                "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
                "Content-Type": "application/json"
            }
            
            # Verifica disponibilità
            check_url = f"{self.base_url}/domains/available?domain={domain_name}"
            response = requests.get(check_url, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"Errore nella verifica disponibilità dominio: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            availability = response.json()
            if not availability.get("available", False):
                error_msg = f"Il dominio {domain_name} non è disponibile"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Acquista il dominio
            purchase_url = f"{self.base_url}/domains/purchase"
            purchase_data = {
                "domain": domain_name,
                "consent": {
                    "agreementKeys": ["DNRA"],
                    "agreedBy": "customer",
                    "agreedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                },
                "period": 1,  # 1 anno
                "renewAuto": True,
                "contactAdmin": {
                    # Dati di contatto
                },
                "contactRegistrant": {
                    # Dati di contatto
                },
                "contactTech": {
                    # Dati di contatto
                },
                "contactBilling": {
                    # Dati di contatto
                }
            }
            
            response = requests.post(purchase_url, headers=headers, json=purchase_data)
            
            if response.status_code != 200:
                error_msg = f"Errore nell'acquisto del dominio: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            logger.info(f"Dominio {domain_name} acquistato con successo")
            return response.json()
        
        # Implementazione per Namecheap (simulata)
        else:
            # Simulazione per Namecheap
            logger.info(f"Simulazione acquisto dominio {domain_name} con Namecheap")
            return {"domain": domain_name, "purchase_date": time.strftime("%Y-%m-%d")}
            
    def configure_dns(self, domain_name, records=None):
        """
        Configura i record DNS per il dominio
        
        Args:
            domain_name: Il nome di dominio da configurare
            records: Lista di record DNS da aggiungere (opzionale)
            
        Returns:
            dict: Risultato della configurazione DNS
        """
        logger.info(f"Configurazione DNS per dominio: {domain_name}")
        
        # Record DNS predefiniti se non specificati
        if records is None:
            records = [
                {
                    "type": "A",
                    "name": "@",
                    "data": "76.76.21.21",  # IP di Vercel
                    "ttl": 3600
                },
                {
                    "type": "CNAME",
                    "name": "www",
                    "data": f"@",
                    "ttl": 3600
                }
            ]
        
        # Implementazione specifica per GoDaddy
        if self.provider.lower() == "godaddy":
            headers = {
                "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
                "Content-Type": "application/json"
            }
            
            dns_url = f"{self.base_url}/domains/{domain_name}/records"
            
            # Aggiungi i record DNS uno alla volta
            for record in records:
                record_type = record["type"]
                record_name = record["name"]
                
                record_url = f"{dns_url}/{record_type}/{record_name}"
                response = requests.put(
                    record_url, 
                    headers=headers, 
                    json=[{
                        "data": record["data"],
                        "ttl": record["ttl"]
                    }]
                )
                
                if response.status_code not in [200, 201, 204]:
                    error_msg = f"Errore nella configurazione DNS per {record_type} {record_name}: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            
            logger.info(f"DNS configurato con successo per {domain_name}")
            return {"domain": domain_name, "records": records}
        
        # Simulazione per altri provider
        else:
            logger.info(f"Simulazione configurazione DNS per {domain_name}")
            return {"domain": domain_name, "records": records}

    def get_vercel_dns_records(self, deployment_info):
        """
        Ottiene i record DNS corretti in base al deployment Vercel
        
        Args:
            deployment_info: Informazioni sul deployment Vercel
            
        Returns:
            list: Lista di record DNS da configurare
        """
        logger.info("Preparazione record DNS basati su dati Vercel")
        
        # Record base per Vercel
        records = [
            {
                "type": "A",
                "name": "@",
                "data": "76.76.21.21",  # IP standard di Vercel
                "ttl": 3600
            },
            {
                "type": "CNAME",
                "name": "www",
                "data": "@",
                "ttl": 3600
            }
        ]
        
        # Se il deployment contiene informazioni DNS specifiche
        if deployment_info and "dns" in deployment_info:
            vercel_records = deployment_info["dns"]
            for record in vercel_records:
                # Aggiungi o sostituisci i record in base ai dati Vercel
                records.append({
                    "type": record["type"],
                    "name": record["name"],
                    "data": record["value"],
                    "ttl": 3600
                })
        
        return records