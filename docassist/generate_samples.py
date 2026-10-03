"""Create demo company documents (PDF) to try the assistant with.

    python -m docassist.generate_samples samples/
"""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

DOCUMENTS = {
    "employee_handbook.pdf": [
        ("Northwind Supplies - Employee Handbook", [
            ("Working hours", "Standard working hours are Monday to Friday from 9:00 to 18:00 (UTC-3). "
             "Employees may work remotely up to three days per week after completing their probation period."),
            ("Probation period", "The probation period lasts 90 days. During probation, remote work is limited "
             "to one day per week and requires approval from the direct manager."),
        ]),
        ("Leave and expenses", [
            ("Vacation", "Full-time employees receive 15 business days of paid vacation per year. Vacation requests "
             "must be submitted in the HR portal at least 10 business days in advance."),
            ("Sick leave", "Sick leave longer than two consecutive days requires a medical certificate sent to "
             "hr@northwind.example within 48 hours."),
            ("Expense reimbursement", "Business expenses are reimbursed within 15 days. Receipts must be uploaded "
             "to the expenses folder before the 5th of the following month. Meals are reimbursed up to USD 25 per day "
             "during business trips."),
        ]),
    ],
    "product_faq.pdf": [
        ("Northwind Supplies - Customer FAQ", [
            ("Shipping", "Orders placed before 14:00 ship the same business day. Standard delivery takes 2 to 5 "
             "business days. Shipping is free for orders above USD 150."),
            ("Returns and refunds", "Customers can return unused products within 30 days of delivery. Refunds are "
             "issued to the original payment method within 7 business days after the return is inspected. "
             "Custom-printed products cannot be returned."),
            ("Warranty", "Electronic products include a 12-month warranty against manufacturing defects. "
             "The warranty does not cover damage caused by misuse or unauthorized repairs."),
        ]),
    ],
    "service_agreement.pdf": [
        ("Service Level Agreement - Managed Support", [
            ("Support hours", "Support is available Monday to Friday, 8:00 to 20:00 (UTC-3), by email and WhatsApp."),
            ("Response times", "Critical incidents receive a first response within 1 hour. High priority tickets "
             "within 4 business hours. Normal tickets within 1 business day."),
            ("Uptime and credits", "The provider guarantees 99.5% monthly uptime. If uptime falls below the target, "
             "the client receives a service credit of 10% of the monthly fee for each 0.5% below the target, "
             "up to a maximum of 50%."),
            ("Termination", "Either party may terminate the agreement with 30 days written notice."),
        ]),
    ],
}


def generate(folder: Path) -> list[Path]:
    """Write the demo PDFs into `folder` (created if needed) and return their paths."""
    folder.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    paths = []
    for filename, pages in DOCUMENTS.items():
        story = []
        for page_index, (title, sections) in enumerate(pages):
            if page_index:
                story.append(PageBreak())
            story.append(Paragraph(title, styles["Title"]))
            for heading, body in sections:
                story += [Paragraph(heading, styles["Heading2"]), Paragraph(body, styles["BodyText"]), Spacer(1, 8)]
        path = folder / filename
        SimpleDocTemplate(str(path), pagesize=A4, title=pages[0][0]).build(story)
        paths.append(path)
    return paths


def main() -> None:
    """Command-line entry point: generate the demo PDFs and print their paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path, nargs="?", default=Path("samples"))
    args = parser.parse_args()
    for path in generate(args.folder):
        print(path)


if __name__ == "__main__":
    main()
