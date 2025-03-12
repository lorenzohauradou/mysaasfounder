import os
from dotenv import load_dotenv

def load_config():
    """
    Carica le configurazioni dalle variabili d'ambiente
    """
    load_dotenv()
    
    # variabili d'ambiente obbligatorie
    required_vars = [
        "DOMAIN_PROVIDER_API_KEY", 
        "DOMAIN_PROVIDER_API_SECRET",
        "EMAIL_PROVIDER_API_KEY",
        "GITHUB_TOKEN",
        "VERCEL_TOKEN",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Variabili d'ambiente mancanti: {', '.join(missing_vars)}")
    
    return {
        "domain": {
            "provider": os.getenv("DOMAIN_PROVIDER", "godaddy"),
            "api_key": os.getenv("DOMAIN_PROVIDER_API_KEY"),
            "api_secret": os.getenv("DOMAIN_PROVIDER_API_SECRET")
        },
        "email": {
            "provider": os.getenv("EMAIL_PROVIDER", "sendgrid"),
            "api_key": os.getenv("EMAIL_PROVIDER_API_KEY")
        },
        "github": {
            "token": os.getenv("GITHUB_TOKEN")
        },
        "vercel": {
            "token": os.getenv("VERCEL_TOKEN")
        },
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY")
        },
        "claude": {
            "api_key": os.getenv("CLAUDE_API_KEY")
        }
    }