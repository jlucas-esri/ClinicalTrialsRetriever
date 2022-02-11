from zipfile import ZipFile, ZIP_DEFLATED
import shutil
import os
from datetime import date
import logging
import time

parentDir = os.path.dirname(os.path.dirname(__file__))
gdb = os.path.realpath(os.path.join(parentDir, 'NCIClinicalTrialsAPI', 'NCIClinicalTrialsAPI.gdb'))

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def zip() -> str:
    # shutil.make_archive(os.path.basename(gdb), 'zip', gdb)
    logger.debug('Zipping Gdb...')
    start = time.perf_counter()
    with ZipFile('NCIClinicalTrialsApiFinal.gdb.zip', 'w', ZIP_DEFLATED) as zip:
        addNonLockFiles(zip)       
    elapsed = time.perf_counter() - start
    logger.debug(f'Zipped Gdb in {elapsed: .2f}s')

        # logger.debug('Adding ')

def addNonLockFiles(zip:ZipFile):
    for dirpath, dirnames, filenames in os.walk(gdb):
        for file in filenames:
            if file.endswith('.lock'):
                continue
            zip.write(os.path.join(dirpath, file), os.path.join(os.path.basename(gdb), 
                                                    os.path.join(dirpath, file)[len(gdb)+len(os.sep):]))