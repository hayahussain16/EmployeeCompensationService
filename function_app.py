import azure.functions as func
import logging
import os
import pyodbc
import json

app = func.FunctionApp()


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    connection_string = os.environ["SQL_CONNECTION_STRING"]
    return pyodbc.connect(connection_string)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def employee_to_dict(row):
    return {
        "EmployeeID": row.EmployeeID,
        "FirstName": row.FirstName,
        "LastName": row.LastName,
        "DepartmentID": row.DepartmentID,
        "Salary": float(row.Salary),
        "Bonus": float(row.Bonus) if row.Bonus is not None else None,
        "HireDate": str(row.HireDate) if row.HireDate is not None else None
    }


# =========================================================
# PART A - CRUD
# =========================================================

# ---------------------------------------------------------
# 1. Create Employee
# ---------------------------------------------------------

@app.route(
    route="employees",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def create_employee(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        # Read JSON body
        try:
            data = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({
                    "error": "Request body must contain valid JSON."
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Required fields
        required_fields = [
            "FirstName",
            "LastName",
            "DepartmentID",
            "Salary"
        ]

        for field in required_fields:
            if field not in data or data[field] is None:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Missing required field: {field}"
                    }),
                    status_code=400,
                    mimetype="application/json"
                )

        first_name = data["FirstName"]
        last_name = data["LastName"]
        department_id = data["DepartmentID"]
        salary = data["Salary"]
        bonus = data.get("Bonus")
        hire_date = data.get("HireDate")

        # Basic validation
        if not isinstance(first_name, str) or not first_name.strip():
            return func.HttpResponse(
                json.dumps({
                    "error": "FirstName must be a non-empty string."
                }),
                status_code=400,
                mimetype="application/json"
            )

        if not isinstance(last_name, str) or not last_name.strip():
            return func.HttpResponse(
                json.dumps({
                    "error": "LastName must be a non-empty string."
                }),
                status_code=400,
                mimetype="application/json"
            )

        try:
            department_id = int(department_id)
            salary = float(salary)

            if bonus is not None:
                bonus = float(bonus)

        except (TypeError, ValueError):
            return func.HttpResponse(
                json.dumps({
                    "error": "DepartmentID, Salary, and Bonus must be numeric."
                }),
                status_code=400,
                mimetype="application/json"
            )

        if salary < 0:
            return func.HttpResponse(
                json.dumps({
                    "error": "Salary cannot be negative."
                }),
                status_code=400,
                mimetype="application/json"
            )

        if bonus is not None and bonus < 0:
            return func.HttpResponse(
                json.dumps({
                    "error": "Bonus cannot be negative."
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check department exists
        cursor.execute(
            """
            SELECT DepartmentID
            FROM Department
            WHERE DepartmentID = ?
            """,
            department_id
        )

        if cursor.fetchone() is None:
            return func.HttpResponse(
                json.dumps({
                    "error": "Department does not exist."
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Insert employee
        cursor.execute(
            """
            INSERT INTO Employee
            (FirstName, LastName, DepartmentID, Salary, Bonus, HireDate)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            first_name.strip(),
            last_name.strip(),
            department_id,
            salary,
            bonus,
            hire_date
        )

        conn.commit()

        return func.HttpResponse(
            json.dumps({
                "message": "Employee created successfully."
            }),
            status_code=201,
            mimetype="application/json"
        )

    except Exception:
        logging.exception("Error creating employee")

        if conn is not None:
            conn.rollback()

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to create employee."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# 2. Get Employee by ID
# ---------------------------------------------------------

@app.route(
    route="employees/{employee_id}",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def get_employee(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        employee_id = req.route_params.get("employee_id")

        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return func.HttpResponse(
                json.dumps({
                    "error": "Employee ID must be a valid integer."
                }),
                status_code=400,
                mimetype="application/json"
            )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT EmployeeID,
                   FirstName,
                   LastName,
                   DepartmentID,
                   Salary,
                   Bonus,
                   HireDate
            FROM Employee
            WHERE EmployeeID = ?
            """,
            employee_id
        )

        row = cursor.fetchone()

        if row is None:
            return func.HttpResponse(
                json.dumps({
                    "error": "Employee not found."
                }),
                status_code=404,
                mimetype="application/json"
            )

        employee = employee_to_dict(row)

        return func.HttpResponse(
            json.dumps(employee),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception("Error retrieving employee")

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to retrieve employee."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# 3. Get All Employees
# Optional filter:
# /api/employees?department_id=1
# ---------------------------------------------------------

@app.route(
    route="employees",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def get_employees(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        department_id = req.params.get("department_id")

        conn = get_db_connection()
        cursor = conn.cursor()

        if department_id:

            try:
                department_id = int(department_id)
            except ValueError:
                return func.HttpResponse(
                    json.dumps({
                        "error": "department_id must be a valid integer."
                    }),
                    status_code=400,
                    mimetype="application/json"
                )

            cursor.execute(
                """
                SELECT EmployeeID,
                       FirstName,
                       LastName,
                       DepartmentID,
                       Salary,
                       Bonus,
                       HireDate
                FROM Employee
                WHERE DepartmentID = ?
                """,
                department_id
            )

        else:

            cursor.execute(
                """
                SELECT EmployeeID,
                       FirstName,
                       LastName,
                       DepartmentID,
                       Salary,
                       Bonus,
                       HireDate
                FROM Employee
                """
            )

        rows = cursor.fetchall()

        employees = []

        for row in rows:
            employees.append(employee_to_dict(row))

        return func.HttpResponse(
            json.dumps(employees),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception("Error retrieving employees")

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to retrieve employees."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# 4. Update Employee
# ---------------------------------------------------------

@app.route(
    route="employees/{employee_id}",
    methods=["PUT"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def update_employee(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        employee_id = req.route_params.get("employee_id")

        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return func.HttpResponse(
                json.dumps({
                    "error": "Employee ID must be a valid integer."
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Read JSON
        try:
            data = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({
                    "error": "Request body must contain valid JSON."
                }),
                status_code=400,
                mimetype="application/json"
            )

        # PUT replaces the employee details,
        # therefore these fields are required.
        required_fields = [
            "FirstName",
            "LastName",
            "DepartmentID",
            "Salary"
        ]

        for field in required_fields:
            if field not in data or data[field] is None:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Missing required field: {field}"
                    }),
                    status_code=400,
                    mimetype="application/json"
                )

        first_name = data["FirstName"]
        last_name = data["LastName"]
        department_id = data["DepartmentID"]
        salary = data["Salary"]
        bonus = data.get("Bonus")
        hire_date = data.get("HireDate")

        if not isinstance(first_name, str) or not first_name.strip():
            return func.HttpResponse(
                json.dumps({
                    "error": "FirstName must be a non-empty string."
                }),
                status_code=400,
                mimetype="application/json"
            )

        if not isinstance(last_name, str) or not last_name.strip():
            return func.HttpResponse(
                json.dumps({
                    "error": "LastName must be a non-empty string."
                }),
                status_code=400,
                mimetype="application/json"
            )

        try:
            department_id = int(department_id)
            salary = float(salary)

            if bonus is not None:
                bonus = float(bonus)

        except (TypeError, ValueError):
            return func.HttpResponse(
                json.dumps({
                    "error": "DepartmentID, Salary, and Bonus must be numeric."
                }),
                status_code=400,
                mimetype="application/json"
            )

        if salary < 0:
            return func.HttpResponse(
                json.dumps({
                    "error": "Salary cannot be negative."
                }),
                status_code=400,
                mimetype="application/json"
            )

        if bonus is not None and bonus < 0:
            return func.HttpResponse(
                json.dumps({
                    "error": "Bonus cannot be negative."
                }),
                status_code=400,
                mimetype="application/json"
            )

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check employee exists
        cursor.execute(
            """
            SELECT EmployeeID
            FROM Employee
            WHERE EmployeeID = ?
            """,
            employee_id
        )

        if cursor.fetchone() is None:
            return func.HttpResponse(
                json.dumps({
                    "error": "Employee not found."
                }),
                status_code=404,
                mimetype="application/json"
            )

        # Check department exists
        cursor.execute(
            """
            SELECT DepartmentID
            FROM Department
            WHERE DepartmentID = ?
            """,
            department_id
        )

        if cursor.fetchone() is None:
            return func.HttpResponse(
                json.dumps({
                    "error": "Department does not exist."
                }),
                status_code=400,
                mimetype="application/json"
            )

        cursor.execute(
            """
            UPDATE Employee
            SET FirstName = ?,
                LastName = ?,
                DepartmentID = ?,
                Salary = ?,
                Bonus = ?,
                HireDate = ?
            WHERE EmployeeID = ?
            """,
            first_name.strip(),
            last_name.strip(),
            department_id,
            salary,
            bonus,
            hire_date,
            employee_id
        )

        conn.commit()

        return func.HttpResponse(
            json.dumps({
                "message": "Employee updated successfully."
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception("Error updating employee")

        if conn is not None:
            conn.rollback()

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to update employee."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# 5. Delete Employee
# ---------------------------------------------------------

@app.route(
    route="employees/{employee_id}",
    methods=["DELETE"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def delete_employee(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        employee_id = req.route_params.get("employee_id")

        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return func.HttpResponse(
                json.dumps({
                    "error": "Employee ID must be a valid integer."
                }),
                status_code=400,
                mimetype="application/json"
            )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM Employee
            WHERE EmployeeID = ?
            """,
            employee_id
        )

        if cursor.rowcount == 0:
            return func.HttpResponse(
                json.dumps({
                    "error": "Employee not found."
                }),
                status_code=404,
                mimetype="application/json"
            )

        conn.commit()

        return func.HttpResponse(
            json.dumps({
                "message": "Employee deleted successfully."
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception("Error deleting employee")

        if conn is not None:
            conn.rollback()

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to delete employee."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# =========================================================
# PART B - COMPENSATION REPORTING
# =========================================================

# ---------------------------------------------------------
# Report 1: Total Bonus Paid
# ---------------------------------------------------------

@app.route(
    route="reports/total-bonus",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def total_bonus(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COALESCE(SUM(Bonus), 0) AS TotalBonus
            FROM Employee
            """
        )

        row = cursor.fetchone()

        result = {
            "TotalBonus": float(row.TotalBonus)
        }

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception("Error calculating total bonus")

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to calculate total bonus."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# Report 2: Employees Who Have Never Received a Bonus
# ---------------------------------------------------------

@app.route(
    route="reports/no-bonus",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def employees_with_no_bonus(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT EmployeeID,
                   FirstName,
                   LastName,
                   DepartmentID,
                   Salary,
                   Bonus,
                   HireDate
            FROM Employee
            WHERE Bonus IS NULL
            """
        )

        rows = cursor.fetchall()

        employees = []

        for row in rows:
            employees.append(employee_to_dict(row))

        return func.HttpResponse(
            json.dumps(employees),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception(
            "Error retrieving employees with no bonus"
        )

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to retrieve employees with no bonus."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# Report 3: Bonus as Percentage of Salary
# ---------------------------------------------------------

@app.route(
    route="reports/bonus-percentage",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def bonus_percentage(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                EmployeeID,
                FirstName,
                LastName,
                Salary,
                Bonus,
                ROUND((Bonus / Salary) * 100, 2)
                    AS BonusPercentage
            FROM Employee
            WHERE Bonus IS NOT NULL
              AND Salary > 0
            """
        )

        rows = cursor.fetchall()

        employees = []

        for row in rows:
            employees.append({
                "EmployeeID": row.EmployeeID,
                "FirstName": row.FirstName,
                "LastName": row.LastName,
                "Salary": float(row.Salary),
                "Bonus": float(row.Bonus),
                "BonusPercentage": float(row.BonusPercentage)
            })

        return func.HttpResponse(
            json.dumps(employees),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception(
            "Error calculating bonus percentage"
        )

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to calculate bonus percentage."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# Report 4:
# Departments Where Total Bonus Exceeds
# Department Average Salary
# ---------------------------------------------------------

@app.route(
    route="reports/departments-bonus-exceeds-average",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def departments_bonus_exceeds_average(
    req: func.HttpRequest
) -> func.HttpResponse:

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                d.DepartmentID,
                d.DepartmentName,
                SUM(COALESCE(e.Bonus, 0))
                    AS TotalBonus,
                AVG(e.Salary)
                    AS AverageSalary
            FROM Department d
            INNER JOIN Employee e
                ON d.DepartmentID = e.DepartmentID
            GROUP BY
                d.DepartmentID,
                d.DepartmentName
            HAVING
                SUM(COALESCE(e.Bonus, 0))
                > AVG(e.Salary)
            """
        )

        rows = cursor.fetchall()

        departments = []

        for row in rows:
            departments.append({
                "DepartmentID": row.DepartmentID,
                "DepartmentName": row.DepartmentName,
                "TotalBonus": float(row.TotalBonus),
                "AverageSalary": float(row.AverageSalary)
            })

        return func.HttpResponse(
            json.dumps(departments),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception(
            "Error finding departments where total bonus "
            "exceeds average salary"
        )

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to generate department compensation report."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# Report 5:
# Employees Ranked by Bonus Amount
# No-bonus employees ranked last
# ---------------------------------------------------------

@app.route(
    route="reports/bonus-ranking",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def bonus_ranking(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                EmployeeID,
                FirstName,
                LastName,
                DepartmentID,
                Salary,
                Bonus,
                HireDate
            FROM Employee
            ORDER BY
                CASE
                    WHEN Bonus IS NULL THEN 1
                    ELSE 0
                END,
                Bonus DESC,
                EmployeeID ASC
            """
        )

        rows = cursor.fetchall()

        employees = []

        rank = 1

        for row in rows:
            employees.append({
                "Rank": rank,
                "EmployeeID": row.EmployeeID,
                "FirstName": row.FirstName,
                "LastName": row.LastName,
                "DepartmentID": row.DepartmentID,
                "Salary": float(row.Salary),
                "Bonus": (
                    float(row.Bonus)
                    if row.Bonus is not None
                    else None
                ),
                "HireDate": (
                    str(row.HireDate)
                    if row.HireDate is not None
                    else None
                )
            })

            rank += 1

        return func.HttpResponse(
            json.dumps(employees),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception(
            "Error ranking employees by bonus"
        )

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to generate bonus ranking."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------
# Report 6:
# Highest Base Salary and Highest Total Compensation
# ---------------------------------------------------------

@app.route(
    route="reports/highest-compensation",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS
)
def highest_compensation(req: func.HttpRequest) -> func.HttpResponse:

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Highest base salary
        cursor.execute(
            """
            SELECT TOP 1
                EmployeeID,
                FirstName,
                LastName,
                Salary,
                Bonus
            FROM Employee
            ORDER BY
                Salary DESC,
                EmployeeID ASC
            """
        )

        highest_salary_row = cursor.fetchone()

        # Highest total compensation
        cursor.execute(
            """
            SELECT TOP 1
                EmployeeID,
                FirstName,
                LastName,
                Salary,
                Bonus,
                Salary + COALESCE(Bonus, 0)
                    AS TotalCompensation
            FROM Employee
            ORDER BY
                Salary + COALESCE(Bonus, 0) DESC,
                EmployeeID ASC
            """
        )

        highest_total_row = cursor.fetchone()

        if (
            highest_salary_row is None
            or highest_total_row is None
        ):
            return func.HttpResponse(
                json.dumps({
                    "error": "No employees found."
                }),
                status_code=404,
                mimetype="application/json"
            )

        highest_salary_employee = {
            "EmployeeID": highest_salary_row.EmployeeID,
            "FirstName": highest_salary_row.FirstName,
            "LastName": highest_salary_row.LastName,
            "Salary": float(highest_salary_row.Salary),
            "Bonus": (
                float(highest_salary_row.Bonus)
                if highest_salary_row.Bonus is not None
                else None
            )
        }

        highest_total_employee = {
            "EmployeeID": highest_total_row.EmployeeID,
            "FirstName": highest_total_row.FirstName,
            "LastName": highest_total_row.LastName,
            "Salary": float(highest_total_row.Salary),
            "Bonus": (
                float(highest_total_row.Bonus)
                if highest_total_row.Bonus is not None
                else None
            ),
            "TotalCompensation": float(
                highest_total_row.TotalCompensation
            )
        }

        same_person = (
            highest_salary_row.EmployeeID
            == highest_total_row.EmployeeID
        )

        result = {
            "HighestBaseSalary": highest_salary_employee,
            "HighestTotalCompensation": highest_total_employee,
            "SamePerson": same_person
        }

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )

    except Exception:
        logging.exception(
            "Error finding highest salary and compensation"
        )

        return func.HttpResponse(
            json.dumps({
                "error": "Failed to generate highest compensation report."
            }),
            status_code=500,
            mimetype="application/json"
        )

    finally:
        if conn is not None:
            conn.close()