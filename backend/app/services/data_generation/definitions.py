import uuid
from datetime import datetime


START_DATE = datetime(2024, 7, 1)

END_DATE = datetime(2025, 12, 31)

NUM_CUSTOMERS = 5000

CHURN_RATE = 0.15

INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Retail",
    "Manufacturing", "Education", "Media", "Logistics",
]

COMPANY_SIZES = ["startup", "smb", "mid_market", "enterprise"]

COMPANY_SIZE_WEIGHTS = [0.30, 0.30, 0.25, 0.15]

PLAN_TIERS = ["free", "starter", "professional", "enterprise"]

PLAN_TIER_WEIGHTS = [0.10, 0.30, 0.35, 0.25]

REGIONS = ["north_america", "europe", "apac", "latam"]

REGION_WEIGHTS = [0.45, 0.25, 0.20, 0.10]

CHANNELS = ["organic", "paid_search", "referral", "partner", "content"]

CHANNEL_WEIGHTS = [0.25, 0.25, 0.20, 0.15, 0.15]

MRR_BY_TIER = {"free": 0, "starter": 49, "professional": 149, "enterprise": 499}

EVENT_TYPES = ["login", "feature_use", "page_view", "export", "invite_user", "api_call"]

FEATURES = [
    "dashboard", "reports", "integrations", "api", "automations",
    "collaboration", "analytics", "export", "admin", "billing",
]

TICKET_CATEGORIES = [
    "billing", "technical", "feature_request", "bug_report",
    "onboarding", "cancellation",
]

FEEDBACK_CHANNELS = ["nps_survey", "csat_survey", "in_app", "email", "review_site"]

OUTAGE_START = datetime(2024, 8, 15)

OUTAGE_END = datetime(2024, 9, 30)

TICKET_TEMPLATES = {
    "billing": [
        "I was charged twice this month and need a refund processed immediately.",
        "Our invoice doesn't match the agreed pricing. Can someone review this?",
        "We're having trouble updating our payment method in the billing portal.",
        "I need to understand the charges on our latest statement, several line items are unclear.",
        "Can we switch from monthly to annual billing? What discount is available?",
        "The auto-renewal charged us but we wanted to cancel. Please reverse this.",
    ],
    "technical": [
        "The dashboard keeps timing out when I try to load reports for the past quarter.",
        "Our API integration is returning 500 errors intermittently since last night.",
        "Data sync between our CRM and your platform seems delayed by several hours.",
        "The export feature generates corrupted CSV files when the dataset exceeds 10K rows.",
        "Single sign-on stopped working after we updated our identity provider config.",
        "Performance has degraded significantly — page loads are taking 15+ seconds.",
    ],
    "feature_request": [
        "We need the ability to schedule automated report delivery to stakeholders.",
        "Can you add support for custom date ranges in the analytics dashboard?",
        "We'd love a Slack integration for real-time alerts when metrics change.",
        "It would be helpful to have role-based access controls for different team members.",
        "Please consider adding a mobile app — our field team needs access on the go.",
        "We need webhook support for triggering workflows in our internal tools.",
    ],
    "bug_report": [
        "Charts on the overview page aren't rendering correctly in Safari.",
        "The search function returns no results even for exact-match queries.",
        "Notifications are being sent twice for every alert trigger we set up.",
        "The date picker component resets to today's date every time I change tabs.",
        "User permissions changes aren't taking effect until we clear the browser cache.",
        "Filters applied on one page persist unexpectedly when navigating to another.",
    ],
    "onboarding": [
        "We just signed up and need help migrating data from our previous analytics tool.",
        "Can someone walk us through setting up our first dashboard? The docs are unclear.",
        "Our team of 15 needs onboarding — is there a group training option available?",
        "We're stuck on the API setup step. The authentication flow isn't well documented.",
        "How do we connect our Salesforce instance? The integration guide seems outdated.",
    ],
    "cancellation": [
        "We've decided to move to a competitor that better fits our workflow. Please cancel.",
        "Our budget has been cut and we can no longer justify the cost. Need to cancel.",
        "The platform doesn't meet our needs. Too many missing features for our use case.",
        "We're consolidating tools and your product didn't make the cut. Please process cancellation.",
        "Repeated outages have eroded our trust. We need to cancel effective immediately.",
    ],
}

FEEDBACK_TEMPLATES = {
    "positive": [
        "Love the new analytics dashboard! It's exactly what our team needed.",
        "Support team was incredibly responsive and resolved our issue within the hour.",
        "The product keeps getting better with each release. Very impressed with the roadmap.",
        "Onboarding was smooth and the documentation is excellent. Great experience so far.",
        "The platform has saved our team at least 10 hours per week on reporting.",
    ],
    "neutral": [
        "The product works fine for basic use cases but we need more advanced features.",
        "Decent tool overall. Some UI improvements would make it much more intuitive.",
        "It gets the job done but the learning curve is steeper than expected.",
        "Solid product. Would appreciate better integration options with our existing stack.",
        "No major complaints, but nothing that really stands out from competitors either.",
    ],
    "negative": [
        "Frustrated with the constant performance issues. This is affecting our productivity.",
        "The pricing doesn't match the value we're getting. Considering alternatives.",
        "We've reported the same bug three times and it's still not fixed. Very disappointed.",
        "The recent UI update made everything harder to find. Please revert or improve navigation.",
        "Our team has lost confidence in the platform after the recent data sync failures.",
    ],
}

def uid() -> str:
    return str(uuid.uuid4())
