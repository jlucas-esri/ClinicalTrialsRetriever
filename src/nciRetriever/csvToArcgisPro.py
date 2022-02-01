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
        f'nciBiomarkers{today}.csv',
        f'nciDiseases{today}.csv',
        f'nciArms{today}.csv',
        f'nciInterventions{today}.csv' 
    ]
    logger.debug(f'Output gdb: {outGdbLocation}')
    

    for csvName in csvNames:
        outTableName, _ = os.path.splitext(csvName)
        outTableName = re.sub(r'[\-0-9]', '', outTableName)
        logger.debug(f'Csv name: {csvName}')
        logger.debug(f'Output table name: {outTableName}')
        arcpy.conversion.TableToTable(csvName, outGdbLocation, outTableName)

