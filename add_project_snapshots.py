'''add snapshots from coverity'''
import common
import sql, numpy as np, pandas as pd, logging
import sys
from datetime import datetime 
from dateutil import parser

def read_data(datafile):
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
    if not datalist:
        logging.warn("no data provided")
        return [], None
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

    i=0
    while i<len(datalist):
        data=datalist[i]
        if parser.parse(data['snapshotDate']) > lastSnapshotDateInDb:
            break
        i+=1
    
    return datalist[i:], lastSnapshotId


def add_to_db(datalist, past_snapshot_id):
    if not datalist:
        return 
    projectId= common.get_project_id(datalist[0]['streamName'])
    
    #snapshotCount prior to insertion
    before=common.get_snapshot_count(projectId)

    #we read it from oldest to newset
    for data in datalist:
        data['last_snapshot']=past_snapshot_id
        data['streamName']=projectId
        past_snapshot_id=data["snapshotId"]
    
    df=pd.DataFrame(datalist)
    df=common.replace_blankString_with_NaN(df)
    column_names_in_db=sql.get_table_columns('snapshot')
    df.columns=column_names_in_db

    sql.load_df('snapshot',df)

    #snapshotCount after insertion
    after=common.get_snapshot_count(projectId)

    logging.info('%s new snapshots inserted',after-before)

def update_end_date():
    q='''update project p
        set end_date=(select max(date) from snapshot s where project_id=p.id);'''
    sql.execute(q)


def add_snapshots(datafile):
    #read data and put it in a list from oldest to newest
    datalist=read_data(datafile)
    
    #trim the portion that is already in database
    datalist, lastSnapshot = trim_old_data(datalist)

    logging.info("new data found: %s", len(datalist))
    add_to_db(datalist, lastSnapshot)

    update_end_date()

if __name__=='__main__':
    #pass xml filename as command line argument
    try:
        datafile=sys.argv[1]
    except:
        logging.error("no input data provided as cli argument")

    add_snapshots(datafile)



    
    