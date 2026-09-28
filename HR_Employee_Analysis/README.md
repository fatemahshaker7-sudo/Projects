# Understanding Employee Turnover Through HR Data Analytics

## Problem Statement

Just over half of the company's employees left between 2018 and 2023, and in 2023 exits outnumbered new hires for the first time. This project analyzes employee, engagement survey data to identify who is leaving, when, and from where, and to recommend actions that improve HR decisions on retention, and hiring.

---

## Executive Summary

**Process.** Three datasets (employee records, engagement surveys, training and development) were loaded with date columns parsed, checked for quality, cleaned, and merged on employee ID. Cleaning included trimming stray whitespace (e.g. `'Production       '`), correcting `EmployeeStatus` for employees who had an exit date but were labeled Active, Future Start, or Leave of Absence, and engineering tenure features from `StartDate` and `ExitDate`. The analysis is descriptive and visual (exploratory data analysis with pandas, matplotlib, and seaborn). No predictive model was deployed.

**Key findings.** 51% of employees (1,533 of 3,000) left. Exits rose every year, from 4 in 2018 to 596 in 2023, and in 2023 they were nearly double hires (596 vs 335), a net loss of 261 employees. The four termination types (involuntary, voluntary, resignation, retirement) each account for about a quarter of exits. People leave early: the median tenure before leaving is about 1.1 years, and among leavers 47% left within one year and 74% within two. Executive Office (79%) and Admin Offices (60%) have the highest attrition rates and peaked in 2021-2022, but by 2023 every department was losing 17-24% of its staff. Production, the largest department, accounts for 172 of the 261 net job losses in 2023. Admin Offices reports the lowest satisfaction (2.51 vs about 3.0-3.1 elsewhere).

**Conclusions and recommendations.** Attrition is broad, early in employees' tenure, and growing, and none of the metrics the company currently collects explains it. The main recommendations are to focus retention efforts on the early years, prioritize Production and Admin Offices, monitor high-exit data and architecture roles, address retention before increasing hiring, and fix data collection (exit interviews with coded reasons, consistent employee status, and validated dates) so attrition can be explained and predicted in the future.

---

## File Directory

```
.
├── README.md
├── data/
│   ├── original/
│   │   ├── employee_data.csv
│   │   ├── employee_engagement_survey_data.csv
│   │   ├── recruitment_data.csv
│   │   └── training_and_development_data.csv
│   └── cleaned/
│       └── cleaned_merged_employee_data.csv
├── code/
│   ├── HR_Employee_Analysis.ipynb
├── presentation/
│   ├── HR_Employee_ppt.pdf
```

---

## Data and Data Dictionary

**Source.** Three related HR datasets of 3,000 records each: employee records, engagement survey responses, training and development records. The employee records cover start dates from August 2018 to August 2023. The data appears to be synthetic. *[Add the link to the dataset source here.]*

### cleaned data (`cleaned_merged_employee_data.csv`)

| Feature | Type | Description |
|---|---|---|
| `EmpID` | int | Unique employee ID (the key used for merging) |
| `FirstName`, `LastName` | str | Employee name (personal data) |
| `StartDate` | date | Date the employee started |
| `ExitDate` | date | Date the employee left (missing for current employees) |
| `Title` | str | Job title (32 unique) |
| `Supervisor` | str | Supervisor's name |
| `ADEmail` | str | Company email (personal data) |
| `BusinessUnit` | str | Business unit code (10 unique) |
| `EmployeeStatus` | str | Status: Active, Future Start, Leave of Absence, Terminated, Terminated for Cause, Voluntarily Terminated (corrected in cleaning; see below) |
| `EmployeeType` | str | Contract, Full-Time, or Part-Time |
| `PayZone` | str | Pay zone A, B, or C |
| `TerminationType` | str | Involuntary, Voluntary, Resignation, Retirement, or `Unk` (employee has not left) |
| `TerminationDescription` | str | Free-text termination reason (filler text with no usable information) |
| `DepartmentType` | str | Department (6 unique), whitespace trimmed |
| `Division` | str | Division (25 unique) |
| `DOB` | date | Date of birth (personal data) |
| `State` | str | State of residence |
| `JobFunctionDescription` | str | Job function (83 unique) |
| `GenderCode` | str | Female or Male |
| `LocationCode` | int | Location code |
| `RaceDesc` | str | Race description |
| `MaritalDesc` | str | Marital status |
| `Performance Score` | str | PIP, Needs Improvement, Fully Meets, or Exceeds |
| `Current Employee Rating` | int | Numeric rating, 1 to 5 |
| `Employee ID` | int | Employee ID (matches `EmpID`) |
| `Survey Date` | date | Date of the survey |
| `Engagement Score` | int | 1 to 5 |
| `Satisfaction Score` | int | 1 to 5 |
| `Work-Life Balance Score` | int | 1 to 5 |
| `Employee ID` | int | Employee ID (matches `EmpID`) |
| `Training Date` | date | Date of training |
| `Training Program Name` | str | Communication Skills, Customer Service, Leadership Development, Project Management, or Technical Skills |
| `Training Type` | str | Internal or External |
| `Training Outcome` | str | Completed, Passed, Failed, or Incomplete |
| `Location` | str | Training location |
| `Trainer` | str | Trainer name |
| `Training Duration(Days)` | int | Length of training, 1 to 5 days |
| `Training Cost` | float | Cost of the training |
| `TenureDays` | `ExitDate` minus `StartDate`, in days (missing for employees who have not left) |
| `TenureYears` | `TenureDays` divided by 365.25, rounded to 2 decimals |
| `TenureCat` | Tenure band: <6 months, 6-12 months, 1-2 years, 2-3 years, 3+ years |
| `ExitYear` | Year extracted from `ExitDate` |
| `EmployeeStatus` (corrected) | Rows labeled Active, Future Start, or Leave of Absence that had an `ExitDate` were relabeled as terminated |
| `DepartmentType` (cleaned) | Trailing whitespace removed (e.g. `'Production       '` became `'Production'`) |

