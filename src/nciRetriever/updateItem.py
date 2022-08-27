from arcgis.gis import GIS
import os
from datetime import date
import logging
import time

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def update(today:date):
    gis = GIS('pro')
    newGdbZip = os.path.realpath(r'./NCIClinicalTrialsApiFinal2.gdb.zip')

    logger.debug('Getting and overwriting item...')
    start = time.perf_counter()
    
    with open(r'nciRetriever/secrets/itemId.txt') as f:
        itemId = f.read()

    nciGdbItem = gis.content.get(itemId)
    nciGdbItem.update(item_properties={'description': f'NCI Clinical Trials API Data as of {today}'}, data=newGdbZip)
    nciGdbItem.publish(overwrite=True)
    nciGdbItem.share(everyone=True)

    elapsed = time.perf_counter() - start
    logger.debug(f'Item overwritten in {elapsed: .2f}s')