'''add snapshots from coverity'''
import sql
import sys
import xml.etree.ElementTree as ET
from datetime import datetime 
from dateutil import parser
import pandas as pd
import numpy as np
import common


def read_data(datfile):
    '''Returns snapshot data from oldest to newest '''

    datalist = common.read_xml_file_to_list_of_dicts(datafile)

    #turn into oldest to newest as the file reads from newet to oldest
    datalist.reverse()
    
    return datalist

def trim_old_data(datalist):
    '''
    See if data from input file already is there in the database.
    If yes, trim that portion and only return the new data that db need to extend to

    Parameter
    ----------
    full data of input file

    Return
    --------
    trimmed data
    id of last snapshot in database
    '''
    #get the project name
    stream = datalist[0]['streamName']

    #get the last snapshot in database
    q = '''select s.date, s.id from snapshot s
        join project p on s.project_id = p.id
        where p.name=%s
        order by date desc
        limit 1;'''
    results=sql.execute(q,(stream,))
    
    if not results:
        return  datalist, 'null'
    
    lastSnapshotDateInDb = results[0]['date']
    lastSnapshotId = results[0]['id']

    for i, data in enumerate(datalist):
        if parser.parse(data['snapshotDate']) > lastSnapshotDateInDb:
            break
    
    return datalist[i:], lastSnapshotId


def add_to_db(datalist, past_snapshot_id):
    projectId= common.get_project_id(datalist[0]['streamName'])
    #we read it from oldest to newset
    for data in datalist:
        data['last_snapshot']=past_snapshot_id
        data['streamName']=projectId
        # for k in data.keys():
        #     if data[k]=="":
        #         data[k]=np.NaN

        past_snapshot_id=data["snapshotId"]
    
    df=pd.DataFrame(datalist)
    df=common.replace_blankString_with_NaN(df)
    column_names_in_db=sql.get_table_columns('snapshot')
    df.columns=column_names_in_db

    sql.load_df('snapshot',df)



if __name__=='__main__':
    #pass xml filename as command line argument
    datafile=sys.argv[1]

    #read data and put it in a list from oldest to newest
    datalist=read_data(datafile)
    
    #trim the portion that is already in database
    datalist, lastSnapshot = trim_old_data(datalist)

    add_to_db(datalist, lastSnapshot)

    
    