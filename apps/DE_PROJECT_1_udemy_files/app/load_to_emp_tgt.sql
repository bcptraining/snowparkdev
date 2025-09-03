MERGE INTO employee_tgt USING (select distinct * from employee ) employee
    ON employee_tgt.first_name = employee.first_name
    and employee_tgt.last_name = employee.last_name
    WHEN MATCHED THEN 
        UPDATE SET employee_tgt.email = employee.email,
        employee_tgt.address = employee.address,
        employee_tgt.city = employee.city,
        employee_tgt.doj = employee.doj
    WHEN NOT MATCHED THEN 
        INSERT (first_name, last_name,email,address,city,doj) 
        VALUES (employee.first_name,employee.last_name,employee.email,employee.address,
        employee.city,employee.doj);