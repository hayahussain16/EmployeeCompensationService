# Employee Compensation Service

A backend service built using Azure Functions, Python, and SQL Server to manage employee and department records and generate compensation reports.

## Technology Stack

- Python
- Azure Functions
- SQL Server
- pyodbc
- Azure Functions Core Tools
- Visual Studio Code

## Architecture

The application follows a simple API-based architecture:

Client
   ↓
Azure Function HTTP API
   ↓
SQL Server Database

All employee and compensation operations go through the Functions layer. Clients do not access the database directly.

## Database

The database contains two tables:

### Department

- DepartmentID - Primary Key
- DepartmentName
- Location

### Employee

- EmployeeID - Primary Key
- FirstName
- LastName
- DepartmentID - Foreign Key
- Salary
- Bonus
- HireDate

The Employee table has a many-to-one relationship with Department.

A NULL Bonus represents an employee who has not received a bonus.

## API Endpoints

### Employee CRUD

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/employees` | Create employee |
| GET | `/api/employees/{employee_id}` | Get employee by ID |
| GET | `/api/employees` | Get all employees |
| GET | `/api/employees?department_id=1` | Filter employees by department |
| PUT | `/api/employees/{employee_id}` | Update employee |
| DELETE | `/api/employees/{employee_id}` | Delete employee |

### Compensation Reports

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/reports/total-bonus` | Total bonus paid |
| GET | `/api/reports/no-bonus` | Employees with no bonus |
| GET | `/api/reports/bonus-percentage` | Bonus as percentage of salary |
| GET | `/api/reports/departments-bonus-exceeds-average` | Departments where total bonus exceeds average salary |
| GET | `/api/reports/bonus-ranking` | Employees ranked by bonus |
| GET | `/api/reports/highest-compensation` | Highest salary and highest total compensation |

## Setup

### 1. Install Python

Install Python 3.x and verify:

```powershell
python --version