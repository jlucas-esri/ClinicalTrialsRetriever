from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection
import logging

def updateFC(today):
    gis = GIS('home')


    # if not gis.content.is_service_name_available('upToDateNciClinicalTrialsData', 'featureService'):
    #     service = gis.content.search(query='upToDateNciClinicalTrialsData', item_type='Feature Service')[0]
    # else:
    #     service = gis.content.create_service('upToDateNciClinicalTrialsData', has_static_data=False, service_type='featureService')
    #     serviceFLC = FeatureLayerCollection.fromitem(service)
    #     siteResponse = serviceFLC.upload(f'nciSites{today}.csv', f'NCI Clinical Trials associated sites as of {today}')
    #     eligibilityResponse = serviceFLC.upload(f'nciEligibility{today}.csv', f'NCI Unstructured Eligibility for each trial as of {today}')
    #     trialsResponse = serviceFLC.upload(f'nciTrials{today}.csv', f'NCI Clinical Trials as of {today}')

    trialsFSList = gis.content.search(query='upToDateNciClinicalTrialsData', item_type='Feature Service')
    trialsFSProps = {
        'title': 'upToDateNciClinicalTrialsData',
        'tags': ['NCI', 'Cancer', 'Clinical Trials'],
        'description': f'National Cancer Institute Clinical Trials Information as of {today}',
        'type': 'Feature Service',
        'overwrite': True
    }
    if not len(trialsFSList):
        trialsFS = gis.content.add(item_properties=trialsFSProps, data=f'./nciTrials{today}.csv')
    else:
        trialsFS = trialsFSList[0]
        trialsFS.update(item_properties=trialsFSProps, data=f'./nciTrials{today}.csv')
    
    sitesFSList = gis.content.search(query='upToDateNciSitesData', item_type='Feature Service')
    sitesFSProps = {
        'title': 'upToDateNciSitesData',
        'tags': ['NCI', 'Cancer', 'Sites'],
        'description': f'National Cancer Institute Clinical Trials Sites Information as of {today}',
        'type': 'Feature Service',
        'overwrite': True
    }
    if not len(sitesFSList):
        sitesFS = gis.content.add(item_properties=sitesFSProps, data=f'./nciSites{today}.csv')
    else:
        sitesFS = sitesFSList[0]
        sitesFS.update(item_properties=sitesFSProps, data=f'./nciSites{today}.csv')

    eligibilityFSList = gis.content.search(query='upToDateNciEligibilityData', item_type='Feature Service')
    eligibilityFSProps = {
        'title': 'upToDateNciEligbilityData',
        'tags': ['NCI', 'Cancer', 'Eligibility'],
        'description': f'National Cancer Institute Clinical Trials Eligibility Information as of {today}',
        'type': 'Feature Service',
        'overwrite': True
    }

    if not len(eligibilityFSList):
        eligibilityFS = gis.content.add(item_properties=eligibilityFSProps, data=f'./nciEligibility{today}.csv')
    else:
        eligibilityFS = eligibilityFSList[0]
        eligibilityFS.update(item_properties=eligibilityFSProps, data=f'./nciEligibility{today}.csv')
    # print(siteResponse)
    # print(eligibilityResponse)
    # print(trialsResponse)
        
    # # print(dir(service))
    # print(service.properties)
    # print(service.tables)
    # print(service.layers)
    # print(dir(service))

    # if len(service.layers) == 0:
    #     service.upload(f'nciSites{today}.csv', f'NCI Clinical Trials associated sites as of {today}')
    # if len(service.tables) == 0:
    #     service.upload(f'nciEligibility{today}.csv', f'NCI Unstructured Eligibility for each trial as of {today}')
    #     service.upload(f'nciTrials{today}.csv', f'NCI Clinical Trials as of {today}')

    