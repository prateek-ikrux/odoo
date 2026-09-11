# -*- coding: utf-8 -*-
{
    'name': 'CRM Custom',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'author': 'iKrux',
    'website': 'https://www.ikrux.com',
    'summary': 'Replaces revenue/probability on CRM leads with staffing requirement and client onboarding details',
    'description': """
CRM Custom
==========

Reshapes the CRM lead / opportunity around a staffing requirement rather than a
monetary forecast.

Removed from every view (form, kanban, lists, calendar, activity, graph, pivot
and the pipeline analysis reports):

* Expected Revenue (and its prorated variant on the Forecast views)
* Probability (%)
* the Properties block

The fields themselves are kept on the model so the won / lost lifecycle, the
existing data and any other module relying on them keep working.

Added:

* Percentage Discussed and Bill Rate - both sit where the probability used to
  be, in the title. A full-time placement is priced as a percentage and a
  consulting one as a bill rate, so the engagement type decides which shows.
  Neither is required: the figure is rarely known when the lead is raised.
* Client Name - the standard Company Name field, relabelled.
* Client Location, POC Location, Type of Client (Active / Dormant / Passive),
  No. of Open Positions and Roles Opened.
* Engagement Type (Full-time / Consulting) with the Project Duration in months.
  A full-time engagement reads NA instead of a duration.
* An "Engagement Progress" block inside Client & Requirement Details, tracking
  Requirement Received, Recruitment Started, Agreement Signed and Client
  Onboarded.

Changed on the Contacts tab:

* Company Information gains the Client Location.
* Contact Information gains Number and POC Location, and Job Position is
  relabelled Designation.
* The Marketing group is hidden.
""",
    'depends': ['crm'],
    'data': [
        'views/crm_lead_view_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
