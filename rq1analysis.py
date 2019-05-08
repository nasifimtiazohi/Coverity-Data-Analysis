import pymysql
import numpy as np
import matplotlib.pyplot as plt

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

def intro_cdf_analysis():
    projects=['Kodi','Linux','Firefox','Samba','Ovirt-engine']
    for project in projects:
        query='select count(*) as c from alerts where is_invalid=0 and stream="'+project+'"'
        total=execute(query)[0]['c']

        query='select count(distinct bug_type) as c from alerts where is_invalid=0 and stream="'+project+'"'
        bug=execute(query)[0]['c']

        query='''select bug_type,count(*) as c
                from alerts
                where is_invalid=0
                and stream="'''+project+'''" 
                group by bug_type
                order by count(*) desc;'''
        results=execute(query)
        ind=[]
        cum=[]
        prcnt=[]
        i=1
        for item in results:
            cum.append(item['c'])
            ind.append(i)
            i+=1
        cum=np.cumsum(cum)

        old=0
        i=1
        for c in cum:
            temp=(float(c)/total)*100
            prcnt.append(temp)
            if old <70 and temp>=70:
                print((float(i)/bug)*100)
            elif old<80 and temp>=80:
                print((float(i)/bug)*100)
            elif old<90 and temp>=90:
                print((float(i)/bug)*100)
            old=temp
            i+=1
        for i in range(0,len(ind)):
            ind[i]=(float(i)/bug)*100
        plt.plot(ind,prcnt)
    plt.xlabel("the rate of occurrence per alert type")
    plt.ylabel("CDF")
    plt.vlines(20,ymin=20,ymax=100)
    plt.legend(projects,loc='center right')
    plt.show()


def actionable_cdf_analysis():
    projects=['Kodi','Linux','Firefox','Samba','ovirt-engine']
    for project in projects:
        query='select count(*) as c from alerts a join actionability ac on ac.alert_id=a.idalerts where is_invalid=0 and actionability=1 and stream="'+project+'"'
        total=execute(query)[0]['c']

        query='select count(distinct bug_type) as c from alerts a join actionability ac on ac.alert_id=a.idalerts where is_invalid=0 and actionability=1 and stream="'+project+'"'
        bug=execute(query)[0]['c']

        query='''select bug_type,count(*) as c
                from alerts a
                join actionability ac on ac.alert_id=a.idalerts
                where is_invalid=0
                and actionability=1
                and stream="'''+project+'''" 
                group by bug_type
                order by count(*) desc;'''
        results=execute(query)
        ind=[]
        cum=[]
        prcnt=[]
        i=1
        for item in results:
            cum.append(item['c'])
            ind.append(i)
            i+=1
        cum=np.cumsum(cum)

        old=0
        i=1
        for c in cum:
            temp=(float(c)/total)*100
            prcnt.append(temp)
            if old <70 and temp>=70:
                print((float(i)/bug)*100)
            elif old<80 and temp>=80:
                print((float(i)/bug)*100)
            elif old<90 and temp>=90:
                print((float(i)/bug)*100)
            old=temp
            i+=1
        
        plt.plot(ind,prcnt)
    plt.xlabel("the rate of occurrence of each alert type when actionable (sorted)")
    plt.ylabel("CDF")
    plt.vlines(20,ymin=70,ymax=100)
    plt.show()

            
