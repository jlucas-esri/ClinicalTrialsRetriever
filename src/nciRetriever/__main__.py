import requests
from typing import List
import re
from nciRetriever.updateFC import updateFC
from nciRetriever.csvToArcgisPro import csvToArcgisPro
from nciRetriever.geocode import geocodeSites
from nciRetriever.createRelationships import createRelationships
from nciRetriever.zipGdb import zipGdb
from nciRetriever.updateItem import update
from nciRetriever.removeTables import removeTables
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

# nciThesaurus = pd.read_csv('thesaurus.csv')
# uniqueMainDiseasesDf = pd.read_csv('nciUniqueMainDiseasesReference.csv')
# uniqueSubTypeDiseasesDf = pd.read_csv('nciUniqueSubTypeDiseasesReference.csv')
# uniqueDiseasesWithoutSynonymsDf = pd.read_csv('nciUniqueDiseasesWithoutSynonymsReference.csv')

def createTrialDict(trial: dict) -> dict:
    trialDict = {'nciId': trial['nci_id'], 
                'protocolId': trial['protocol_id'],
                'nctId': trial['nct_id'], 
                'detailDesc': trial['detail_description'], 
                'officialTitle': trial['official_title'], 
                'briefTitle': trial['brief_title'],
                'briefDesc': trial['brief_summary'],
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
        trialDict.update({'minAgeInYears': int(trial['eligibility']['structured']['min_age_in_years']) if trial['eligibility']['structured']['min_age_in_years'] is not None else None})
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
    if marker['synonyms'] is None:
        namesList = [marker['name']]
    else:
        namesList = [*marker['synonyms'], marker['name']]
    for name in namesList:
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

def createMainToSubTypeRelDicts(trial:dict, disease:dict) -> List[dict]:
    if disease['type'] is None or 'subtype' not in disease['type']:
        return []
    relDicts = []
    for parent in disease['parents']:
        relDicts.append({
            'maintype': parent,
            'subtype': disease['nci_thesaurus_concept_id']
        })
    return relDicts

def createDiseasesWithoutSynonymsDict(trial:dict, disease:dict) -> dict:
    # diseaseDict = {
    #     'nciId': trial['nci_id'],
    #     'inclusionIndicator': disease['inclusion_indicator'],
    #     'isLeadDisease': disease['is_lead_disease'],
    #     'nciThesaurusConceptId': disease['nci_thesaurus_concept_id']
    # }
    # correctDisease = uniqueDiseasesWithoutSynonymsDf.loc[uniqueDiseasesWithoutSynonymsDf['nciThesaurusConceptId'] == disease['nci_thesaurus_concept_id']] 
    # if correctDisease.empty:
    #     logger.error('Disease not found in full reference. Aborting insertion...')
    #     return {}
    # # logger.debug(correctDisease['name'].values[0])
    # # time.sleep(2)
    # diseaseDict.update({
    #     'name': correctDisease['name'].values[0]
    # })
    # return diseaseDict

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
    

def createMainDiseasesDict(trial:dict, disease:dict) -> dict:
    # diseaseDict = {
    #     'nciId': trial['nci_id'],
    #     'inclusionIndicator': disease['inclusion_indicator'],
    #     'isLeadDisease': disease['is_lead_disease'],
    #     'nciThesaurusConceptId': disease['nci_thesaurus_concept_id']
    # }
    # correctDisease = uniqueMainDiseasesDf.loc[uniqueMainDiseasesDf['nciThesaurusConceptId'] == disease['nci_thesaurus_concept_id']] 
    # if correctDisease.empty:
    #     return {}

    # diseaseDict.update({
    #     'name': correctDisease['name'].values[0]
    # })
    # return diseaseDict
    # if 'type' not in disease.keys():
    #     return {}
    if disease['type'] is None or 'maintype' not in disease['type']:
        return {}

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

def createSubTypeDiseasesDict(trial:dict, disease:dict) -> dict:
    # diseaseDict = {
    #     'nciId': trial['nci_id'],
    #     'inclusionIndicator': disease['inclusion_indicator'],
    #     'isLeadDisease': disease['is_lead_disease'],
    #     'nciThesaurusConceptId': disease['nci_thesaurus_concept_id']
    # }
    # correctDisease = uniqueSubTypeDiseasesDf.loc[uniqueSubTypeDiseasesDf['nciThesaurusConceptId'] == disease['nci_thesaurus_concept_id']] 
    # if correctDisease.empty:
    #     return {}

    # diseaseDict.update({
    #     'name': correctDisease['name'].values[0]
    # })
    # return diseaseDict
    # if 'type' not in disease.keys():
    #     return {}
    if disease['type'] is None or 'subtype' not in disease['type']:
        return {}

    try:
        return {
            'nciId': trial['nci_id'],
            'name': disease['name'],
            'isLeadDisease': disease['is_lead_disease'],
            'nciThesaurusConceptId': disease['nci_thesaurus_concept_id'],
            'inclusionIndicator': disease['inclusion_indicator']
        }   
    except KeyError:
        logger.error('Invalid key for subtype diseases. Not adding to list...')
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

def deDuplicateTable(csvName:str, deduplicationList:List[str]):
    df = pd.read_csv(csvName)
    df.drop_duplicates(subset=deduplicationList, inplace=True)
    df.dropna(subset=deduplicationList, inplace=True)
    df.to_csv(csvName, index=False)

def correctMainToSubTypeTable(today):
    mainDf = pd.read_csv(f'nciUniqueMainDiseases{today}.csv')
    subTypeDf = pd.read_csv(f'nciUniqueSubTypeDiseases{today}.csv')
    relDf = pd.read_csv(f'MainToSubTypeRelTable{today}.csv')
    for idx, row in relDf.iterrows():
        parentId = row['maintype']
        if parentId in mainDf['nciThesaurusConceptId'].values:
            continue
        elif parentId in subTypeDf['nciThesaurusConceptId'].values:
            while True:
                possibleMainTypesDf = relDf[relDf['subtype'] == parentId]
                if possibleMainTypesDf.empty:
                    logger.error(f'Parent {parentId} not found in main diseases or subtype diseases')
                    parentId = ''
                    break
                #setting the parentId value with the parent of the subtype found
                for value in possibleMainTypesDf['maintype'].values:
                    if parentId == value:
                        continue
                    parentId = value
                    break
                else:
                    logger.error(f'Parent {parentId} not found in main diseases or subtype diseases')
                    parentId = ''
                    break
                # parentId = possibleMainTypesDf['maintype'].values[0]
                if parentId in mainDf['nciThesaurusConceptId'].values:
                    break

            if parentId == '':
                continue

            relDf.iloc[idx]['maintype'] = parentId
        else:
            pass
    relDf.to_csv(f'MainToSubTypeRelTable{today}.csv', index=False)
            # logger.error(f'maintype id {parentId} is not found in main diseases or subtype diseases')

def createUniqueSitesCsv(today):
    logger.debug('Reading sites...')
    sitesDf = pd.read_csv(f'nciSites{today}.csv')
    logger.debug('Dropping duplicates and trial-depedent information...')
    sitesDf.drop_duplicates(subset='orgName', inplace=True) 
    sitesDf.drop(['recruitmentStatusDate', 'recruitmentStatus', 'nciId'], axis=1, inplace=True)
    logger.debug('Saving unique sites table...')
    sitesDf.to_csv(f'nciUniqueSites{today}.csv', index=False)

def createUniqueDiseasesWithoutSynonymsCsv(today):
    logger.debug('Reading diseases without synonyms...')
    diseasesWithoutSynonymsDf = pd.read_csv(f'nciDiseasesWithoutSynonyms{today}.csv')
    logger.debug('Dropping duplicates and trial-dependent information...')
    diseasesWithoutSynonymsDf.drop_duplicates(subset='nciThesaurusConceptId', inplace=True)
    diseasesWithoutSynonymsDf.drop(['isLeadDisease', 'inclusionIndicator', 'nciId'], axis=1, inplace=True)
    diseasesWithoutSynonymsDf.dropna()
    logger.debug('Saving unique diseases table...')
    diseasesWithoutSynonymsDf.to_csv(f'nciUniqueDiseasesWithoutSynonyms{today}.csv', index=False)

def createUniqueMainDiseasesCsv(today):
    logger.debug('Reading main diseases...')
    mainDiseasesDf = pd.read_csv(f'nciMainDiseases{today}.csv')
    logger.debug('Dropping duplicates and trial-dependent information...')
    mainDiseasesDf.drop_duplicates(subset='nciThesaurusConceptId', inplace=True)
    mainDiseasesDf.drop(['isLeadDisease', 'inclusionIndicator', 'nciId'], axis=1, inplace=True)
    mainDiseasesDf.dropna()
    logger.debug('Saving unique diseases table...')
    mainDiseasesDf.to_csv(f'nciUniqueMainDiseases{today}.csv', index=False)

def createUniqueSubTypeDiseasesCsv(today):
    logger.debug('Reading main diseases...')
    subTypeDiseasesDf = pd.read_csv(f'nciSubTypeDiseases{today}.csv')
    logger.debug('Dropping duplicates and trial-dependent information...')
    subTypeDiseasesDf.drop_duplicates(subset='nciThesaurusConceptId', inplace=True)
    subTypeDiseasesDf.drop(['isLeadDisease', 'inclusionIndicator', 'nciId'], axis=1, inplace=True)
    subTypeDiseasesDf.dropna()
    logger.debug('Saving unique diseases table...')
    subTypeDiseasesDf.to_csv(f'nciUniqueSubTypeDiseases{today}.csv', index=False)

def createUniqueBiomarkersCsv(today):
    logger.debug('Reading main biomarkers...')
    mainBiomarkersDf = pd.read_csv(f'nciMainBiomarkers{today}.csv')
    logger.debug('Dropping duplicates and trial-dependent information...')
    mainBiomarkersDf.drop_duplicates(subset='nciThesaurusConceptId', inplace=True)
    mainBiomarkersDf.drop(['eligibilityCriterion', 'inclusionIndicator', 'assayPurpose', 'nciId'], axis=1, inplace=True)
    mainBiomarkersDf.dropna()
    logger.debug('Saving unique biomarkers table...')
    mainBiomarkersDf.to_csv(f'nciUniqueMainBiomarkers{today}.csv', index=False)

def createUniqueInterventionsCsv(today):
    logger.debug('Reading main interventions...')
    mainInterventionsDf = pd.read_csv(f'nciMainInterventions{today}.csv')
    logger.debug('Dropping duplicates and trial-dependent information...')
    mainInterventionsDf.drop_duplicates(subset='nciThesaurusConceptId', inplace=True)
    mainInterventionsDf.drop(['nciId', 'inclusionIndicator', 'arm', 'nciIdWithArm'], axis=1, inplace=True)
    mainInterventionsDf.dropna()
    logger.debug('Saving unique interventions table...')
    mainInterventionsDf.to_csv(f'nciUniqueMainInterventions{today}.csv', index=False)

def retrieveToCsv():


    baseUrl = r'https://clinicaltrialsapi.cancer.gov/api/v2/'
    with open('./nciRetriever/secrets/key.txt', 'r') as f:
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
    createdMainToSubTypeRelTableCsv = False
    createdDiseaseWithoutSynonymsCsv = False
    createdMainDiseaseCsv = False
    createdSubTypeDiseaseCsv = False
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
                                        'briefTitle',
                                        'briefDesc',
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

        mainToSubTypeRelsDf = pd.DataFrame(columns=[
            'maintype',
            'subtype'
        ])

        mainDiseasesDf = pd.DataFrame(columns=[
            'nciId',
            'inclusionIndicator',
            'isLeadDisease',
            'nciThesaurusConceptId',
            'name'
        ])

        diseasesWithoutSynonymsDf = pd.DataFrame(columns=[
            'nciId',
            'inclusionIndicator',
            'isLeadDisease',
            'nciThesaurusConceptId',
            'name'
        ])

        subTypeDiseasesDf = pd.DataFrame(columns=[
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
                    # biomarkers.extend(createBiomarkersDicts(trial, biomarker))

                    mainBiomarkersDict = createMainBiomarkersDict(trial, biomarker)
                    if mainBiomarkersDict != {}:
                        mainBiomarkers.append(mainBiomarkersDict)

                # biomarkerDf = pd.DataFrame.from_records(biomarkers)
                # biomarkersDf = pd.concat([biomarkersDf, biomarkerDf], ignore_index=True, verify_integrity=True)
                mainBiomarkerDf = pd.DataFrame.from_records(mainBiomarkers)
                mainBiomarkersDf = pd.concat([mainBiomarkersDf, mainBiomarkerDf], ignore_index=True, verify_integrity=True)
                
            if trial['diseases'] is not None:
                # diseases = []
                mainToSubTypeRel = []
                mainDiseases = []
                subTypeDiseases = []
                diseasesWithoutSynonyms = []
                for disease in trial['diseases']:
                    # diseasesDicts = createDiseasesDicts(trial, disease)
                    # diseases.extend(diseasesDicts)
                    mainDiseasesDict = createMainDiseasesDict(trial, disease)
                    if mainDiseasesDict != {}:
                        mainDiseases.append(mainDiseasesDict)
                    subTypeDiseasesDict = createSubTypeDiseasesDict(trial, disease)
                    if subTypeDiseasesDict != {}:
                        subTypeDiseases.append(subTypeDiseasesDict)
                    diseasesWithoutSynonymsDict = createDiseasesWithoutSynonymsDict(trial, disease)
                    if diseasesWithoutSynonymsDict != {}:
                        diseasesWithoutSynonyms.append(diseasesWithoutSynonymsDict)

                    mainToSubTypeRel.extend(createMainToSubTypeRelDicts(trial, disease))
                    

                # diseaseDf = pd.DataFrame.from_records(diseases)
                # diseasesDf = pd.concat([diseasesDf, diseaseDf], ignore_index=True, verify_integrity=True)
                mainToSubTypeRelDf = pd.DataFrame.from_records(mainToSubTypeRel)
                mainToSubTypeRelsDf = pd.concat([mainToSubTypeRelsDf, mainToSubTypeRelDf], ignore_index=True, verify_integrity=True)

                mainDiseaseDf = pd.DataFrame.from_records(mainDiseases)
                mainDiseasesDf = pd.concat([mainDiseasesDf, mainDiseaseDf], ignore_index=True, verify_integrity=True)

                subTypeDiseaseDf = pd.DataFrame.from_records(subTypeDiseases)
                subTypeDiseasesDf = pd.concat([subTypeDiseasesDf, subTypeDiseaseDf], ignore_index=True, verify_integrity=True)

                diseaseWithoutSynonymsDf = pd.DataFrame.from_records(diseasesWithoutSynonyms)
                diseasesWithoutSynonymsDf = pd.concat([diseasesWithoutSynonymsDf, diseaseWithoutSynonymsDf], ignore_index=True, verify_integrity=True)

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
        def createAndAddToCsv(createdBoolean:bool, df:pd.DataFrame, fileName:str):
            if not createdBoolean:
                if os.path.isfile(fileName):
                    os.remove(fileName)
                df.to_csv(fileName, index=False)
                createdBoolean = True
            else:
                df.to_csv(fileName, index=False, mode='a', header=False)
            return createdBoolean

        createdSiteCsv = createAndAddToCsv(createdSiteCsv, sitesDf, f'nciSites{today}.csv')
        createdTrialCsv = createAndAddToCsv(createdTrialCsv, trialsDf, f'nciTrials{today}.csv')
        createdEligibilityCsv = createAndAddToCsv(createdEligibilityCsv, eligibilityDf, f'nciEligibility{today}.csv')
        # createdBiomarkerCsv = createAndAddToCsv(createdBiomarkerCsv, biomarkersDf, f'nciBiomarkers{today}.csv')

        # mainBiomarkersDf.drop_duplicates(['nciId', 'nciThesaurusConceptId'], inplace=True)
        createdMainBiomarkerCsv = createAndAddToCsv(createdMainBiomarkerCsv, mainBiomarkersDf, f'nciMainBiomarkers{today}.csv')

        # createdDiseaseCsv = createAndAddToCsv(createdDiseaseCsv, diseasesDf, f'nciDiseases{today}.csv')

        # diseasesWithoutSynonymsDf.drop_duplicates(['nciId', 'nciThesaurusConceptId'], inplace=True)
        createdDiseaseWithoutSynonymsCsv = createAndAddToCsv(createdDiseaseWithoutSynonymsCsv, diseasesWithoutSynonymsDf, f'nciDiseasesWithoutSynonyms{today}.csv')

        # mainToSubTypeRelsDf.drop_duplicates(['maintype', 'subtype'], inplace=True)
        createdMainToSubTypeRelTableCsv = createAndAddToCsv(createdMainToSubTypeRelTableCsv, mainToSubTypeRelsDf, f'MainToSubTypeRelTable{today}.csv')        

        # mainDiseasesDf.drop_duplicates(['nciId', 'nciThesaurusConceptId'], inplace=True)
        createdMainDiseaseCsv = createAndAddToCsv(createdMainDiseaseCsv, mainDiseasesDf, f'nciMainDiseases{today}.csv')

        # subTypeDiseasesDf.drop_duplicates(['nciId', 'nciThesaurusConceptId'], inplace=True)
        createdSubTypeDiseaseCsv = createAndAddToCsv(createdSubTypeDiseaseCsv, subTypeDiseasesDf, f'nciSubTypeDiseases{today}.csv')

        createdArmsCsv = createAndAddToCsv(createdArmsCsv, armsDf, f'nciArms{today}.csv')
        # createdInterventionCsv = createAndAddToCsv(createdInterventionCsv, interventionsDf, f'nciInterventions{today}.csv')

        # mainInterventionsDf.drop_duplicates(['nciIdWithArm', 'nciThesaurusConceptId'], inplace=True)
        createdMainInterventionCsv = createAndAddToCsv(createdMainInterventionCsv, mainInterventionsDf, f'nciMainInterventions{today}.csv')


        sectionElapsed = time.perf_counter()-sectionStart

        logger.debug(f'Trials {trialNumFrom}-{trialNumFrom+50} retrieved in {sectionElapsed: .2f}s')


        #ensuring that a request isn't sent less than three seconds after the last one. This avoids rate limiting
        if sectionElapsed < 3:
            time.sleep(3-sectionElapsed)
            
            
    elapsed = time.perf_counter() - start
    logger.debug(f'All {totalNumTrials} trials retrieved and saved in {elapsed: .2f}s')
    logger.debug('De-duplicating all necessary csv files...')

    deDuplicateTable(f'nciDiseasesWithoutSynonyms{today}.csv', ['nciId', 'nciThesaurusConceptId'])
    deDuplicateTable(f'nciMainDiseases{today}.csv', ['nciId', 'nciThesaurusConceptId'])
    deDuplicateTable(f'nciSubTypeDiseases{today}.csv', ['nciId', 'nciThesaurusConceptId'])
    deDuplicateTable(f'nciMainBiomarkers{today}.csv', ['nciId', 'nciThesaurusConceptId'])
    deDuplicateTable(f'nciMainInterventions{today}.csv', ['nciIdWithArm', 'nciThesaurusConceptId'])

    createUniqueSitesCsv(today)
    createUniqueBiomarkersCsv(today)
    createUniqueDiseasesWithoutSynonymsCsv(today)
    createUniqueMainDiseasesCsv(today)
    createUniqueSubTypeDiseasesCsv(today)
    createUniqueInterventionsCsv(today)

    deDuplicateTable(f'MainToSubTypeRelTable{today}.csv', ['maintype', 'subtype'])
    logger.debug('Correcting any subtype ids in the maintype column for the main disease to subtype disease relationship table...')
    start = time.perf_counter()
    correctMainToSubTypeTable(today)
    elapsed = time.perf_counter() - start
    logger.debug(f'Main disease to subtype disease relationship table corrected in {elapsed: .2f}s')
    deDuplicateTable(f'MainToSubTypeRelTable{today}.csv', ['maintype', 'subtype'])


def createDiseasesAndBiomarkersRelTable(today, inputCsv:str, outputCsv:str):
    logger.debug('Creating diseases and biomarkers relationship...')
    url = r'https://clinicaltrialsapi.cancer.gov/api/v2/biomarkers'

    with open('./nciRetriever/secrets/key.txt') as f:
        apiKey = f.read()

    headers = {
        'X-API-KEY': apiKey,
        'Content-Type': 'application/json'
    }

    logger.debug('Reading unique diseases...')
    mainDiseasesDf = pd.read_csv(inputCsv)

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
    diseaseBiomarkerRelDf.to_csv(outputCsv, index=False)

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
    url = r'https://clinicaltrialsapi.cancer.gov/api/v2/trials'

    with open('./nciRetriever/secrets/key.txt') as f:
        apiKey = f.read()

    headers = {
        'X-API-KEY': apiKey,
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    # pprint(response.json())

    with open('./response.json', 'w') as f:
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
    # createDiseasesAndBiomarkersRelTable(today, f'nciUniqueMainDiseases{today}.csv', f'MainDiseaseBiomarkerRelTable{today}.csv')
    # # # # createDiseasesAndBiomarkersRelTable(today, f'nciUniqueDiseasesWithoutSynonyms{today}.csv', 'DiseaseBiomarkerRelTable.csv')
    # createDiseasesAndInterventionsRelTable(today)
    csvToArcgisPro(today)
    geocodeSites()
    createRelationships()
    removeTables()

    zipGdb()
    update(today)

    elapsed = time.perf_counter() - start
    logger.debug(f'NCI retrieval process completed in {elapsed: .2f}s')

def testThesaurus():

    thesaurus = pd.read_csv('./thesaurus.csv')
    # print(thesaurus.head(10))
    print(thesaurus['type'].unique())

def editThesaurus():
    thesaurus = pd.read_csv('./Thesaurus.txt', delimiter='\t')
    thesaurus.rename(columns={oldName: newName for oldName, newName in zip(thesaurus.columns, ['code', 'concept', 'parents', 'synonyms', 'definition', 'name', 'conceptStatus', 'type'])}, inplace=True)
    thesaurus.to_csv('thesaurus.csv', index=False)

    

if __name__ == '__main__':
    # retrieveToCsv()
    # csvToArcgisPro(today)
    main()
    # updateFC(today)
    # test()
    # editThesaurus()
    # testThesaurus()
    # view()
