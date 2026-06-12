import re

def extract_float(text):
    if not text:
        return 0.0
    # Find all float-like patterns in text (e.g. 10.5, 10, 1.23)
    matches = re.findall(r"[-+]?\d*\.\d+|\d+", str(text))
    if matches:
        # Return the first found number
        return float(matches[0])
    return 0.0

def extract_multiple_strings(text):
    if not text:
        return []
    # Split by comma or 'and', strip whitespace
    parts = re.split(r',| and |&|\/', str(text))
    cleaned = [p.strip() for p in parts if p.strip()]
    return cleaned

env = self.env
jobs = env['hr.job'].with_context(active_test=False).search([])
for job in jobs:
    if job.x_budget:
        val = extract_float(job.x_budget)
        if job.x_employment_type == 'fte':
            job.write({'x_budget_lpa': val})
        elif job.x_employment_type == 'consulting':
            job.write({'x_bill_rate_lpm': val})
env.cr.commit()

applicants = env['hr.applicant'].with_context(active_test=False).search([])
for app in applicants:
    vals = {}
    if app.x_current_ctc:
        vals['x_current_ctc_lpa'] = extract_float(app.x_current_ctc)
    if app.x_expected_ctc:
        vals['x_expected_ctc_lpa'] = extract_float(app.x_expected_ctc)
    
    if vals:
        app.write(vals)

    # Process Offer in hand M2M tags
    if app.x_offer_in_hand:
        offers = extract_multiple_strings(app.x_offer_in_hand)
        tag_ids = []
        for offer in offers:
            # We enforce names to be just strings, e.g. "12.5"
            tag = env['hr.applicant.offer.tag'].search([('name', '=ilike', offer)], limit=1)
            if not tag:
                tag = env['hr.applicant.offer.tag'].create({'name': offer})
            tag_ids.append(tag.id)
        if tag_ids:
            app.write({'x_offer_in_hand_ids': [(6, 0, tag_ids)]})
env.cr.commit()
print("Migration completed.")
