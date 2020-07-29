
select t3.CWE,mc.memory as memoryCWE, t4.memory as memoryAlert from
(select t1.CWE from
(select distinct CWE
from alert
where language in ('C','C++') and CWE is not null) t1
join
(select distinct CWE
from cve) t2
on t1.CWE=t2.CWE) t3
join memory_cwe mc on t3.CWE=mc.CWE
join
(select CWE, avg(memory) as memory from alert
join memory_error me on alert.alert_type_id = me.alert_type_id
group by CWE) as t4 on t4.CWE=t3.CWE;