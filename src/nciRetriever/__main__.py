import requests
from typing import List
import re
from nciRetriever.updateFC import updateFC
from nciRetriever.csvToArcgisPro import csvToArcgisPro
from nciRetriever.geocode import geocodeSites
from nciRetriever.createRelationships import createRelationships
from nciRetriever.zipGdb import zip
from nciRetriever.updateItem import update
from datetime import date
import pandas as pd
import logging
from urllib.parse import urljoin
import json
import time
import sys
import os
from pprint import pprint

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

today = date.today()

def createTrialDict(trial: dict) -> dict:
    trialDict = {'nciId': trial['nci_id'], 
                'protocolId': trial['protocol_id'],
                'nctId': trial['nct_id'], 
                'detailDesc': trial['detail_description'], 
                'officialTitle': trial['official_title'], 
                'phase': trial['phase'], 
                'leadOrg': trial['lead_org'], 
                'amendmentDate': trial['amendment_date'], 
                'primaryPurpose': trial['primary_purpose'], 
                'currentTrialStatus': trial['current_trial_status'],
                'startDate': trial['start_date']}
    if 'completion_date' in trial.keys():
        trialDict.update({'completionDate': trial['completion_date']})
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
    if 'study_source' in trial.keys():
        trialDict.update({'studySource': trial['study_source']})
    if 'study_protocol_type' in trial.keys():
        trialDict.update({'studyProtocolType': trial['study_protocol_type']})
    if 'record_verification_date' in trial.keys():
        trialDict.update({'recordVerificationDate': trial['record_verification_date']})
    
    return trialDict

def createSiteDict(trial:dict, site:dict) -> dict:
    siteDict = {'nciId': trial['nci_id'],
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
                        'orgName': site['org_name']
                        }
    # if 'org_coordinates' in site.keys():
    #     siteDict['lat'] = site['org_coordinates']['lat']
    #     siteDict['long'] = site['org_coordinates']['lon']
    
    return siteDict

def createBiomarkersDicts(trial:dict, marker:dict) -> List[dict]:
    parsedBiomarkers = []
    for name in [*marker['synonyms'], marker['name']]:
        biomarkerDict = {
            'nciId': trial['nci_id'],
            'nciThesaurusConceptId': marker['nci_thesaurus_concept_id'],
            'name': name,
            'assayPurpose': marker['assay_purpose']
        }
        if 'eligibility_criterion' in marker.keys():
            biomarkerDict.update({'eligibilityCriterion': marker['eligibility_criterion']})
        if 'inclusion_indicator' in marker.keys():
            biomarkerDict.update({'inclusionIndicator': marker['inclusion_indicator']})

        parsedBiomarkers.append(biomarkerDict)
    return parsedBiomarkers

def createMainBiomarkersDict(trial:dict, marker:dict) -> dict:
    parsedBiomarker = {
        'nciId': trial['nci_id'],
        'nciThesaurusConceptId': marker['nci_thesaurus_concept_id'],
        'name': marker['name'],
        'assayPurpose': marker['assay_purpose'],
    }
    if 'eligibility_criterion' in marker.keys():
        parsedBiomarker.update({'eligibilityCriterion': marker['eligibility_criterion']})
    if 'inclusion_indicator' in marker.keys():
        parsedBiomarker.update({'inclusionIndicator': marker['inclusion_indicator']})
    return parsedBiomarker


def createDiseasesDicts(trial:dict, disease:dict) -> List[dict]:
    parsedDiseases = []
    try:
        names = [disease['name']]
        if 'synonyms' in disease.keys():
            names.extend(disease['synonyms'])
    except KeyError:
        logger.error(f'Invalid key for diseases. Possible keys: {disease.keys()}')
        return parsedDiseases

    for name in names:
        diseaseDict = {
            'inclusionIndicator': disease['inclusion_indicator'],
            'isLeadDisease': disease['is_lead_disease'],
            'name': name,
            'nciThesaurusConceptId': disease['nci_thesaurus_concept_id'],
            'nciId': trial['nci_id']
        }
        parsedDiseases.append(diseaseDict)
    return parsedDiseases

def createMainDiseasesDict(trial:dict, disease:dict) -> dict:
    try:
        return {
            'nciId': trial['nci_id'],
            'name': disease['name'],
            'isLeadDisease': disease['is_lead_disease'],
            'nciThesaurusConceptId': disease['nci_thesaurus_concept_id'],
            'inclusionIndicator': disease['inclusion_indicator']
        }   
    except KeyError:
        logger.error('Invalid key for main diseases. Not adding to list...')
        return {}

