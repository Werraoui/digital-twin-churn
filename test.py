
""""from src.agents.data_agent.ingest import load_telco
from src.agents.data_agent.clean import clean_telco

raw = load_telco()
telco = clean_telco(raw)
# telco: 7043 rows, TotalCharges float, categories still text

from src.agents.data_agent.ingest import load_telco, load_online_retail_ii, load_support_tickets
from src.agents.data_agent.clean import (
    clean_telco,
    clean_retail,
    filter_retail_purchases,
    clean_support_tickets,
)
telco = clean_telco(load_telco())
retail = clean_retail(load_online_retail_ii())          # all events
purchases = filter_retail_purchases(retail)             # RFM-ready subset
tickets = clean_support_tickets(load_support_tickets())

print(purchases)
print("*************")
print(tickets)

from src.agents.data_agent.validate import validate_cleaned_sources, raise_if_any_errors
reports = validate_cleaned_sources(telco, retail, tickets, purchases=purchases)
raise_if_any_errors(reports)  # warnings are OK
for report in reports:
    print(report.dataset, "ok" if report.ok else "FAILED")
    for issue in report.warnings:
        print("  warning:", issue.check, issue.n_rows)
"""



