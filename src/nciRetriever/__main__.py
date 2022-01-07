import requests
from nciRetriever.updateFC import updateFC
from datetime import date
import pandas as pd
import logging
from urllib.parse import urljoin
import json
import time
import sys
import os

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

    start = time.perf_counter()
    today = date.today()

    createdTrialCsv = False
    createdSiteCsv = False
    createdEligibilityCsv = False

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
                                        'startDate',
                                        'maxAgeInYears',
                                        'minAgeInYears',
                                        'gender',
                                        'acceptsHealthyVolunteers'])

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
        eligibilityDf = pd.DataFrame(columns=['protocolId',
                                              'inclusionIndicator',
                                              'description'])
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
            if 'max_age_in_years' in trial['eligibility']['structured'].keys():
                trialDict.update({'maxAgeInYears': int(trial['eligibility']['structured']['max_age_in_years'])})
            if 'min_age_in_years' in trial['eligibility']['structured'].keys():
                trialDict.update({'minAgeInYears': int(trial['eligibility']['structured']['min_age_in_years'])})
            if 'gender' in trial['eligibility']['structured'].keys():
                trialDict.update({'gender': trial['eligibility']['structured']['gender']})
            if 'accepts_healthy_volunteers' in trial['eligibility']['structured'].keys():
                trialDict.update({'acceptsHealthyVolunteers': trial['eligibility']['structured']['accepts_healthy_volunteers']})
            trialDf = pd.DataFrame.from_records([trialDict])
            trialsDf = pd.concat([trialsDf, trialDf], verify_integrity=True, ignore_index=True)

            if trial['eligibility']['unstructured'] is not None:
                for condition in trial['eligibility']['unstructured']:
                    eligibilityDict = {
                        'protocolId': trial['protocol_id'],
                        'inclusionIndicator': condition['inclusion_indicator'],
                        'description': condition['description']
                    }
                    conditionDf = pd.DataFrame.from_records([eligibilityDict])
                    eligibilityDf = pd.concat([eligibilityDf, conditionDf], verify_integrity=True, ignore_index=True)

            if trial['sites'] is not None:

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
            if os.path.isfile(f'nciSites{today}.csv'):
                os.remove(f'nciSites{today}.csv')
            sitesDf.to_csv(f'nciSites{today}.csv', index=False)
            createdSiteCsv = True
        else:
            sitesDf.to_csv(f'nciSites{today}.csv', index=False, mode='a', header=False)
        
        if not createdTrialCsv:
            if os.path.isfile(f'nciTrials{today}.csv'):
                os.remove(f'nciTrials{today}.csv')
            trialsDf.to_csv(f'nciTrials{today}.csv', index=False)
            createdTrialCsv = True
        else:
            trialsDf.to_csv(f'nciTrials{today}.csv', index=False, mode='a', header=False)

        if not createdEligibilityCsv:
            if os.path.isfile(f'nciEligibility{today}.csv'):
                os.remove(f'nciEligibility{today}.csv')
            eligibilityDf.to_csv(f'nciEligibility{today}.csv', index=False)
            createdEligibilityCsv = True
        else:
            eligibilityDf.to_csv(f'nciEligibility{today}.csv', index=False, mode='a', header=False)

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
    # main()
    updateFC()