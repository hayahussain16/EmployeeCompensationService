-- Employee Compensation Service
-- Sample Data

INSERT INTO Department (DepartmentID, DepartmentName, Location)
VALUES
    (1, 'IT', 'Mumbai'),
    (2, 'HR', 'Delhi'),
    (3, 'Finance', 'Bangalore'),
    (4, 'Marketing', 'Pune');


INSERT INTO Employee
    (FirstName, LastName, DepartmentID, Salary, Bonus, HireDate)
VALUES
    ('Haya', 'Hussain', 1, 60000.00, 5000.00, '2024-01-15'),
    ('Aisha', 'Khan', 2, 50000.00, NULL, '2023-06-10'),
    ('Rahul', 'Sharma', 3, 75000.00, 8000.00, '2022-03-20'),
    ('Sara', 'Patel', 1, 65000.00, NULL, '2024-08-01'),
    ('Arjun', 'Mehta', 4, 55000.00, 3000.00, '2023-11-05');