def createArmsDict(trial:dict, arm:dict) -> dict:
    parsedArm = re.sub(r'\(.+\)', '', arm['name'])
    parsedArm = re.sub(r'\s+', '_', parsedArm.strip())
    return {
        'nciId': trial['nci_id'],
        'name': arm['name'],
        'nciIdWithName': f'{trial["nci_id"]}_{parsedArm}',
        'description': arm['description'],
        'type': arm['type']
    }

def createInterventionsDicts(trial:dict, arm:dict) -> List[dict]:
    parsedInterventions = []

    parsedArm = re.sub(r'\(.+\)', '', arm['name'])
    parsedArm = re.sub(r'\s+', '_', parsedArm.strip())

    for intervention in arm['interventions']:

        names = intervention['synonyms']
        if 'name' in intervention.keys():
            names.append(intervention['name'])
        elif 'intervention_name' in intervention.keys():
            names.append(intervention['intervention_name'])

        for name in names:
            try:
                interventionDict = {
                    'nciId': trial['nci_id'],
                    'arm': arm['name'],
                    'nciIdWithArm': f'{trial["nci_id"]}_{parsedArm}',
                    'type': intervention['intervention_type'],
                    'inclusionIndicator': intervention['inclusion_indicator'],
                    'name': name,
                    'category': intervention['category'],
                    'nciThesaurusConceptId': intervention['intervention_code'],
                    'description': intervention['intervention_description']
                }
            except KeyError:
                try:
                    interventionDict = {
                        'nciId': trial['nci_id'],
                        'arm': arm['name'],
                        'nciIdWithArm': f'{trial["nci_id"]}_{parsedArm}',
                        'type': intervention['type'],
                        'inclusionIndicator': intervention['inclusion_indicator'],
                        'name': name,
                        'category': intervention['category'],
                        'nciThesaurusConceptId': intervention['nci_thesaurus_concept_id'],
                        'description': intervention['description']
                    }
                except KeyError as e:
                    logger.exception(e)
                    logger.error(f'Invalid intervention keys. Possible keys are: {intervention.keys()}')
                    continue
            parsedInterventions.append(interventionDict)
    return parsedInterventions

def createMainInterventionDicts(trial:dict, arm:dict) -> List[dict]:
    parsedArm = re.sub(r'\(.+\)', '', arm['name'])
    parsedArm = re.sub(r'\s+', '_', parsedArm.strip())

    parsedMainInterventions = []

    for intervention in arm['interventions']:
        try:
            mainInterventionDict = {
                'nciId': trial['nci_id'],
                'arm': arm['name'],
                'nciIdWithArm': f'{trial["nci_id"]}_{parsedArm}',
                'type': intervention['intervention_type'],
                'inclusionIndicator': intervention['inclusion_indicator'],
                'name': intervention['intervention_name'],
                'category': intervention['category'],
                'nciThesaurusConceptId': intervention['intervention_code'],
                'description': intervention['intervention_description']
            }
        except KeyError:
            try:
                mainInterventionDict = {
                    'nciId': trial['nci_id'],
                    'arm': arm['name'],
                    'nciIdWithArm': f'{trial["nci_id"]}_{parsedArm}',
                    'type': intervention['type'],
                    'inclusionIndicator': intervention['inclusion_indicator'],
                    'name': intervention['name'],
                    'category': intervention['category'],
                    'nciThesaurusConceptId': intervention['nci_thesaurus_concept_id'],
                    'description': intervention['description']
                }
            except KeyError:
                logger.error(f'Unexpected intervention keys: {intervention.keys()}. Not inserting...')
                continue

        parsedMainInterventions.append(mainInterventionDict)
    return parsedMainInterventions


