#spearman correlation with fix complexity and severity?
import pymysql 
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stat
from scipy.stats import mannwhitneyu
projects=['Linux','Firefox','Samba','Kodi','Ovirt-engine']
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results
f=open('temp.txt','w')
def fix_complexity():
    for project in projects:
        query='''select fc.*, datediff(s.date,a.first_detected) as diff
                from alerts a
                join snapshots s
                on a.last_snapshot_id = s.idsnapshots
                join fix_complexity fc
                on a.idalerts=fc.alert_id
                where a.is_invalid=0
                and a.status="Fixed"
                and a.stream="'''+project+'"'
        results=execute(query)

        lifespan=[]
        complexity=[]

        for item in results:
            if item['diff'] < 0:
                continue
            lifespan.append(item['diff'])
            complexity.append(float(item['infile_loc_change'])/item['infile_fixed_alerts'])
        print(stat.spearmanr(complexity,lifespan))
def severity():
    for project in projects:
        query='''select b.impact, datediff(s.date,a.first_detected) as diff
                from alerts a
                join snapshots s
                on a.last_snapshot_id = s.idsnapshots
                join bug_types b
                on a.bug_type=b.idbug_types
                join actionability ac
                on a.idalerts=ac.alert_id
                where a.is_invalid=0
                and a.status="Fixed"
                and ac.actionability=1
                and a.stream="'''+project+'"'
        results=execute(query)

        lifespan=[]
        severity=[]
        d={}
        d['High']=[]
        d['Low']=[]
        d['Medium']=[]
        for item in results:
            if item['diff'] < 0:
                continue
            lifespan.append(item['diff'])
            if item['impact']=='Low':
                severity.append(1)
                d[item['impact']].append(item['diff'])
            elif item['impact']=='Medium':
                severity.append(2)
                d[item['impact']].append(item['diff'])
            elif item['impact']=='High':
                severity.append(3)
                d[item['impact']].append(item['diff'])
            else:
                print(item)
        
        levels=['Low','Medium','High']
        print(stat.spearmanr(severity,lifespan))
        print(project,np.median(d['High']),np.median(d['Medium']),np.median(d['Low']))
        print(mannwhitneyu(d['High'],d['Medium']))
        print(mannwhitneyu(d['Medium'],d['Low']))
        # print(np.median(high),np.median(medium))
        # print(mannwhitneyu(np.array(high),np.array(medium)))
        sp=stat.spearmanr(severity,lifespan)
        if sp[1] < .05:
            f.write(project+'\\textsuperscript{*}&')
        else:
            f.write(project+'&')
        coeff=round(sp[0],2)
        temp=[coeff,np.median(d['High']),np.median(d['Medium']),np.median(d['Low'])]
        f.write('&'.join(str(x) for x in temp))
        f.write(r'\\'+'\n')

if __name__ == "__main__":
    fix_complexity()