def alert_type_analysis_C():
    #in this text file, we will write in latex table format
    csv=open("alert_type_analysis_C.csv","w")

    d={}
    new_d={}
    query='''select distinct b.idbug_types,b.type,b.impact
            from bug_types b
            join alerts a
            on a.bug_type=b.idbug_types
            where a.stream!="ovirt-engine"'''
    results=execute(query)
    for item in results:
        d[item['type']]={'id':item['idbug_types']}
        d[item['type']]['name']=item['type']
        d[item['type']]['severity']=item['impact']
    
    projects=['Kodi','Linux','Firefox','Samba']

    alert_in_all_projects=0
    for k in d.keys():
        #initialize all blank lists here
        intro=[]
        actionability=[]
        lifespan=[]
        for project in projects:
            #get the occurrence count
            query='select count(*) as c from alerts where is_invalid=0 and bug_type='+str(d[k]['id'])+' and stream="'+project+'"'
            c=execute(query)[0]['c']
            intro.append(c)

            #get the actionability count
            query='select count(*) as c from alerts a join actionability ac on \
                ac.alert_id=a.idalerts where actionability=1 and is_invalid=0 and status="Fixed" and  bug_type='+str(d[k]['id'])+' and stream="'+project+'"'
            ac=execute(query)[0]['c']
            if c==0:
                ac=0
            else:
                ac= (float(ac)/c)*100
            actionability.append(ac)

            #get the median lifespan of this bug type for this project
            query='''select datediff(s.date,a.first_detected) as diff 
                from alerts a join actionability ac on 
                ac.alert_id=a.idalerts 
                join snapshots s on a.last_snapshot_id=s.idsnapshots
                where actionability=1 and is_invalid=0 and status="Fixed" and  bug_type='''+str(d[k]['id'])+' and a.stream="'+project+'"'
            templist=execute(query)
            temp=[]
            for tl in templist:
                temp.append(tl['diff'])
            if len(temp)>0:
                lifespan.append(np.median(temp))
        #intro.sort()
        if 0 not in actionability:
            print(k)
            alert_in_all_projects+=1

        if 0 not in intro:
            d[k]['introlist']=intro
            d[k]['intro']=np.median(intro)

            d[k]['actlist']=actionability
            d[k]['act']=np.median(actionability)

            d[k]['lifespanlist']=lifespan
            d[k]['lifespan']=np.median(lifespan)
            new_d[k]=d[k]
            temp=[k,d[k]['introlist'],d[k]['intro'],d[k]['actlist'],d[k]['act'],d[k]['lifespanlist'],d[k]['lifespan']]
            csv.write(','.join(str(x) for x in temp)+'\n')
    csv.close()
    print(new_d)
    #sort through median introduction
    sorted_d= sorted(new_d.items(), key=lambda kv: kv[1]['intro'],reverse=True)

    print("hey hello",alert_in_all_projects)

    f=open('csv.txt','w')
    f.write("Alert Type & Median Occurrence & Median Actionability\n")
    for temp in sorted_d:
        if temp[1]['intro'] < 100 :
            break
        t=[temp[1]['name'],temp[1]['severity'],round(temp[1]['intro'],1),round(temp[1]['act'],1),round(temp[1]['lifespan'],1)]
        f.write('&'.join(str(x) for x in t)+r'\\'+'\n')
    f.close()
        
        