def retrieveToCsv():

    baseUrl = r'https://clinicaltrialsapi.cancer.gov/api/v2/'
    with open('./nciRetriever/secrets/key.txt') as f:
        apiKey = f.read()

    headers = {
        'X-API-KEY': apiKey,
        'Content-Type': 'application/json'
    }
    trialEndpoint = urljoin(baseUrl, 'trials')
    logger.debug(trialEndpoint)

    #sending initial request to get the total number of trials
    trialsResponse = requests.get(trialEndpoint, headers=headers, params={'trial_status': 'OPEN'})
    trialsResponse.raise_for_status()
    trialJson = trialsResponse.json()
    totalNumTrials = trialJson['total']
    logger.debug(f'Total number of trials: {totalNumTrials}')

    start = time.perf_counter()

    createdTrialCsv = False
    createdSiteCsv = False
    createdEligibilityCsv = False
    createdBiomarkerCsv = False
    createdMainBiomarkerCsv = False
    createdDiseaseCsv = False
    createdMainDiseaseCsv = False
    createdArmsCsv = False
    createdInterventionCsv = False
    createdMainInterventionCsv = False

    for trialNumFrom in range(0, totalNumTrials, 50):
        sectionStart = time.perf_counter()
        
        #creating the dataframes again after every 50 trials to avoid using too much memory
        trialsDf = pd.DataFrame(columns=['protocolId', 
                                        'nciId', 
                                        'nctId', 
                                        'detailDesc', 
                                        'officialTitle', 
                                        'phase', 
                                        'leadOrg', 
                                        'amendmentDate', 
                                        'primaryPurpose', 
                                        'activeSitesCount', 
                                        'currentTrialStatus',
                                        'startDate',
                                        'completionDate',
                                        'maxAgeInYears',
                                        'minAgeInYears',
                                        'gender',
                                        'acceptsHealthyVolunteers',
                                        'studySource',
                                        'studyProtocolType',
                                        'recordVerificationDate'])

        sitesDf = pd.DataFrame(columns=['nciId',
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
                                        'orgName'])
        eligibilityDf = pd.DataFrame(columns=['nciId',
                                              'inclusionIndicator',
                                              'description'])

        biomarkersDf = pd.DataFrame(columns=[
            'nciId',
            'eligibilityCriterion',
            'inclusionIndicator',
            'nciThesaurusConceptId',
            'name',
            'assayPurpose'
        ])

        mainBiomarkersDf = pd.DataFrame(columns=[
            'nciId',
            'eligibilityCriterion',
            'inclusionIndicator',
            'nciThesaurusConceptId',
            'name',
            'assayPurpose'
        ])

        diseasesDf = pd.DataFrame(columns=[
            'nciId',
            'inclusionIndicator',
            'isLeadDisease',
            'nciThesaurusConceptId',
            'name'
        ])

        mainDiseasesDf = pd.DataFrame(columns=[
            'nciId',
            'inclusionIndicator',
            'isLeadDisease',
            'nciThesaurusConceptId',
            'name'
        ])

        armsDf = pd.DataFrame(columns=[
            'nciId',
            'name',
            'nciIdWithName',
            'description',
            'type'
        ])

        interventionsDf = pd.DataFrame(columns=[
            'nciId',
            'arm',
            'nciIdWithArm',
            'type',
            'inclusionIndicator',
            'name',
            'category',
            'nciThesaurusConceptId',
            'description'
        ])

        mainInterventionsDf = pd.DataFrame(columns=[
            'nciId',
            'arm',
            'nciIdWithArm',
            'type',
            'inclusionIndicator',
            'name',
            'category',
            'nciThesaurusConceptId',
            'description'
        ])

        payload = {
            'size': 50,
            'trial_status': 'OPEN',
            'from': trialNumFrom
        }
        
        response = requests.get(trialEndpoint, headers=headers, params=payload)
        response.raise_for_status()
        sectionJson = response.json()
        
        trials = []
        for trial in sectionJson['data']:
            trials.append(createTrialDict(trial))


            if trial['eligibility']['unstructured'] is not None:
                #parsing the unstructured eligibility information from the trial
                eligibilityInfo = []
                for condition in trial['eligibility']['unstructured']:
                    eligibilityInfo.append({
                        'nciId': trial['nci_id'],
                        'inclusionIndicator': condition['inclusion_indicator'],
                        'description': condition['description']
                    })
                conditionDf = pd.DataFrame.from_records(eligibilityInfo)
                eligibilityDf = pd.concat([eligibilityDf, conditionDf], verify_integrity=True, ignore_index=True)

            if trial['sites'] is not None:
                #parsing the sites associated with the trial
                sites = []
                for site in trial['sites']:
                    sites.append(createSiteDict(trial, site))
                siteDf = pd.DataFrame.from_records(sites)
                sitesDf = pd.concat([sitesDf, siteDf], ignore_index=True, verify_integrity=True)
            
            if trial['biomarkers'] is not None:
                #parsing the biomarkers associated with the trial
                biomarkers = []
                mainBiomarkers = []
                for biomarker in trial['biomarkers']:
                    biomarkers.extend(createBiomarkersDicts(trial, biomarker))
                    mainBiomarkers.append(createMainBiomarkersDict(trial, biomarker))
                biomarkerDf = pd.DataFrame.from_records(biomarkers)
                biomarkersDf = pd.concat([biomarkersDf, biomarkerDf], ignore_index=True, verify_integrity=True)
                mainBiomarkerDf = pd.DataFrame.from_records(mainBiomarkers)
                mainBiomarkersDf = pd.concat([mainBiomarkersDf, mainBiomarkerDf], ignore_index=True, verify_integrity=True)
                
            if trial['diseases'] is not None:
                diseases = []
                mainDiseases = []
                for disease in trial['diseases']:
                    diseases.extend(createDiseasesDicts(trial, disease))
                    mainDiseases.append(createMainDiseasesDict(trial, disease))
                diseaseDf = pd.DataFrame.from_records(diseases)
                diseasesDf = pd.concat([diseasesDf, diseaseDf], ignore_index=True, verify_integrity=True)

                mainDiseaseDf = pd.DataFrame.from_records(mainDiseases)
                mainDiseasesDf = pd.concat([mainDiseasesDf, mainDiseaseDf], ignore_index=True, verify_integrity=True)

            if trial['arms'] is not None:
                arms = []
                interventions = []
                mainInterventions = []
                for arm in trial['arms']:
                    arms.append(createArmsDict(trial, arm))
                    interventions.extend(createInterventionsDicts(trial, arm))
                    mainInterventions.extend(createMainInterventionDicts(trial, arm))
                armDf = pd.DataFrame.from_records(arms)
                armsDf = pd.concat([armsDf, armDf], ignore_index=True, verify_integrity=True)
                interventionDf = pd.DataFrame.from_records(interventions)
                interventionsDf = pd.concat([interventionsDf, interventionDf], ignore_index=True, verify_integrity=True)
                mainInterventionDf = pd.DataFrame.from_records(mainInterventions)
                mainInterventionsDf = pd.concat([mainInterventionsDf, mainInterventionDf], ignore_index=True, verify_integrity=True)

        trialDf = pd.DataFrame.from_records(trials)
        trialsDf = pd.concat([trialsDf, trialDf], verify_integrity=True, ignore_index=True)

        #creating and appending the data to csv
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
        
        if not createdBiomarkerCsv:
            if os.path.isfile(f'nciBiomarkers{today}.csv'):
                os.remove(f'nciBiomarkers{today}.csv')
            biomarkersDf.to_csv(f'nciBiomarkers{today}.csv', index=False)
            createdBiomarkerCsv = True
        else:
            biomarkersDf.to_csv(f'nciBiomarkers{today}.csv', index=False, mode='a', header=False)

        if not createdMainBiomarkerCsv:
            if os.path.isfile(f'nciMainBiomarkers{today}.csv'):
                os.remove(f'nciMainBiomarkers{today}.csv')
            mainBiomarkersDf.to_csv(f'nciMainBiomarkers{today}.csv', index=False)
            createdMainBiomarkerCsv = True
        else:
            mainBiomarkersDf.to_csv(f'nciMainBiomarkers{today}.csv', index=False, mode='a', header=False)

        if not createdDiseaseCsv:
            if os.path.isfile(f'nciDiseases{today}.csv'):
                os.remove(f'nciDiseases{today}.csv')
            diseasesDf.to_csv(f'nciDiseases{today}.csv', index=False)
            createdDiseaseCsv = True
        else:
            diseasesDf.to_csv(f'nciDiseases{today}.csv', index=False, mode='a', header=False)

        if not createdMainDiseaseCsv:
            if os.path.isfile(f'nciMainDiseases{today}.csv'):
                os.remove(f'nciMainDiseases{today}.csv')
            mainDiseasesDf.to_csv(f'nciMainDiseases{today}.csv', index=False)
            createdMainDiseaseCsv = True
        else:
            mainDiseasesDf.to_csv(f'nciMainDiseases{today}.csv', index=False, mode='a', header=False)

        if not createdArmsCsv:
            if os.path.isfile(f'nciArms{today}.csv'):
                os.remove(f'nciArms{today}.csv')
            armsDf.to_csv(f'nciArms{today}.csv', index=False)
            createdArmsCsv = True
        else:
            armsDf.to_csv(f'nciArms{today}.csv', index=False, mode='a', header=False)

        if not createdInterventionCsv:
            if os.path.isfile(f'nciInterventions{today}.csv'):
                os.remove(f'nciInterventions{today}.csv')
            interventionsDf.to_csv(f'nciInterventions{today}.csv', index=False)
            createdInterventionCsv = True
        else:
            interventionsDf.to_csv(f'nciInterventions{today}.csv', index=False, mode='a', header=False)

        if not createdMainInterventionCsv:
            if os.path.isfile(f'nciMainInterventions{today}.csv'):
                os.remove(f'nciMainInterventions{today}.csv')
            mainInterventionsDf.to_csv(f'nciMainInterventions{today}.csv', index=False)
            createdMainInterventionCsv = True
        else:
            mainInterventionsDf.to_csv(f'nciMainInterventions{today}.csv', index=False, mode='a', header=False)

        sectionElapsed = time.perf_counter()-sectionStart

        logger.debug(f'Trials {trialNumFrom}-{trialNumFrom+50} retrieved in {sectionElapsed: .2f}s')


        #ensuring that a request isn't sent less than three seconds after the last one. This avoids rate limiting
        if sectionElapsed < 3:
            time.sleep(3-sectionElapsed)
            
            
    elapsed = time.perf_counter() - start
    logger.debug(f'All {totalNumTrials} trials retrieved and saved in {elapsed: .2f}s')
    # logger.debug(sys.getsizeof(trialsDf))
    # logger.debug(sys.getsizeof(sitesDf))
    # logger.debug

    # logger.debug(trialsResponse.json())
    # with open('response.json', 'w') as f:
    #     json.dump(trialJson, f)

