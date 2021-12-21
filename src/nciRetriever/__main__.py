import requests
from datetime import date
import pandas as pd
import logging
from urllib.parse import urljoin
import json
import time
import sys

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
    # finalFileNumTrials = totalNumTrials % 50
# 
    # totalTrialsData = []
# 
    # start = time.perf_counter()
# 
    # for trialNum in range(0, totalNumTrials, 50):
        # logger.debug(trialNum)
        # payload = {
            # 'size': 50,
            # 'from': trialNum
        # }
# 
        # response = requests.get(trialEndpoint, headers=headers, params=payload)
        # response.raise_for_status()
        # sectionJson = response.json()
        # totalTrialsData.extend(sectionJson['data'])
# 
        # if trialNum % 1000 == 0 and trialNum != 0:
            # with open(f'{trialNum-999}-{trialNum}Trials.json', 'w') as f:
                # json.dump(totalTrialsData, f)
            # totalTrialsData = []
        # time.sleep(4)
# 
    # with open(f'{round(totalNumTrials, -3)}-{trialNum}Trials.json', 'w') as f:
        # json.dump(totalTrialsData, f)
# 
    # end = time.perf_counter()
    # logger.debug(f'All trials queried in {end-start: .2f} seconds')
# 

    start = time.perf_counter()

    createdTrialCsv = False
    createdSiteCsv = False

    for trialNumFrom in range(0, totalNumTrials, 50):
        sectionStart = time.perf_counter()
        trialsDf = pd.DataFrame(columns=['protocolId', 
                                        'NciId', 
                                        'NctId', 
                                        'detailDesc', 
                                        'officialTitle', 
                                        'phase', 
                                        'leadOrg', 
                                        'amendmentDate', 
                                        'primaryPurpose', 
                                        'activeSitesCount', 
                                        'currentTrialStatus',
                                        'startDate'])

        sitesDf = pd.DataFrame(columns=['protocolId',
                                        'orgStateOrProvince',
                                        'contactName',
                                        'contactPhone',
                                        'recruitmentStatusDate',
                                        'orgAddressLine1',
                                        'orgAddressLine2',
                                        'orgVa',
                                        'orgTty',
                                        'orgFamily',
                                        'orgPostalCode',
                                        'contactEmail',
                                        'recruitmentStatus',
                                        'orgCity',
                                        'orgEmail',
                                        'orgCounty',
                                        'orgFax',
                                        'orgPhone',
                                        'orgName',
                                        'lat',
                                        'long'])
        payload = {
            'size': 50,
            'from': trialNumFrom
        }
        
        response = requests.get(trialEndpoint, headers=headers, params=payload)
        response.raise_for_status()
        sectionJson = response.json()
        
        for trial in sectionJson['data']:
            trialDict = {'protocolId': trial['protocol_id'], 
                                    'NciId': trial['nci_id'], 
                                    'NctId': trial['nct_id'], 
                                    'detailDesc': trial['detail_description'], 
                                    'officialTitle': trial['official_title'], 
                                    'phase': trial['phase'], 
                                    'leadOrg': trial['lead_org'], 
                                    'amendmentDate': trial['amendment_date'], 
                                    'primaryPurpose': trial['primary_purpose'], 
                                    'currentTrialStatus': trial['current_trial_status'],
                                    'startDate': trial['start_date']}
            if 'active_sites_count' in trial.keys():
                trialDict.update({'activeSitesCount': trial['active_sites_count']})
            trialDf = pd.DataFrame.from_records([trialDict])
            trialsDf = pd.concat([trialsDf, trialDf], verify_integrity=True, ignore_index=True)

            if trial['sites'] is None:
                continue 

            for site in trial['sites']:
                siteDict = {'protocolId': trial['protocol_id'],
                                    'orgStateOrProvince': site['org_state_or_province'],
                                    'contactName': site['contact_name'],
                                    'contactPhone': site['contact_phone'],
                                    'recruitmentStatusDate': site['recruitment_status_date'],
                                    'orgAddressLine1': site['org_address_line_1'],
                                    'orgAddressLine2': site['org_address_line_2'],
                                    'orgVa': site['org_va'],
                                    'orgTty': site['org_tty'],
                                    'orgFamily': site['org_family'],
                                    'orgPostalCode': site['org_postal_code'],
                                    'contactEmail': site['contact_email'],
                                    'recruitmentStatus': site['recruitment_status'],
                                    'orgCity': site['org_city'],
                                    'orgEmail': site['org_email'],
                                    'orgCountry': site['org_country'],
                                    'orgFax': site['org_fax'],
                                    'orgPhone': site['org_phone'],
                                    'orgName': site['org_name'],
                                    'lat': None,
                                    'long': None}
                if 'org_coordinates' in site.keys():
                    siteDict['lat'] = site['org_coordinates']['lat']
                    siteDict['long'] = site['org_coordinates']['lon']
                siteDf = pd.DataFrame.from_records([siteDict])
                
                sitesDf = pd.concat([sitesDf, siteDf], ignore_index=True, verify_integrity=True)
        if not createdSiteCsv:
            sitesDf.to_csv(f'nciSites{date.today()}.csv', index=False)
            createdSiteCsv = True
        else:
            sitesDf.to_csv(f'nciSites{date.today()}.csv', index=False, mode='a', header=False)
        
        if not createdTrialCsv:
            trialsDf.to_csv(f'nciTrials{date.today()}.csv', index=False)
            createdTrialCsv = True
        else:
            trialsDf.to_csv(f'nciTrials{date.today()}.csv', index=False, mode='a', header=False)
        sectionElapsed = time.perf_counter()-sectionStart

        logger.debug(f'Trials {trialNumFrom}-{trialNumFrom+50} retrieved in {sectionElapsed: .2f}s')

        if sectionElapsed < 3:
            time.sleep(3-sectionElapsed)
            
            
    elapsed = time.perf_counter() - start
    logger.debug(f'All data retrieved and saved in {elapsed: .2f}s')
    logger.debug(sys.getsizeof(trialsDf))
    logger.debug(sys.getsizeof(sitesDf))

    # logger.debug(trialsResponse.json())
    # with open('response.json', 'w') as f:
    #     json.dump(trialJson, f)

if __name__ == '__main__':
    main()