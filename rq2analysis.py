import pymysql 
import numpy as np
import matplotlib.pyplot as plt
connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)



f= open("rq2_analysis.txt","w")

def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results

def unactionable_alerts_trend():
    projects=['Kodi','Linux','Firefox','Samba','Ovirt-engine']
    for project in projects:
        query='''select last_snapshot_id, count(*) as c
                from alerts a join actionability ac on 
                    ac.alert_id=a.idalerts
                where actionability = 0
                and is_invalid=0
                and status="Fixed"
                and file_deleted is null
                and file_renamed is null
                and stream = "'''+project+'''"
                group by last_snapshot_id
                order by last_snapshot_id asc'''
        results=execute(query)
        x=[]
        y=[]
        i=1
        for item in results:
            x.append(i)
            i+=1
            y.append(item['c'])
        plt.plot(x,y)
    plt.xlabel("the rate of actionable alerts per alert type")
    plt.ylabel("CDF")
    plt.vlines(20,ymin=20,ymax=100)
    plt.legend(projects,loc='center right')
    plt.show()
if __name__ == "__main__":
    unactionable_alerts_trend()