def createUniqueSitesCsv(today):
    logger.debug('Reading sites...')
    sitesDf = pd.read_csv(f'nciSites{today}.csv')
    logger.debug('Dropping duplicates and trial-depedent information...')
    sitesDf.drop_duplicates(subset='orgName', inplace=True) 
    sitesDf.drop(['recruitmentStatusDate', 'recruitmentStatus', 'nciId'], axis=1, inplace=True)
    logger.debug('Saving unique sites table...')
    sitesDf.to_csv(f'nciUniqueSites{today}.csv', index=False)

def createUniqueDiseasesCsv(today):
    logger.debug('Reading main diseases...')
    mainDiseasesDf = pd.read_csv(f'nciMainDiseases{today}.csv')
    logger.debug('Dropping duplicates and trial-dependent information...')
    mainDiseasesDf.drop_duplicates(subset='nciThesaurusConceptId', inplace=True)
    mainDiseasesDf.drop(['isLeadDisease', 'inclusionIndicator', 'nciId'], axis=1, inplace=True)
    logger.debug('Saving unique diseases table...')
    mainDiseasesDf.to_csv(f'nciUniqueMainDiseases{today}.csv', index=False)

def createUniqueBiomarkersCsv(today):
    logger.debug('Reading main biomarkers...')
    mainBiomarkersDf = pd.read_csv(f'nciMainBiomarkers{today}.csv')
    logger.debug('Dropping duplicates and trial-dependent information...')
    mainBiomarkersDf.drop_duplicates(subset='nciThesaurusConceptId', inplace=True)
    mainBiomarkersDf.drop(['eligibilityCriterion', 'inclusionIndicator', 'assayPurpose', 'nciId'], axis=1, inplace=True)
    logger.debug('Saving unique biomarkers table...')
    mainBiomarkersDf.to_csv(f'nciUniqueMainBiomarkers{today}.csv', index=False)

