import arcpy
import os
import re
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

def createRelationships():
    for destTable in ['nciEligibility', 'nciBiomarkers', 'nciDiseases', 'nciArms']:
        logger.debug(f'Relating nciTrials and {destTable}...')
        createOneToManyTrialRelationship(destTable)

    logger.debug('Relating nciTrials and nciUniqueSitesGeocoded...')
    createManyToManySitesTrialsRelationship()

    logger.debug('Relating nciArms and nciInterventions')
    createOneToManyArmsRelationship()

def createOneToManyTrialRelationship(destTable:str):
    arcpy.management.CreateRelationshipClass(
        os.path.join(gdb, 'nciTrials'),
        os.path.join(gdb, destTable),
        os.path.join(gdb, f'Trials{re.sub(r"nci", "", destTable)}RelClass'),
        'SIMPLE',
        f'Attributes from {destTable}',
        'Attributes from nciTrials',
        cardinality='ONE_TO_MANY',
        origin_primary_key='nciId',
        origin_foreign_key='nciId'
    )

def createManyToManySitesTrialsRelationship():
    attributeFields = [field.name for field in arcpy.ListFields(os.path.join(gdb, 'nciSites')) if field.name in ['nciId', 'orgName', 'recruitmentStatus', 'recruitmentStatusDate']]

    arcpy.management.TableToRelationshipClass(
        os.path.join(gdb, 'nciTrials'),
        os.path.join(gdb, 'nciUniqueSitesGeocoded'),
        os.path.join(gdb, 'TrialsSitesRelClass'),
        'SIMPLE',
        'Attributes from nciUniqueSitesGeocoded',
        'Attributes from nciTrials',
        cardinality='MANY_TO_MANY',
        relationship_table=os.path.join(gdb, 'nciSites'),
        attribute_fields=attributeFields,
        origin_primary_key='nciId',
        origin_foreign_key='nciId',
        destination_primary_key='orgName',
        destination_foreign_key='orgName'
    )

def createOneToManyArmsRelationship():
    arcpy.management.CreateRelationshipClass(
        os.path.join(gdb, 'nciArms'),
        os.path.join(gdb, 'nciInterventions'),
        os.path.join(gdb, 'ArmsInterventionsRelClass'),
        'SIMPLE',
        'Attributes from nciInterventions',
        'Attributes from nciArms',
        cardinality='ONE_TO_MANY',
        origin_primary_key='nciIdWithName',
        origin_foreign_key='nciIdWithArm'
    )