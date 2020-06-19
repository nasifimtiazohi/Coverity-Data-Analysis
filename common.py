import sql
import os
import numpy as np
import pandas as pd
import coloredlogs, logging
coloredlogs.install()

def is_integer(n):
    try:
        int(n)
    except ValueError:
        return False
    return True

def read_xml_file_to_list_of_dicts(file):
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(file)
        root = tree.getroot()
    except:
        return [] #no xml data

    datalist=[]
    for child in root:
        data=child.attrib
        datalist.append(data)
    
    return datalist

def get_project_id(project):
    q='select id from project where name=%s'
    results=sql.execute(q,(project,))
    if not results:
        return None
    elif len(results) >1 :
        logging.error("more than one project with the name %s",project)
    return results[0]['id']

def replace_blankString_with_NaN(df):
    return df.replace(r'^\s*$', np.NaN, regex=True)


def get_start_end_date(projectId):
    '''returns as dateformat '''
    d={}

    q="select start_date, end_date from project where id=%s"
    results=sql.execute(q,(projectId,))
    if not results:
        return d
    result=results[0]

    start=result['start_date']
    end=result['end_date']

    return start, end

def get_repo_name(projectId):
    q='select github_url from project where id=%s'
    results=sql.execute(q,(projectId,))
    gh_url =  results[0]['github_url']
    #take the last part
    return gh_url.split('/')[-1]


def get_snapshot_date(projectId, snapshotId):
    q='''select * from snapshot
        where project_id=%s
        and id=%s; '''
    results=sql.execute(q,(projectId, snapshotId))
    if results:
        temp=results[0]
        if temp['code_version_date']:
            last_detected_date=temp['code_version_date']
        else:
            last_detected_date=temp["date"]
        return last_detected_date
    else:
        logging.error('invalid arguments while finding snapshot date')

def get_next_snapshotId(projectId, snapshotId):
    q='''select * from snapshot
        where project_id=%s
        and last_snapshot=%s'''
    results=sql.execute(q,(projectId, snapshotId))
    if results:
        return results[0]['id']
    else:
        logging.error('invalid arguments while finding snapshot date')


def get_snapshot_count(projectId):
    q='select count(*) as c from snapshot where project_id=%s'
    return sql.execute(q,(projectId,))[0]['c']

def get_alert_count(projectId):
    q='select count(*) as c from alert where project_id=%s'
    return sql.execute(q,(projectId,))[0]['c']

def switch_dir_to_project_path(projectId):
    path="/Users/nasifimtiaz/Desktop/repos_coverity/" + get_repo_name(projectId)
    os.chdir(path)

if __name__=='__main__':
    a =get_snapshot_date(2,10922) 
    print(type(a))
    




 