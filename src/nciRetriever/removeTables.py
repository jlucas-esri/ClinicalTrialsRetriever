import arcpy
import os
import logging

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

arcpy.env.workspace = os.path.dirname(os.path.dirname(__file__))
arcpy.env.overwriteOutput = True
gdb = os.path.join(arcpy.env.workspace, 'NCIClinicalTrialsAPI', 'NCIClinicalTrialsAPI.gdb')

def removeTables():
    logger.debug('Deleting unnecessary tables...')
    for table in ['nciSites', 'nciUniqueSites']:
        arcpy.management.Delete(table)