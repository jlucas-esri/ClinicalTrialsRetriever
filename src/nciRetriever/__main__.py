import requests
import logging
from urllib.parse import urljoin
import json

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

def main():

    baseUrl = r'https://clinicaltrialsapi.cancer.gov/api/v2/'
    with open('./nciRetriever/secrets/key.txt') as f:
        apiKey = f.read()

    headers = {
        'X-API-KEY': apiKey,
        'Content-Type': 'application/json'
    }
    trialEndpoint = urljoin(baseUrl, 'trials')
    logger.debug(trialEndpoint)

    payload = {
        
    }


    trialsResponse = requests.get(trialEndpoint, headers=headers, params=payload)
    trialsResponse.raise_for_status()
    trialJson = trialsResponse.json()
    # logger.debug(trialsResponse.json())
    with open('response.json', 'w') as f:
        json.dump(trialJson, f)

if __name__ == '__main__':
    main()