def createUniqueInterventionsCsv(today):
    logger.debug('Reading main interventions...')
    mainInterventionsDf = pd.read_csv(f'nciMainInterventions{today}.csv')
    logger.debug('Dropping duplicates and trial-dependent information...')
    mainInterventionsDf.drop_duplicates(subset='nciThesaurusConceptId', inplace=True)
    mainInterventionsDf.drop(['nciId', 'inclusionIndicator'], axis=1, inplace=True)
    logger.debug('Saving unique interventions table...')
    mainInterventionsDf.to_csv(f'nciUniqueMainInterventions{today}.csv', index=False)

def createDiseasesAndBiomarkersRelTable(today):
    logger.debug('Creating diseases and biomarkers relationship...')
    url = r'https://clinicaltrialsapi.cancer.gov/api/v2/biomarkers'

    with open('./nciRetriever/secrets/key.txt') as f:
        apiKey = f.read()

    headers = {
        'X-API-KEY': apiKey,
        'Content-Type': 'application/json'
    }

    logger.debug('Reading unique main diseases...')
    mainDiseasesDf = pd.read_csv(f'nciUniqueMainDiseases{today}.csv')

    diseaseBiomarkerRelDicts = []
    logger.debug('Starting requests...')
    start = time.perf_counter()
    for id in mainDiseasesDf['nciThesaurusConceptId']:
        payload = {
            'maintype': id
        }
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()

        for biomarker in response.json()['data']:
            for code in biomarker['codes']:
                diseaseBiomarkerRelDicts.append({
                    'diseaseNciThesaurusConceptId': id,
                    'biomarkerNciThesaurusConceptId': code
                })
        time.sleep(2)
    elapsed = time.perf_counter() - start
    logger.debug(f'Finished requests in {elapsed: .2f}s')

    diseaseBiomarkerRelDf = pd.DataFrame.from_records(diseaseBiomarkerRelDicts)
    diseaseBiomarkerRelDf.drop_duplicates(inplace=True)
    diseaseBiomarkerRelDf.to_csv(f'DiseaseBiomarkerRelTable.csv', index=False)