---

## Conclusions and Recommendations

**Conclusions**

- 51% of employees left between 2018 and 2023, and 2023 was the first year with a net headcount loss (-261).
- Exits are spread evenly across the four termination types, so no single type drives the problem.
- Exits happen early: median tenure at exit is about 1.1 years, and 47% of leavers left within one year.
- Attrition began in the Executive and Admin Offices and by 2023 had spread to every department (17-24% of staff). Production carries most of the headcount loss by volume.
- The company cannot currently explain why people leave, because termination descriptions hold no usable reasons and several fields contradict each other.

**Recommendations**

1. **Target the first year** with structured onboarding and check-ins at 30, 90, and 180 days.
2. **Take a company-wide approach to retention** (pay, management practices, career paths), and start with Production.
3. **Investigate Admin Offices**, where low satisfaction coincides with 60% attrition, using stay interviews.
4. **Monitor data and architecture roles and Software Engineering**, reviewing pay against the market as more data arrives.
5. **Fix retention before increasing hiring**, since hiring volume showed no link to exits.
6. **Improve data collection**: structured exit interviews with coded reasons, consistent employee status, a single performance definition, and validated dates.

**Limitations.** The data covers August 2018 to August 2023, so long tenures cannot appear. Several data-quality problems limit the conclusions: 991 "Active" employees had exit dates, 42% of performance ratings contradicted the performance category, 67% of leavers have a training dated after their exit, and 69% of leavers' survey dates fall after they left. Findings show where to look, not what causes attrition.

---

## Areas for Further Research

- Build a predictive attrition-risk model once the data is reliable (tenure, department, role, and pay as inputs).
- Track hires and exits monthly to test whether the 2023 contraction continues.
- Analyze Production, Admin Offices, and the data and architecture roles in more depth, including pay benchmarking and manager-level effects.
- Estimate the cost of turnover and compare attrition with industry benchmarks.
- Collect surveys tied to specific dates and follow up with leavers, so satisfaction and engagement can be linked to exits.
- Link applicants to employees to study hiring quality and early attrition.

---

## Visualizations


| Chart | Insight |
|---|---|
| ![Hires vs Exits](presentation/images/hires_vs_exits.png) | Exits rose every year and passed hires in 2023 |
| ![Exit rate bubble chart](presentation/images/exit_rate_bubble.png) | Exit rate by department and year: highest in Executive and Admin Offices early, then company-wide by 2023 |
| ![Tenure at exit](presentation/images/tenure_at_exit.png) | About half of leavers left within their first year |
| ![Termination types](presentation/images/termination_types.png) | The four termination types are split almost evenly |

---

## Sources

- *[Dataset source and link]*
- pandas documentation: https://pandas.pydata.org/docs/
- matplotlib documentation: https://matplotlib.org/stable/
- seaborn documentation: https://seaborn.pydata.org/
- Kaggle Employee/HR Dataset (All in One): https://www.kaggle.com/datasets/ravindrasinghrana/employeedataset/data
