import arcpy
import logging
import os
from datetime import date
import re

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
def csvToArcgisPro(today:date):

    arcpy.env.workspace = os.path.dirname(os.path.dirname(__file__))
    arcpy.env.overwriteOutput = True
    outGdbLocation = os.path.join(arcpy.env.workspace, 'NCIClinicalTrialsAPI', 'NCIClinicalTrialsAPI.gdb')

    csvNames = [
        f'nciTrials{today}.csv',
        f'nciSites{today}.csv',
        f'nciUniqueSites{today}.csv',
        f'nciEligibility{today}.csv',
        # f'nciBiomarkers{today}.csv',
        # f'nciDiseases{today}.csv',
        f'nciArms{today}.csv',
        # f'nciInterventions{today}.csv',
        f'nciMainDiseases{today}.csv',
        f'nciDiseasesWithoutSynonyms{today}.csv',
        f'nciSubTypeDiseases{today}.csv',
        f'nciMainBiomarkers{today}.csv',
        f'nciMainInterventions{today}.csv',
        f'nciUniqueMainDiseases{today}.csv',
        f'nciUniqueDiseasesWithoutSynonyms{today}.csv',
        f'nciUniqueSubTypeDiseases{today}.csv',
        f'nciUniqueMainBiomarkers{today}.csv',
        f'nciUniqueMainInterventions{today}.csv',
        # 'DiseaseBiomarkerRelTable.csv',
        # f'MainDiseaseBiomarkerRelTable{today}.csv',
        f'MainToSubTypeRelTable{today}.csv',
        # 'DiseaseInterventionRelTable.csv' 
    ]
    logger.debug(f'Output gdb: {outGdbLocation}')
    

    for csvName in csvNames:
        outTableName, _ = os.path.splitext(csvName)
        outTableName = re.sub(r'[\-0-9]', '', outTableName)
        logger.debug(f'Importing {csvName} as {outTableName}...')
        arcpy.conversion.TableToTable(csvName, outGdbLocation, outTableName)

