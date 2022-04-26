import pandas as pd
import os
from datetime import date
import logging
from tqdm import tqdm

# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt='%Y-%m-%d %H:%M:%S')

def getTrialStats(today:date):
    os.chdir(os.path.realpath('../'))
    diseasesDf = pd.read_csv(f'nciMainDiseases{today}.csv')
    sitesToTrialsDf = pd.read_csv(f'nciSites{today}.csv')
    # sitesDiseaseCountDf = pd.DataFrame(columns=['orgName', 'nciThesaurusConceptId', 'disease', 'count'])
    sitesDiseaseCount = [] 

    for row in tqdm(sitesToTrialsDf[['orgName', 'nciId']].itertuples(), total=len(sitesToTrialsDf.index)):
        #removing the Other Cancer, Other Neoplasm, and Other Disease entries
        relevantDiseasesDf = diseasesDf[(diseasesDf['nciId'] == row.nciId) & (~diseasesDf['nciThesaurusConceptId'].isin(['C2991', 'C3262', 'C2916']))]
        relevantDiseasesDf = relevantDiseasesDf[relevantDiseasesDf['isLeadDisease'] == 1]
        for id in relevantDiseasesDf['nciThesaurusConceptId'].unique():

            rowDict = {
                'orgName': row.orgName,
                'nciThesaurusConceptId': id,
                'disease': relevantDiseasesDf[relevantDiseasesDf['nciThesaurusConceptId'] == id]['name'].iloc[0],
                # 'count': len(relevantDiseasesDf[relevantDiseasesDf['nciThesaurusConceptId'] == id].index)
            }

            sitesDiseaseCount.append(rowDict)

    sitesDiseaseCountDf = pd.DataFrame.from_records(sitesDiseaseCount)
    sitesDiseaseCountDf = sitesDiseaseCountDf.value_counts(['orgName', 'nciThesaurusConceptId', 'disease']).reset_index()
    sitesDiseaseCountDf.to_csv(f'nciSitesToDiseasesCount{today}.csv', index=False)

def deDuplicateStats(today:date):
    df = pd.read_csv(f'nciSitesToDiseasesCount{today}.csv')
    df.drop_duplicates(inplace=True)
    df.to_csv(f'nciSitesToDiseasesCount{today}.csv', index=False)

if __name__ == '__main__':
    today = date.today()
    getTrialStats(today)
    # deDuplicateStats(today)
