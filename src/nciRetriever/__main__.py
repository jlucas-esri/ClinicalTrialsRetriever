import requests
import logging
from urllib.parse import urljoin
import json
import time

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

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

    trialsResponse = requests.get(trialEndpoint, headers=headers)
    trialsResponse.raise_for_status()
    trialJson = trialsResponse.json()
    totalNumTrials = trialJson['total']
    finalFileNumTrials = totalNumTrials % 50

    totalTrialsData = []

    start = time.perf_counter()

    for trialNum in range(0, totalNumTrials, 50):
        logger.debug(trialNum)
        payload = {
            'size': 50,
            'from': trialNum
        }

        response = requests.get(trialEndpoint, headers=headers, params=payload)
        response.raise_for_status()
        sectionJson = response.json()
        totalTrialsData.extend(sectionJson['data'])

        if trialNum % 1000 == 0 and trialNum != 0:
            with open(f'{trialNum-999}-{trialNum}Trials.json', 'w') as f:
                json.dump(totalTrialsData, f)
            totalTrialsData = []
        time.sleep(4)

    with open(f'{round(totalNumTrials, -3)}-{trialNum}Trials.json', 'w') as f:
        json.dump(totalTrialsData, f)

    end = time.perf_counter()
    logger.debug(f'All trials queried in {end-start: .2f} seconds')


    # logger.debug(trialsResponse.json())
    # with open('response.json', 'w') as f:
    #     json.dump(trialJson, f)

if __name__ == '__main__':
    main()