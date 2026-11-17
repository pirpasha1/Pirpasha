"""Office Automation – Payroll & Attendance toolkit.

Core modules (no UI dependency, fully unit-tested):

* :mod:`payroll_app.config`      – settings and attendance status codes
* :mod:`payroll_app.validation`  – issue log used for error checking
* :mod:`payroll_app.importer`    – reads many Excel files into clean tables
* :mod:`payroll_app.payroll`     – daily wage and monthly payment calculations
* :mod:`payroll_app.filters`     – search / filter helpers
* :mod:`payroll_app.reports_excel` – consolidated Excel workbook
* :mod:`payroll_app.reports_pdf`   – individual salary statements & attendance PDF
"""

__version__ = "1.0.0"
