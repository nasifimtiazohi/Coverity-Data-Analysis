import sql
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
        raise Exception('project not there in db') 
    elif len(results) >1 :
        logging.error("more than one project with the name %s",project)
    return results[0]['id']

def replace_blankString_with_NaN(df):
    return df.replace(r'^\s*$', np.nan, regex=True)


def get_start_end_date(projectId):
    d={}

    q="select start_date, end_date from project where id=%s"
    results=sql.execute(q,(projectId,))
    if not results:
        return d
    result=results[0]

    start=result['start_date']
    end=result['end_date']
    start=start.strftime('%Y-%m-%d')
    d['start_date']=start
    end=end.strftime('%Y-%m-%d')
    d['end_date']=end

    return d

def get_repo_name(projectId):
    q='select github_url from project where project id=%s'
    results=sql.execute(q,(projectId,))
    return results[0]['github_url']

if __name__=='__main__':
    logging.info("ASD")
    




 