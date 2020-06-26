import sql
import csv

with open('my_classification.csv','r') as file:
    csv_reader=csv.reader(file)
    for row in csv_reader:
        id=row[0]
        type=row[1]
        classification=row[4]
        
        if id=='Id':
            continue #header
        id=int(id)
        
        q='select type from alert_type where id=%s'
        assert type==sql.execute(q,(id,))[0]['type']
        
        classification=classification.lower()
        if 'yes' == classification:
            classification =1
            q='update memory_error set memory=1 where alert_type_id=%s'
            sql.execute(q,(id,))
        