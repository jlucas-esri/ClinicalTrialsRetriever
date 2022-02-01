import arcpy
import os

def geocodeSites():
    locator = r''
    arcpy.env.workspace = os.path.dirname(os.path.dirname(__file__))
    arcpy.env.overwriteOutput = True
    gdb = os.path.join(arcpy.env.workspace, 'NCIClinicalTrialsAPI', 'NCIClinicalTrialsAPI.gdb')
    sitesTable = os.path.join(gdb, 'nciUniqueSites')
    arcpy.geocoding.GeocodeAddresses(in_table=sitesTable, address_locator=locator, in_address_fields= "'Address or Place' orgAddressLine1 VISIBLE NONE;Address2 orgAddressLine2 VISIBLE NONE;Address3 <None> VISIBLE NONE;Neighborhood <None> VISIBLE NONE;City orgCity VISIBLE NONE;County orgCounty VISIBLE NONE;State orgStateOrProvince VISIBLE NONE;ZIP orgPostalCode VISIBLE NONE;ZIP4 <None> VISIBLE NONE;Country orgCountry VISIBLE NONE", out_feature_class=os.path.join(gdb, 'nciUniqueSitesGeocoded'), out_relationship_type="STATIC", country=None, location_type="ADDRESS_LOCATION", category="Address", output_fields="MINIMAL"))