def createDiseasesAndInterventionsRelTable(today):
    logger.debug('Creating diseases and interventions relationship...')
    url = r'https://clinicaltrialsapi.cancer.gov/api/v2/interventions'

    with open('./nciRetriever/secrets/key.txt') as f:
        apiKey = f.read()

    headers = {
        'X-API-KEY': apiKey,
        'Content-Type': 'application/json'
    }

    logger.debug('Reading unique main diseases...')
    mainDiseasesDf = pd.read_csv(f'nciUniqueMainDiseases{today}.csv')

    diseaseInterventionRelDicts = []
    logger.debug('Starting requests...')
    start = time.perf_counter()

    for id in mainDiseasesDf['nciThesaurusConceptId']:
        payload = {
            'maintype': id
        }
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()

        for intervention in response.json()['data']:
            for code in intervention['codes']:
                diseaseInterventionRelDicts.append({
                    'diseaseNciThesaurusConceptId': id,
                    'interventionNciThesaurusConceptId': code
                })
        time.sleep(2)
    elapsed = time.perf_counter() - start
    logger.debug(f'Finished requests in {elapsed: .2f}s')

    diseaseInterventionRelDf = pd.DataFrame.from_records(diseaseInterventionRelDicts)
    diseaseInterventionRelDf.drop_duplicates(inplace=True)
    diseaseInterventionRelDf.to_csv(f'DiseaseInterventionRelTable.csv', index=False)


def test():
    url = r'https://clinicaltrialsapi.cancer.gov/api/v2/biomarkers'

    with open('./nciRetriever/secrets/key.txt') as f:
        apiKey = f.read()

    headers = {
        'X-API-KEY': apiKey,
        'Content-Type': 'application/json'
    }

    payload = {
        'maintype': 'C133254'
    }
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    pprint(response.json())

    with open('./responseBiomarker.json', 'w') as f:
        json.dump(response.json(), f)

def view():
    trials = pd.read_csv(r'./nciTrials2022-01-07.csv')
    
    logger.debug(f'Number of rows: {len(trials.index)}')
    logger.debug(f'Number of unique protocolId values: {len(trials["protocolId"].unique())}')
    logger.debug(f'Number of unique nciId values: {len(trials["NciId"].unique())}')

def main():
    logger.debug('Starting NCI retrieval process...')
    start = time.perf_counter()

    retrieveToCsv()
    createUniqueSitesCsv(today)
    createUniqueBiomarkersCsv(today)
    createUniqueDiseasesCsv(today)
    createUniqueInterventionsCsv(today)
    # createDiseasesAndBiomarkersRelTable(today)
    # createDiseasesAndInterventionsRelTable(today)
    csvToArcgisPro(today)
    geocodeSites()
    createRelationships()
    zip()
    update(today)

    elapsed = time.perf_counter() - start
    logger.debug(f'NCI retrieval process completed in {elapsed: .2f}s')
    

if __name__ == '__main__':
    # retrieveToCsv()
    # csvToArcgisPro(today)
    main()
    # updateFC(today)
    # test()
    # view()