def alert_type_analysis_Java():
    #in this text file, we will write in latex table format
    csv=open("alert_type_analysis_C.csv","w")

    d={}
    new_d={}
    query='''select distinct b.idbug_types,b.type,b.impact
            from bug_types b
            join alerts a
            on a.bug_type=b.idbug_types
            where a.stream="Ovirt-engine"'''
    results=execute(query)
    for item in results:
        d[item['type']]={'id':item['idbug_types']}
        d[item['type']]['name']=item['type']
        d[item['type']]['severity']=item['impact']
    
    projects=['Ovirt-engine']

    alert_in_all_projects=0
    for k in d.keys():
        #initialize all blank lists here
        intro=[]
        actionability=[]
        lifespan=[]
        for project in projects:
            #get the occurrence count
            query='select count(*) as c from alerts where is_invalid=0 and bug_type='+str(d[k]['id'])+' and stream="'+project+'"'
            c=execute(query)[0]['c']
            intro.append(c)

            #get the actionability count
            query='select count(*) as c from alerts a join actionability ac on \
                ac.alert_id=a.idalerts where actionability=1 and is_invalid=0 and status="Fixed" and  bug_type='+str(d[k]['id'])+' and stream="'+project+'"'
            ac=execute(query)[0]['c']
            if c==0:
                ac=0
            else:
                ac= (float(ac)/c)*100
            actionability.append(ac)

            #get the median lifespan of this bug type for this project
            query='''select datediff(s.date,a.first_detected) as diff 
                from alerts a join actionability ac on 
                ac.alert_id=a.idalerts 
                join snapshots s on a.last_snapshot_id=s.idsnapshots
                where actionability=1 and is_invalid=0 and status="Fixed" and  bug_type='''+str(d[k]['id'])+' and a.stream="'+project+'"'
            templist=execute(query)
            temp=[]
            for tl in templist:
                temp.append(tl['diff'])
            if len(temp)>0:
                lifespan.append(np.median(temp))
        #intro.sort()
        if 0 not in actionability:
            print(k)
            alert_in_all_projects+=1

        if 0 not in intro:
            d[k]['introlist']=intro
            d[k]['intro']=np.median(intro)

            d[k]['actlist']=actionability
            d[k]['act']=np.median(actionability)

            d[k]['lifespanlist']=lifespan
            d[k]['lifespan']=np.median(lifespan)
            new_d[k]=d[k]
            temp=[k,d[k]['introlist'],d[k]['intro'],d[k]['actlist'],d[k]['act'],d[k]['lifespanlist'],d[k]['lifespan']]
            csv.write(','.join(str(x) for x in temp)+'\n')
    csv.close()
    print(new_d)
    #sort through median introduction
    sorted_d= sorted(new_d.items(), key=lambda kv: kv[1]['intro'],reverse=True)

    print("hey hello",alert_in_all_projects)

    f=open('csv.txt','w')
    # f.write("Alert Type & Median Occurrence & Median Actionability\n")
    for temp in sorted_d:
        if temp[1]['intro'] < 100 :
            break
        t=[temp[1]['name'],temp[1]['severity'],round(temp[1]['intro'],1),round(temp[1]['act'],1),round(temp[1]['lifespan'],1)]
        f.write('&'.join(str(x) for x in t)+r'\\'+'\n')
    f.close()
def act_cdf_analysis():
    projects=['Kodi','Linux','Firefox','Samba','Ovirt-engine']
    for project in projects:
        query='''select count(*) as c from alerts a
                join actionability ac
                on a.idalerts=ac.alert_id
                where is_invalid=0 
                and actionability=1
                and stream="'''+project+'"'
        total=execute(query)[0]['c']

        query='''select count(distinct bug_type) as c from alerts a
            where is_invalid=0 
            and stream="'''+project+'"'
        bug=execute(query)[0]['c']
        
        query='''select bug_type,count(*) as c
                from alerts a
                join actionability ac
                on a.idalerts=ac.alert_id
                where is_invalid=0
                and actionability=1
                and stream="'''+project+'''" 
                group by bug_type
                order by count(*) desc;'''
        results=execute(query)
        ind=[]
        cum=[]
        prcnt=[]
        i=1
        for item in results:
            cum.append(item['c'])
            ind.append(i)
            i+=1
        cum=np.cumsum(cum)

        old=0
        i=1
        for c in cum:
            temp=(float(c)/total)*100
            prcnt.append(temp)
            if old <70 and temp>=70:
                print((float(i)/bug)*100)
            elif old<80 and temp>=80:
                print((float(i)/bug)*100)
            elif old<90 and temp>=90:
                print((float(i)/bug)*100)
            old=temp
            i+=1
        for i in range(0,len(ind)):
            ind[i]=(float(i)/bug)*100
        plt.plot(ind,prcnt)
    plt.xlabel("the rate of actionable alerts per alert type")
    plt.ylabel("CDF")
    plt.vlines(20,ymin=20,ymax=100)
    plt.legend(projects,loc='center right')
    plt.show()
if __name__ == "__main__":
    alert_type_analysis_Java()
    #intro_cdf_analysis()
    #act_cdf_analysis()




