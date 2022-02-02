import arcpy
import os
import logging
import time

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def geocodeSites():
    # locator = r''
    locator = r'https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/ArcGIS World Geocoding Service'
    arcpy.env.workspace = os.path.dirname(os.path.dirname(__file__))
    arcpy.env.overwriteOutput = True
    gdb = os.path.join(arcpy.env.workspace, 'NCIClinicalTrialsAPI', 'NCIClinicalTrialsAPI.gdb')
    sitesTable = os.path.join(gdb, 'nciUniqueSites')

    logger.debug('Geocoding sites...')
    start = time.perf_counter()
    arcpy.geocoding.GeocodeAddresses(in_table=sitesTable, address_locator=locator, in_address_fields= "'Address or Place' orgAddressLine1 VISIBLE NONE;Address2 orgAddressLine2 VISIBLE NONE;Address3 <None> VISIBLE NONE;Neighborhood <None> VISIBLE NONE;City orgCity VISIBLE NONE;County orgCounty VISIBLE NONE;State orgStateOrProvince VISIBLE NONE;ZIP orgPostalCode VISIBLE NONE;ZIP4 <None> VISIBLE NONE;Country orgCountry VISIBLE NONE", out_feature_class=os.path.join(gdb, 'nciUniqueSitesGeocoded'), out_relationship_type="STATIC", country=None, location_type="ADDRESS_LOCATION", category="Address", output_fields="MINIMAL")
    elapsed = time.perf_counter() - start
    logger.debug(f'Sites geocoded in {elapsed: .2f}s')
