import pymysql
import numpy as np
#open sql connection 
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


TODO=''
f= open("temp.txt","w")
projects=['Linux','Firefox','Samba','Kodi','Ovirt-engine']
def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results

def all_complexity():
        for project in projects:
                #f.write(project+'\n')
                query='''select count(*) as c
                        from actionability_fixed ac
                        join alerts a 
                        on a.idalerts=ac.alert_id
                        where a.stream="'''+project +'''"
                        and a.is_invalid=0
                        and ac.single_fix_commit is not null'''
                fix_commit_tracked=execute(query)[0]['c']
                #f.write("fix commit tracked for alerts: "+str(fix_commit_tracked)+'\n')
                
                query='''select fc.*
                        from alerts a
                        join actionability_fixed ac
                        on a.idalerts=ac.alert_id
                        join fix_complexity fc
                        on fc.alert_id=ac.alert_id
                        and fc.commit_id=ac.single_fix_commit
                        where a.stream="'''+project+'''"
                        and a.status='Fixed'
                        and a.is_invalid=0
                        and ac.single_fix_commit is not null;'''
                results=execute(query)
                files=[]
                net_loc=[]
                net_logical=[]
                in_loc=[]
                in_logical=[]
                for item in results:
                        file_count=float(item['file_count'])/float(item['total_fixed_alerts'])
                        loc_change=float(item['net_loc_change'])/float(item['total_fixed_alerts'])
                        logical_change=float(item['net_logical_change'])/(item['total_fixed_alerts'])
                        files.append(file_count)
                        net_loc.append(loc_change)
                        net_logical.append(logical_change)
                        loc_change=float(item['infile_loc_change'])/float(item['infile_fixed_alerts'])
                        logical_change=float(item['infile_logical_change'])/(item['infile_fixed_alerts'])
                        in_loc.append(loc_change)
                        in_logical.append(logical_change)
                net_function=TODO
                in_function=TODO
                temp=[project,fix_commit_tracked,round(np.median(files),1), round(np.median(net_loc),1),
                round(np.median(net_logical),1), round(np.median(in_loc),1),round(np.median(in_logical),1)]
                f.write('&'.join(str(x) for x in temp)+r'\\'+'\n')

def bug_complexity():
    for project in projects:
        #f.write(project+'\n')
        query='''select count(*) as c
                from actionability_fixed ac
                join alerts a 
                on a.idalerts=ac.alert_id
                where a.stream="'''+project +'''"
                and a.is_invalid=0
                and a.classification='Bug'
                and ac.single_fix_commit is not null'''
        fix_commit_tracked=execute(query)[0]['c']
        #f.write("fix commit tracked for alerts: "+str(fix_commit_tracked)+'\n')
        
        query='''select fc.*
                from alerts a
                join actionability_fixed ac
                on a.idalerts=ac.alert_id
                join fix_complexity fc
                on fc.alert_id=ac.alert_id
                and fc.commit_id=ac.single_fix_commit
                where a.stream="'''+project+'''"
                and a.status='Fixed'
                and a.is_invalid=0
                and a.classification='Bug'
                and ac.single_fix_commit is not null;'''
        results=execute(query)
        files=[]
        net_loc=[]
        net_logical=[]
        in_loc=[]
        in_logical=[]
        for item in results:
                file_count=float(item['file_count'])/float(item['total_fixed_alerts'])
                loc_change=float(item['net_loc_change'])/float(item['total_fixed_alerts'])
                logical_change=float(item['net_logical_change'])/(item['total_fixed_alerts'])
                files.append(file_count)
                net_loc.append(loc_change)
                net_logical.append(logical_change)
                loc_change=float(item['infile_loc_change'])/float(item['infile_fixed_alerts'])
                logical_change=float(item['infile_logical_change'])/(item['infile_fixed_alerts'])
                in_loc.append(loc_change)
                in_logical.append(logical_change)
        net_function=TODO
        in_function=TODO
        temp=[project,fix_commit_tracked,round(np.median(files),1), round(np.median(net_loc),1),
        round(np.median(net_logical),1), round(np.median(in_loc),1),round(np.median(in_logical),1)]
        f.write('&'.join(str(x) for x in temp)+r'\\'+'\n')

def per_type_analysis():
    query='''select b.type, count(*) as c
        from actionability_fixed ac
        join alerts a 
        on a.idalerts=ac.alert_id
        join bug_types b
        on a.bug_type=b.idbug_types
        where a.is_invalid=0
        and ac.single_fix_commit is not null
        group by b.type
        order by count(*) desc
        limit 10'''
    results=execute(query)
    for item in results:
        if item['c']<100:
                break
        typename=item['type']
        fix_commit_tracked=item['c']
        query='''select fc.*
                from alerts a
                join actionability_fixed ac
                on a.idalerts=ac.alert_id
                join fix_complexity fc
                on fc.alert_id=ac.alert_id
                join bug_types b
                on a.bug_type=b.idbug_types
                and fc.commit_id=ac.single_fix_commit
                where b.type="'''+typename+'''"
                and a.status='Fixed'
                and a.is_invalid=0
                and ac.single_fix_commit is not null;'''
        results=execute(query)
        files=[]
        net_loc=[]
        net_logical=[]
        in_loc=[]
        in_logical=[]
        for item in results:
                file_count=float(item['file_count'])/float(item['total_fixed_alerts'])
                loc_change=float(item['net_loc_change'])/float(item['total_fixed_alerts'])
                logical_change=float(item['net_logical_change'])/(item['total_fixed_alerts'])
                files.append(file_count)
                net_loc.append(loc_change)
                net_logical.append(logical_change)
                loc_change=float(item['infile_loc_change'])/float(item['infile_fixed_alerts'])
                logical_change=float(item['infile_logical_change'])/(item['infile_fixed_alerts'])
                in_loc.append(loc_change)
                in_logical.append(logical_change)
        net_function=TODO
        in_function=TODO
        temp=[typename,fix_commit_tracked,round(np.median(files),1), round(np.median(net_loc),1),
        round(np.median(net_logical),1), round(np.median(in_loc),1),round(np.median(in_logical),1)]
        f.write('&'.join(str(x) for x in temp)+r'\\'+'\n')
        

if __name__ == "__main__":
    all_complexity()
    bug_complexity()
    per_type_analysis()