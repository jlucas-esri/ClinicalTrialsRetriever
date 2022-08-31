# ClinicalTrialsRetriever
interacting with the clinical trials api and retrieving relevant data for Esri cancer project

### Details:

The main script is `src/nciRetriever/__main__.py`

This script should be run in the ArcGIS Pro python virtual environment as this script requires the arcgis and arcpy libraries.

In order to run the script, a file containing the user's National Cancer Institute Clinical Trials API key must be added. The path of this file must be: `src/nciRetriever/secrets/key.txt`.

On the first run, the script will error out where it gets to the ArcGIS Item overwrite section. In order to set up an error-free automated process, upload the zipped file geodatabase located at `src/NCIClinicalTrialsApiFinal2.gdb.zip` to ArcGIS Online. Ensure an accompanying feature service is also created. Then, a file containing the item ID of the ArcGIS Online file geodatabase item (not the feature service!) must be added. The path of this file must be: `src/nciRetriever/secrets/itemId.txt`.

After this is set up, the script can be run every day without error or direct management while updating the clinical trials data stored in ArcGIS Online.




