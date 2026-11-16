import streamlit as st
import pandas as pd
import altair as alt
import math
import re
import sys
import json
from pathlib import Path

# import the model assets 

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from recommender.presentation import money

@st.cache_resource(show_spinner="Loading the saved ranking model and plan catalog...")
def get_model_assets(bundle_signature):
    from recommender.inference import load_assets
    return load_assets()


# load the supported zip codes for input validation

zip_codes = pd.read_csv(
    Path(__file__).resolve().parent / "florida_zip_codes.csv"
)
zip_codes = zip_codes["ZIP Code"].astype(str).to_numpy()


# define the header for questionnaire's pages
def quest_header(section_num, section_title):

    st.title("Health Insurance Questionnaire", anchor=False)
    st.markdown(f"## Section {section_num} | _{section_title}_", anchors=False)


# define the app's initial state

if "page" not in st.session_state:
    st.session_state.page = 0

if "zip_touched" not in st.session_state:
    st.session_state.zip_touched = False

if "people_selected" not in st.session_state:
    st.session_state.people_selected = False


# calculate page positions dynamically based on the number
# of dependents who need coverage.

DEPENDENTS_START = 9

n_dependents = (
    st.session_state.get("total_dependents", 0)
    if st.session_state.get("include_dependents", False)
    else 0
)

NEXT_SECTION = DEPENDENTS_START + n_dependents
BENEFITS_PAGE = NEXT_SECTION + 5
RECOMMENDATIONS_PAGE = BENEFITS_PAGE + 1


# sidebar for progress tracking
if 0 < st.session_state.page < BENEFITS_PAGE:

    current_page = st.session_state.page

    # Results page
    BENEFITS_PAGE = NEXT_SECTION + 5

    # Three sections
    sections = [
        ("Location & Household", 1, 6),
        ("About the Applicants", 6, NEXT_SECTION),
        ("Healthcare Needs & Preferences", NEXT_SECTION, BENEFITS_PAGE)
    ]

    # Calculate progress
    total_steps = BENEFITS_PAGE - 1

    progress = min(
        100,
        max(0, int((current_page - 1) / total_steps * 100))
    )

    # Sidebar
    if current_page > 0:

        with st.sidebar:

            st.markdown("### Questionnaire Progress")

            st.progress(
                progress,
                text=f"{progress}% complete"
            )

            st.divider()

            for title, start, end in sections:

                if current_page >= end:
                    icon = ":material/check_circle:"
                    label = title

                elif start <= current_page < end:
                    icon = ":material/radio_button_checked:"
                    label = f"**{title}**"

                else:
                    icon = ":material/radio_button_unchecked:"
                    label = f":gray[{title}]"

                st.markdown(f"{icon}  {label}")


# define functions to track user interaction
def mark_zip_touched():
    st.session_state.zip_touched = True

def mark_people_selected():
    st.session_state.people_selected = True


# reuse navigation controls across pages and allow conditional
# page skipping based on the user's previous answers
def navigation_buttons(validity, skip_f=1, skip_b=1):
    col1, spacer, col2 = st.columns([1, 4, 0.6])

    with col1:
        if st.button("← Return", disabled=st.session_state.page == 0):
            st.session_state.page -= skip_b
            st.rerun()

    with col2:
        if st.button("Next →", type="primary", disabled=not validity):
            st.session_state.page += skip_f
            st.rerun()


# landing Page
if st.session_state.page == 0:

    st.markdown(
        "<h1 style='text-align: center;'>"
        "Find the Right Health Insurance Plan for You"
        "</h1>",
        anchors = False,
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align: center; color: gray; font-size: 19px;'>"
        "Discover health insurance options tailored to "
        "your household, budget, and healthcare needs."
        "</p>",
        anchors=False,
        unsafe_allow_html=True
    )

    st.write("")
    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True, height=180):
            st.markdown("##### :material/tune: Personalized",
                        anchors = False)
            st.write(
                "Explore plans based on your household "
                "and personal preferences."
            )

    with col2:
        with st.container(border=True, height=180):
            st.markdown("##### :material/payments: Budget-Aware",
                        anchors = False)
            st.write(
                "Compare monthly premiums and "
                "out-of-pocket costs."
            )

    with col3:
        with st.container(border=True, height=180):
            st.markdown("##### :material/verified_user: Plan Comparison",
                        anchors = False)
            st.write(
                "Find options that match your "
                "healthcare needs."
            )

    st.write("")
    st.write("")

    left, center, right = st.columns([1, 1.5, 1])

    with center:
        if st.button(
            "Get Started",
            type="primary",
            width="stretch",
            icon=":material/arrow_forward:"
        ):
            st.session_state.page = 1
            st.rerun()

    st.caption(
        "This tool provides informational plan comparisons for 2026. "
        "Final eligibility and enrollment are determined "
        "through the official Marketplace."
    )

    st.caption(
        "Inspired by the [official HealthCare.gov plan comparison tool](https://www.healthcare.gov/see-plans/#/). " \
        "This is an independent project and is not affiliated with or endorsed by HealthCare.gov."
    )

    
# question 01: zip code
if st.session_state.page == 1:

    quest_header("01", "Location & Household")

    st.markdown("### What is your _ZIP Code?_ (Florida)", anchors=False)

    zip_code = st.text_input(
        "Enter the first 5 digits of your ZIP Code.", 
        label_visibility = "visible",
        value=None, 
        placeholder="e.g., 32816",
        max_chars = 5,
        live = True,
        required = True,
        persist_state = "session",
        key = "zip_code",
        on_change=mark_zip_touched
        )

    validity = bool(re.fullmatch(r"\d{5}", zip_code or "") and zip_code in zip_codes)

    if zip_code and not validity and st.session_state.zip_touched:
        st.error("Please enter a valid 5-digit Florida ZIP code.")

    navigation_buttons(validity)


# question 02: claimed as a dependent
if st.session_state.page == 2:

    quest_header("01", "Location & Household")

    st.markdown("### Will someone else claim you as tax dependent?", anchors=False)

    is_dependent = st.radio(
        "Select the option that best reflects your situation.",
        ["Yes", "No", "Not Sure"],
        help = (
            r"Someone claims you as a tax dependent if they include you on "
            r"their federal tax return, usually a parent or guardian. "
            r"For example, if your parents include you as a dependent on their taxes, select "
            r"\"Yes\" — even if you work or file your own tax return."
        ),
        index = None,
        persist_state = "session",
        key = "is_dependent",
        )

    validity = is_dependent is not None

    if is_dependent == "Yes":
        st.markdown("### How many people are in the household of the person claiming you as a tax dependent?", anchors=False)

        total_household = st.number_input(
            r"Include the person claiming you, their spouse (if married), you, "
            r"and any other dependents they claim on their federal tax return.", 
            help = (
                "For example, if your parents claim you and your sibling, "
                "your household size would be 4."
            ),
            label_visibility = "visible",
            value=2, 
            placeholder="e.g., 3",
            step = 1,
            persist_state = "session",
            key = "dependent_total_household",
            )
        
        validity = total_household is not None and total_household > 1

        if not validity:
            st.error("Please enter only whole numbers greater than 1 (e.g., 3)")
        
    else:
        total_household = 0

    navigation_buttons(validity, skip_f = 3 if is_dependent == "Yes" else 1)


# question 03: married
if st.session_state.page == 3:

    quest_header("01", "Location & Household")

    st.markdown("### Are you legally married?", anchors=False)

    is_married = st.radio(
        r"Select \"Yes\" only if you are legally married, "
        r"not simply living with a partner.", 
        ["Yes", "No"],
        help = (
            "For example, living with your boyfriend or girlfriend "
            "does not count as being legally married."
        ),
        index = None,
        persist_state = "session",
        key = "married"
        )
    
    validity = is_married is not None

    if is_married == "Yes":
        st.markdown("### Will you file a joint federal income tax return with your spouse?", anchors=False)

        fill_jointly = st.radio(
            "Select the option that best reflects your situation.", 
            ["Yes", "No", "Not Sure"],
            help = (
                r"Filing jointly means you and your spouse submit one "
                r"federal income tax return together, rather than separate returns. "
                r"For example, if you and your spouse report your "
                r"income together on the same tax return, select \"Yes\"."
            ),
            index = None,
            persist_state = "session",
            key = "jointly",
            )

        validity = fill_jointly is not None
        
    else:
        fill_jointly = "No"

    navigation_buttons(validity)


# question 04: claimed dependents
if st.session_state.page == 4:

    quest_header("01", "Location & Household")

    st.markdown("### Will you claim _any dependents_ on your 2026 federal tax return?", anchors=False)

    has_dependents = st.radio(
        "Select the option that best reflects your situation.", 
        ["Yes", "No", "Not Sure"],
        help = (
            "Dependents are people you expect to claim on your federal tax return, "
            "such as qualifying children or relatives. "
            "For example, if you plan to claim your two children on your taxes, select \"Yes\" "
            "and enter 2 — even if they already have health insurance."
        ),
        index = None,
        persist_state = "session",
        key = "has_dependents"
        )

    validity = has_dependents is not None

    if has_dependents == "Yes":
        st.markdown("### How many dependents will you claim?", anchors=False)

        total_dependents_tax = st.number_input(
            "Enter the number of dependents that you will claim.", 
            label_visibility = "visible",
            value=1, 
            placeholder="e.g., 3",
            step = 1,
            persist_state = "session",
            key = "total_dependents_tax",
            )
        
        validity = total_dependents_tax is not None and total_dependents_tax > 0

        if not validity:
            st.error("Please enter only whole numbers greater than zero (e.g., 3)")
        
    else:
        total_dependents_tax = 0

    navigation_buttons(validity)


# question 05: estimated annual household income
if st.session_state.page == 5:

    quest_header("01", "Location & Household")

    st.markdown("### What is your estimated _annual household income_ for 2026?", anchors=False)

    income = st.number_input(
        r"Enter your household's expected income for 2026.",
        help = (
            r"Enter the total income your household expects to receive "
            r"throughout 2026, not just your personal income. "
            r"For example, if you earn \$45,000 and your spouse earns "
            r"\$25,000, your estimated household income is $70,000."
        ),
        label_visibility = "visible",
        value=60000, 
        placeholder="e.g., 60700",
        step = 10000,
        persist_state = "session",
        key = "income",
        )

    validity = income >= 0

    if not validity:
        st.error("Please enter only whole numbers greater or equal to 0 (e.g., 60700)")

    navigation_buttons(validity, skip_b = 3 if st.session_state.get("is_dependent") == "Yes" else 1)


# question 06: who needs insurance
if st.session_state.page == 6:

    quest_header("02", "About the Applicants")

    st.markdown("### Who _needs_ health insurance coverage?", anchors=False)

    st.text(
        "Select only the people who need health insurance coverage."
    )
    include_me = st.checkbox(
        label = "Me",
        label_visibility = "visible",
        key = "include_me",
        persist_state = "session",
        on_change = mark_people_selected
    )
    include_partner = st.checkbox(
        label = "My partner/spouse",
        label_visibility = "visible",
        persist_state = "session",
        key = "include_partner",
        on_change = mark_people_selected
    )
    include_dependents = st.checkbox(
        label = "My children or other dependents",
        label_visibility = "visible",
        persist_state = "session",
        key = "include_dependents",
        on_change = mark_people_selected
    )

    if (include_dependents):
        
        total_dependents = st.number_input(
            "Please inform the number of other dependents seeking health care", 
            label_visibility = "visible",
            value=1, 
            placeholder="e.g., 3",
            step = 1,
            required = True,
            persist_state = "session",
            key = "total_dependents"
            )

    if not include_dependents:
        validity = include_me or include_partner

    else:
        validity = total_dependents > 0

        if st.session_state.people_selected and not validity:
            st.error("Please inform a valid number of dependents")

    if include_me:
        next_page = 7

    elif include_partner:
        next_page = 8

    else:
        next_page = (
            DEPENDENTS_START
            if n_dependents > 0
            else NEXT_SECTION
        )

    navigation_buttons(
        validity,
        skip_f=next_page - st.session_state.page
    )


# question 07: questions about the user
if st.session_state.page == 7:

    quest_header("02", "About the Applicants")

    st.markdown("### How old are _you_?", anchors=False)

    you_age = st.number_input(
        "Enter your age", 
        label_visibility = "collapsed",
        value=25, 
        placeholder="e.g., 3",
        step = 10,
        required = True,
        persist_state = "session",
        key = "you_age",
        )

    if you_age < 0:
            st.error("Please select a valid age.")

    st.markdown("### Do you _smoke_?", anchors=False)

    you_smoke = st.radio(
        "Select an option",
        ["Yes", "No"],
        label_visibility="collapsed",
        index = None,
        persist_state = "session",
        key = "you_smoke"
        )

    st.markdown("### Are you currently _pregnant_?", anchors=False)

    you_pregnant = st.radio(
        "Select an option",
        ["Yes", "No", "Prefer not to say"],
        label_visibility="collapsed",
        index = None,
        persist_state = "session",
        key = "you_pregnant"
        )

    validity = you_age > 0 and you_smoke is not None and you_pregnant is not None

    if st.session_state.get("include_partner", False):
        next_page = 8

    elif n_dependents > 0:
        next_page = DEPENDENTS_START

    else:
        next_page = NEXT_SECTION

    navigation_buttons(
        validity,
        skip_f=next_page - st.session_state.page
    )


# question 08: questions about the user's spouse
if st.session_state.page == 8:

    quest_header("02", "About the Applicants")

    st.markdown("### How old is your _spouse_?", anchors=False)

    st.text("Please inform your spouse's age.")
    spouse_age = st.number_input(
        "Enter the age", 
        label_visibility = "collapsed",
        value=25, 
        placeholder="e.g., 3",
        step = 10,
        required = True,
        persist_state = "session",
        key = "spouse_age",
        )

    if spouse_age < 0:
            st.error("Please select a valid age")

    st.markdown("### Does your spouse _smoke_?", anchors=False)

    spouse_smoke = st.radio(
        "Select the option that better reflects your situation.",
        ["Yes", "No"],
        label_visibility= "collapsed",
        index = None,
        persist_state = "session",
        key = "spouse_smoke"
        )

    st.markdown("### Is your spouse currently _pregnant_?", anchors=False)

    spouse_pregnant = st.radio(
        "Select the option that better reflects your situation.", 
        ["Yes", "No", "Prefer not to say"],
        label_visibility="collapsed",
        index = None,
        persist_state = "session",
        key = "spouse_pregnant"
        )

    validity = spouse_age > 0 and spouse_smoke is not None and spouse_pregnant is not None

    next_page = (
        DEPENDENTS_START
        if n_dependents > 0
        else NEXT_SECTION
    )

    previous_page = (
        7 if st.session_state.get("include_me", False)
        else 6
    )

    navigation_buttons(
        validity,
        skip_f=next_page - st.session_state.page,
        skip_b=st.session_state.page - previous_page
    )


# question 09: questions about the user's dependents
if DEPENDENTS_START <= st.session_state.page < NEXT_SECTION:

    quest_header("02", "About the Applicants")

    i = st.session_state.page - DEPENDENTS_START

    st.markdown(
        f"## Dependent {i + 1} of {n_dependents}",
        anchors=False
    )

    st.markdown(
        f"### How old is this _dependent_?",
        anchors=False
    )
    age = st.number_input(
        "Please enter a valid age.",
        label_visibility = "collapsed",
        min_value=0,
        value=12,
        step=1,
        required=True,
        key=f"dependent_{i}_age",
        persist_state="session"
    )

    st.markdown(
        f"### Does this dependent _smoke_?",
        anchors=False
    )
    smoke = st.radio(
        "Does this dependent smoke?",
        ["Yes", "No"],
        label_visibility="collapsed",
        index=None,
        key=f"dependent_{i}_smoke",
        persist_state="session"
    )

    st.markdown(
        f"### Is this dependent _pregnant_?",
        anchors=False
    )
    pregnant = st.radio(
        "Is this dependent currently pregnant?",
        ["Yes", "No", "Prefer not to say"],
        label_visibility= "collapsed",
        index=None,
        key=f"dependent_{i}_pregnant",
        persist_state="session"
    )

    validity = smoke is not None and pregnant is not None

    # determine previous page

    if i > 0:
        previous_page = st.session_state.page - 1

    elif st.session_state.get("include_partner", False):
        previous_page = 8

    elif st.session_state.get("include_me", False):
        previous_page = 7

    else:
        previous_page = 6

    navigation_buttons(
        validity,
        skip_f=1,
        skip_b=st.session_state.page - previous_page
    )


# question 10: expected healthcare usage
if st.session_state.page == NEXT_SECTION:

    quest_header("03", "Healthcare Needs & Preferences")

    st.markdown(
        "### How much healthcare do the applicants "
        "_expect to need_ in the coming year?",
        anchors=False
    )

    healthcare_usage = st.radio(
        "Select the option that best describes your household.",
        [
            "High - Frequent medical care, ongoing treatments, or major medical procedures",
            "Moderate - Some doctor visits, specialist appointments, or regular medications",
            "Low - Mostly preventive care and occasional doctor visits",
            "Not sure"
        ],
        index=None,
        key="healthcare_usage",
        persist_state="session"
    )

    validity = healthcare_usage is not None

    if st.session_state.get("include_dependents", False):
        previous_page = NEXT_SECTION - 1

    elif st.session_state.get("include_partner", False):
        previous_page = 8

    elif st.session_state.get("include_me", False):
        previous_page = 7

    else:
        previous_page = 6

    navigation_buttons(
        validity,
        skip_b=NEXT_SECTION - previous_page
    )


# question 11: personal priorities
if st.session_state.page == NEXT_SECTION + 1:

    quest_header("03", "Healthcare Needs & Preferences")

    st.markdown(
        "### What _matters most_ to you when choosing "
        "a health insurance plan?",
        anchors=False
    )

    priorities = st.multiselect(
        "Select up to two priorities.",
        [
            "Lower monthly premiums",
            "Lower costs when receiving care",
            "Protection against large medical bills",
            "More freedom to choose doctors"
        ],
        select_all=False,
        max_selections=2,
        key="priorities",
        persist_state="session",
        placeholder="Select up to two options"
    )

    validity = len(priorities) > 0

    navigation_buttons(validity)


# question 12: monthly budget
if st.session_state.page == NEXT_SECTION + 2:

    quest_header("03", "Healthcare Needs & Preferences")

    st.markdown(
        "### What is the maximum amount your household "
        "would feel _comfortable paying per month_ "
        "for health insurance?",
        anchors=False
    )

    monthly_budget = st.slider(
        "Maximum monthly budget (USD)",
        label_visibility= "collapsed",
        min_value=0,
        max_value=2000,
        value=500,
        step=50,
        format="$%d",
        persist_state="session",
        key="monthly_budget"
    )

    end = "+" if monthly_budget == 2000 else ""

    st.write(f"Your maximum monthly budget: **${monthly_budget:,}{end}**")

    navigation_buttons(True)


# question 13: specialist referrals
if st.session_state.page == NEXT_SECTION + 3:

    quest_header("03", "Healthcare Needs & Preferences")

    st.markdown(
        "### How important is it to see specialists "
        "_without a referral_?",
            anchors=False
    )

    referral_preference = st.radio(
        "Select an option",
        [
            "Very important",
            "Somewhat important",
            "Not important"
        ],
        label_visibility="collapsed",
        index=None,
        key="referral_preference",
        persist_state="session"
    )

    validity = referral_preference is not None

    navigation_buttons(validity)


# question 14: out-of-network coverage
if st.session_state.page == NEXT_SECTION + 4:

    quest_header("03", "Healthcare Needs & Preferences")

    st.markdown(
        "### Do you need coverage for non-emergency "
        "care _outside your provider network_?",
        anchors = False
    )

    out_network = st.radio(
        "Select an option",
        ["Yes", "No", "Not sure"],
        label_visibility= "collapsed",
        index=None,
        key="out_network",
        persist_state="session"
    )

    validity = out_network is not None

    col1, spacer, col2 = st.columns([1, 4, 1.5])

    with col1:
        if st.button("← Return"):
            st.session_state.page -= 1
            st.rerun()

    with col2:
        if st.button(
            "View Results →",
            type="primary",
            disabled=not validity,
            width="stretch"
        ):
            st.session_state.page = BENEFITS_PAGE
            st.rerun()


# potential benefits page

COVERAGE_YEAR = 2026

OFFICIAL_SOURCES = {
    "marketplace": "https://www.healthcare.gov/lower-costs/",
    "tax_credit": "https://www.irs.gov/credits-deductions/premium-tax-credit-ptc-overview",
    "cost_sharing": "https://www.healthcare.gov/lower-costs/save-on-out-of-pocket-costs/",
    "kidcare": "https://www.floridakidcare.org/requirements/",
    "medicaid": "https://www.myflfamilies.com/medicaid/determining-your-income-limit",
    "medicare": "https://www.healthcare.gov/medicare/medicare-and-the-marketplace/",
}


# marketplace coverage in 2026 uses the 2025 federal poverty guidelines.
# these values apply to florida and the other contiguous states.
def get_fpl(household_size):
    return 15650 + 5500 * (household_size - 1)


# estimate tax household size from the questionnaire's existing paths
def get_household_size():
    state = st.session_state
    dependent_status = state.get("is_dependent")

    if dependent_status == "Yes":
        # Question 02 already collects the claiming tax filer's household size.
        # Questions 03 and 04 are skipped for this path.
        raw_size = state.get("dependent_total_household")
        try:
            size = int(raw_size)
            if isinstance(raw_size, bool) or size < 2 or float(raw_size) != size:
                return None
            return size
        except (TypeError, ValueError, OverflowError):
            return None

    if dependent_status != "No":
        return None

    # For non-dependents, the questionnaire asks about marriage and dependents.
    married = state.get("married")
    has_dependents = state.get("has_dependents")

    if married not in ("Yes", "No") or has_dependents not in ("Yes", "No"):
        return None

    # Separate tax returns generally require a more individualized PTC review.
    if married == "Yes" and state.get("jointly") != "Yes":
        return None

    household = 1 + (1 if married == "Yes" else 0)

    if has_dependents == "Yes":
        raw_count = state.get("total_dependents_tax")
        try:
            count = int(raw_count)
            if isinstance(raw_count, bool) or count < 1 or float(raw_count) != count:
                return None
            household += count
        except (TypeError, ValueError, OverflowError):
            return None

    return household


# read the annual household income already collected in question 05
def get_estimated_annual_income():
    value = st.session_state.get("income")
    if value is None or isinstance(value, bool):
        return None
    try:
        income = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(income) or income < 0:
        return None
    return income


# use only people selected as needing health insurance coverage
def get_applicants():
    state = st.session_state
    applicants = []

    if state.get("include_me", False):
        applicants.append({
            "name": "You",
            "age": state.get("you_age"),
            "pregnant": state.get("you_pregnant") == "Yes",
            "role": "self",
        })

    if state.get("include_partner", False):

        if state.get("is_dependent") == "Yes":
            relationship = "Your partner/spouse"
        else:
            relationship = (
                "Your spouse" if state.get("married") == "Yes" else "Your partner"
            )
        applicants.append({
            "name": relationship,
            "age": state.get("spouse_age"),
            "pregnant": state.get("spouse_pregnant") == "Yes",
            "role": "partner",
        })

    if state.get("include_dependents", False):
        n = int(state.get("total_dependents", 0) or 0)
        for i in range(n):
            applicants.append({
                "name": f"Dependent {i + 1}",
                "age": state.get(f"dependent_{i}_age"),
                "pregnant": state.get(f"dependent_{i}_pregnant") == "Yes",
                "role": "dependent",
            })

    return applicants


# florida dcf monthly thresholds for ages 19-20 and parents/caretakers
# effective april 2026 through march 2027; other medicaid groups differ
FLORIDA_FAMILY_MEDICAID_MONTHLY_LIMITS = {
    1: 356,
    2: 478,
    3: 600,
    4: 723,
    5: 846,
    6: 968,
    7: 1091,
    8: 1214,
    9: 1335,
    10: 1459,
    11: 1583,
    12: 1706,
}


# suggest coverage programs, without determining official eligibility
def get_potential_benefits(person, household_size, income, applicants):

    benefits = []
    state = st.session_state
    name = person["name"]
    age = person.get("age")
    role = person.get("role")

    def add_benefit(title, message, source):
        benefits.append({
            "title": title,
            "message": message,
            "source": OFFICIAL_SOURCES[source],
        })

    if age is None:
        add_benefit(
            "Marketplace Coverage Review",
            f"Coverage options for {name.lower()} can be explored through the "
            "official Marketplace application. More information is needed.",
            "marketplace",
        )
        return benefits

    if age < 19:
        add_benefit(
            "Florida KidCare",
            f"{name} may qualify for coverage through Florida KidCare. "
            "Free, subsidized, or full-pay options may apply depending on "
            "income and other eligibility requirements.",
            "kidcare",
        )

    if person.get("pregnant") is True:
        add_benefit(
            "Florida Pregnancy Medicaid",
            f"{name} may qualify for pregnancy-related Medicaid coverage. "
            "Income, household composition, and other requirements apply.",
            "medicaid",
        )

    if age < 19:
        return benefits

    if age >= 65:
        add_benefit(
            "Medicare Eligibility Review",
            f"{name} may qualify for Medicare based on age. "
            "Eligibility and any Part A premium depend on additional rules. "
            "If Medicare is not available, ask about Marketplace options.",
            "medicare",
        )
        return benefits

    # an unmarried partner may have a different tax household. for tax
    # dependents, marriage was not asked, so that relationship is also unknown.
    partner_household_uncertain = (
        state.get("include_partner", False)
        and (
            state.get("is_dependent") == "Yes"
            or state.get("married") != "Yes"
        )
    )

    income_screen_available = (
        household_size is not None
        and income is not None
        and not partner_household_uncertain
    )

    # a tax-household size is only a proxy for the person's medicaid household
    # this comparison flags cases worth reviewing; it does not decide eligibility.
    medicaid_limit = (
        FLORIDA_FAMILY_MEDICAID_MONTHLY_LIMITS.get(household_size)
        if income_screen_available
        else None
    )
    medicaid_screen_available = medicaid_limit is not None
    low_income_for_medicaid_review = (
        medicaid_screen_available and income / 12 <= medicaid_limit
    )
    show_medicaid_review = (
        not medicaid_screen_available or low_income_for_medicaid_review
    )

    if low_income_for_medicaid_review:
        medicaid_income_message = (
            "The reported income is within the published limit using the "
            "estimated household size, but Medicaid may count households "
            "and income differently. "
        )
    else:
        medicaid_income_message = (
            "A reliable Medicaid income comparison cannot be made from "
            "these answers. "
        )

    if age in (19, 20) and show_medicaid_review:
        add_benefit(
            "Florida Medicaid — Ages 19–20 Review",
            f"{name} may want to explore Florida Medicaid's ages 19–20 "
            "category. " + medicaid_income_message
            + "This category generally requires being unmarried or having "
            "had a marriage annulled. Other eligibility rules apply.",
            "medicaid",
        )

    # identify possible minor children, including those who already
    # have coverage and were not selected as applicants.
    minor_applicant_present = any(
        p.get("role") == "dependent"
        and p.get("age") is not None
        and p["age"] < 18
        for p in applicants
    )

    has_tax_dependents = (
        state.get("is_dependent") == "No"
        and state.get("has_dependents") == "Yes"
    )

    possible_minor_child = (
        minor_applicant_present or has_tax_dependents
    )

    if (
        age >= 19
        and role in ("self", "partner")
        and possible_minor_child
        and show_medicaid_review
    ):
        add_benefit(
            "Florida Medicaid — Parent or Caretaker Review",
            medicaid_income_message
            + "If this adult is a parent or qualifying caretaker "
            "relative living with a dependent child under 18, "
            "this Medicaid category may be worth exploring. "
            "Other eligibility requirements apply.",
            "medicaid",
        )

    if not income_screen_available:
        add_benefit(
            "Marketplace Savings Review",
            f"{name} may have Marketplace coverage or savings options. "
            "The available information is not enough to compare income "
            "against the applicable tax household reliably.",
            "marketplace",
        )
        return benefits

    income_percentage = 100 * income / get_fpl(household_size)

    # in 2026, the usual income screen for ptc is 100%-400% of fpl.
    # the income-based csr screen generally extends up to 250% of fpl.
    if 100 <= income_percentage <= 400:
        if state.get("is_dependent") == "Yes" and role == "self":
            ptc_message = (
                "Based on the household size and annual income reported for "
                "the person claiming you as a tax dependent, that tax household "
                "may fall within the income range for a Premium Tax Credit. "
                "The claiming taxpayer generally handles Marketplace savings; "
                "a dependent cannot obtain a separate tax credit based only "
                "on their own income. Other eligibility rules apply."
            )
            csr_message = (
                "The reported tax household may also fall within the income "
                "range for Cost-Sharing Reductions. Eligible household members "
                "generally must enroll in a Silver Marketplace plan to receive "
                "these savings. Other eligibility rules apply."
            )
                
        elif state.get("is_dependent") == "Yes":
            ptc_message = (
                "The reported household income falls within the general "
                "Premium Tax Credit screening range. However, this "
                "applicant's tax household and individual eligibility "
                "must be confirmed through an official application."
            )

            csr_message = (
                "The reported household income falls within the general "
                "Cost-Sharing Reduction screening range. Eligibility "
                "for this applicant must be confirmed, and eligible "
                "members generally need a Silver Marketplace plan."
            )

        else:
            ptc_message = (
                f"Based on estimated household income, {name.lower()} may "
                "meet the income range for a Premium Tax Credit that can "
                "lower Marketplace premiums. Other eligibility rules apply, "
                "including tax filing, other coverage, and immigration status."
            )
            csr_message = (
                f"Based on estimated household income, {name.lower()} may "
                "meet the income range for Cost-Sharing Reductions. "
                "Eligible people generally must select a Silver Marketplace "
                "plan to receive these savings. Other requirements apply."
            )

        add_benefit("Premium Tax Credit (PTC)", ptc_message, "tax_credit")

        if income_percentage <= 250:
            add_benefit("Cost-Sharing Reductions (CSR)", csr_message, "cost_sharing")

    if not benefits:
        add_benefit(
            "Marketplace Coverage Options",
            f"{name} may be able to explore Marketplace health plans. "
            "The answers did not identify a specific savings program, "
            "but coverage and financial assistance can be reviewed "
            "through an official application.",
            "marketplace",
        )

    return benefits


# display potential benefits page
if st.session_state.page == BENEFITS_PAGE:
    st.caption("HEALTH INSURANCE QUESTIONNAIRE")
    st.title("Your Potential Benefits", anchor=False)
    st.write(
        "Based on your answers, here are some programs "
        "and savings opportunities the applicants may qualify for."
    )
    st.caption("These are preliminary suggestions, not official eligibility determinations.")

    applicants = get_applicants()
    household_size = get_household_size()
    income = get_estimated_annual_income()

    # a summary is possible for a dependent because the questionnaire already
    # asked for the claiming taxpayer's household size.
    # an unmarried or unclassified partner may belong to a different tax
    # household, but this does not erase the respondent's household answers.
    partner_household_uncertain = (
        st.session_state.get("include_partner", False)
        and (
            st.session_state.get("is_dependent") == "Yes"
            or st.session_state.get("married") != "Yes"
        )
    )

    if (
        household_size is not None
        and income is not None
        and not partner_household_uncertain
    ):
        income_percentage = 100 * income / get_fpl(household_size)

        with st.container(border=True):
            st.markdown("#### Your Household Summary",
                        anchors=False)
            col1, col2, col3 = st.columns(3)
            col1.metric("Household Size", household_size)
            col2.metric("Annual Income", f"USD {income:,.0f}")
            col3.metric("Income as % of FPL", f"{income_percentage:.0f}%")
            st.caption(
                "Based on 2026 estimated annual income and the 2025 "
                "federal poverty guidelines used for Marketplace coverage "
                "in 2026. Medicaid may use different household and income rules."
            )
            if st.session_state.get("is_dependent") == "Yes":
                st.caption(
                    "Household size comes from the tax household of the "
                    "person claiming you as a dependent. Financial assistance "
                    "is assessed for that tax household, not for you separately."
                )
            if partner_household_uncertain:
                st.caption(
                    "An included partner or spouse may have a different tax "
                    "household. This summary should not automatically be "
                    "used to estimate that person's savings."
                )
    else:
        st.info(
            "An income-based household comparison could not be completed "
            "reliably with these answers. The suggestions below are informational."
        )

    st.divider()

    for person in applicants:
        st.subheader(person["name"], anchor=False)
        benefits = get_potential_benefits(person, household_size, income, applicants)
        for benefit in benefits:
            with st.container(border=True):
                st.markdown(f"##### {benefit['title']}", anchors=False)
                st.write(benefit["message"])
                st.markdown(
                    "[Learn more about eligibility]" f"({benefit['source']})"
                )

    st.divider()
    st.warning(
        "These results do not guarantee eligibility. Actual benefits depend "
        "on additional factors, including citizenship or immigration status, "
        "tax filing information, current health coverage, and "
        "employer-sponsored insurance. Additional Marketplace savings "
        "restrictions apply in 2026."
    )
    st.caption(
        "Important for 2026: If advance Premium Tax Credit payments exceed "
        "the credit allowed on the final tax return, the full excess amount "
        "must be repaid. Report changes in income and household circumstances "
        "to the Marketplace."
    )
    st.markdown(
        "[Explore official Marketplace coverage options]"
        "(https://www.healthcare.gov/)"
    )

    col1, spacer, col2 = st.columns([1, 4, 1.8])
    with col1:
        if st.button("← Return"):
            st.session_state.page = NEXT_SECTION + 4
            st.rerun()

    with col2:
        if st.button("See Recommendations →", type="primary", width="stretch"):
            st.session_state.page = RECOMMENDATIONS_PAGE
            st.rerun()


# personalized plan explanations
# the comparison logic below is preserved from the original snippet.
def generate_plan_fit_explanations(plan, all_plans, answers):
    """
    Explain plan comparisons based on plan attributes, not model internals.
    """
    explanations = {
        "budget": "",
        "priorities": [],
    }

    premium = plan["monthly_premium"]
    budget = answers.get("monthly_budget")
    priorities = answers.get("priorities", [])

    # Monthly budget
    if budget is None:
        explanations["budget"] = (
            f"This plan costs USD {premium:,.2f} per month. "
            "No monthly budget was provided."
        )

    else:
        difference = abs(premium - budget)

        if premium < budget:
            explanations["budget"] = (
                f"At USD {premium:,.2f} per month, this plan "
                f"is USD {difference:,.2f} below your stated "
                f"monthly budget of USD {budget:,.2f}."
            )

        elif premium > budget:
            explanations["budget"] = (
                f"At USD {premium:,.2f} per month, this plan "
                f"is USD {difference:,.2f} above your stated "
                f"monthly budget of USD {budget:,.2f}."
            )

        else:
            explanations["budget"] = (
                f"At USD {premium:,.2f} per month, this plan "
                "matches your stated monthly budget exactly."
            )

    # Helper for comparing numeric costs across plans
    def compare_cost(field, label):
        available = [
            p for p in all_plans
            if p.get(field) is not None
        ]

        if plan.get(field) is None or not available:
            return (
                f"The {label} is not available in the prepared "
                "catalog for this plan."
            )

        lowest_plan = min(available, key=lambda p: p[field])

        current_value = plan[field]
        lowest_value = lowest_plan[field]

        difference = current_value - lowest_value

        if abs(difference) < 0.005:
            return (
                f"This plan has the lowest {label} among "
                f"the compared options, at USD {current_value:,.2f}."
            )

        return (
            f"This plan has a {label} of "
            f"USD {current_value:,.2f}, which is "
            f"USD {difference:,.2f} higher than "
            f"the lowest option ({lowest_plan['name']}: "
            f"USD {lowest_value:,.2f})."
        )

    # Explain every selected priority
    for priority in priorities:

        if priority == "Lower monthly premiums":
            message = compare_cost(
                "monthly_premium",
                "monthly premium",
            )

        elif priority == "Lower costs when receiving care":
            message = (
                compare_cost(
                    "deductible",
                    "household deductible"
                    if plan.get("covered_people", 1) > 1
                    else "individual deductible",
                )
                + " Deductibles are only one component of "
                "healthcare costs. Copayments and coinsurance "
                "are not compared in this prototype."
            )

        elif priority == "Protection against large medical bills":
            message = (
                compare_cost(
                    "moop",
                    "household out-of-pocket maximum"
                    if plan.get("covered_people", 1) > 1
                    else "individual out-of-pocket maximum",
                )
                + " This limit generally applies to covered "
                "in-network cost-sharing, not monthly premiums "
                "or non-covered services."
            )

        elif priority == "More freedom to choose doctors":
            referral_text = (
                "Specialist referrals are required."
                if plan["referrals_required"] is True
                else "Specialist referrals are not required."
                if plan["referrals_required"] is False
                else "Specialist referral requirements are not available."
            )

            if plan.get("out_of_network_covered") is True:
                network_text = (
                    "This plan includes out-of-network benefits."
                )

            elif plan.get("out_of_network_covered") is False:
                network_text = (
                    "This plan does not cover routine out-of-network care."
                )

            else:
                network_text = (
                    "Out-of-network coverage information is not available."
                )

            message = (
                f"{referral_text} {network_text} "
                "Provider availability and network participation "
                "should be confirmed with the insurer."
            )

        else:
            message = (
                "This priority has not yet been implemented "
                "in the comparison system."
            )

        explanations["priorities"].append({
            "priority": priority,
            "message": message,
        })

    return explanations


# recommendation cards
def render_recommendation_card(
    plan,
    all_plans,
    highlight=False,
    answers=None,
):

    container_key = (
        "best_plan_card"
        if highlight
        else f"ranked_plan_{plan['rank']}"
    )

    with st.container(border=True, key=container_key):

        if highlight:
            st.markdown(
                "**:green[:material/verified: BEST MATCH]**"
            )
        else:
            st.caption(f"RANK #{plan['rank']}")

        st.subheader(plan["name"], anchor=False)

        st.caption(
            f"{plan['issuer']}  ·  "
            f"{plan['metal_level']}  ·  "
            f"{plan['plan_type']}"
        )

        # Main plan metrics
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Monthly Premium",
            money(plan["monthly_premium"], 2)
        )

        col2.metric(
            "Household deductible" if plan.get("covered_people", 1) > 1 else "Individual deductible",
            money(plan["deductible"])
        )

        col3.metric(
            "Household maximum out-of-pocket" if plan.get("covered_people", 1) > 1 else "Individual maximum out-of-pocket",
            money(plan["moop"])
        )

        st.caption(
            f"Annual premium: "
            f"USD {plan['annual_premium']:,.2f}"
        )

        # Coverage characteristics
        referral_text = (
            "Required"
            if plan["referrals_required"] is True
            else "Not required" if plan["referrals_required"] is False
            else "Information not available"
        )

        
        if plan.get("out_of_network_covered") is True:
            network_text = "Covered"

        elif plan.get("out_of_network_covered") is False:
            network_text = "Not covered for routine care"

        else:
            network_text = "Information not available"


        st.markdown(
            f"**Specialist referrals:** {referral_text}"
        )

        st.markdown(
            f"**Out-of-network coverage:** {network_text}"
        )

        st.divider()

        # Personalized explanations
        explanations = generate_plan_fit_explanations(
            plan,
            all_plans,
            st.session_state if answers is None else answers
        )

        st.markdown(
            "#### How This Plan Relates to Your Preferences",
            anchors=False
        )

        st.markdown("**Monthly Budget**")
        st.write(explanations["budget"])

        for item in explanations["priorities"]:

            st.markdown(
                f"**{item['priority']}**"
            )

            st.write(item["message"])

        if not explanations["priorities"]:
            st.caption(
                "No personal priorities were selected."
            )


# altair pie charts
def make_pie_chart(plans, field, title):

    chart_data = pd.DataFrame([
        {
            "Plan": f"#{plan['rank']} {plan['name']}",
            "Value": plan[field]
        }
        for plan in plans
    ]).dropna(subset=["Value"])

    chart = (
        alt.Chart(chart_data)
        .mark_arc()
        .encode(
            theta=alt.Theta(
                "Value:Q",
                stack=True
            ),
            color=alt.Color(
                "Plan:N",
                scale=alt.Scale(
                    domain=[f"#{p['rank']} {p['name']}" for p in plans],
                    range=["#6595D0", "#75BDA7", "#E7B56D", "#B096C7", "#D38996"][:len(plans)]
                ),
                legend=alt.Legend(
                    orient="bottom",
                    title=None
                )
            ),
            tooltip=[
                alt.Tooltip("Plan:N", title="Plan"),
                alt.Tooltip(
                    "Value:Q",
                    title="Amount (USD)",
                    format=",.2f"
                )
            ],
            order=alt.Order(
                "Plan:N",
                sort="ascending"
            )
        )
        .properties(
            title=title,
            height=240
        )
    )

    return chart
def render_price_comparison_charts(plans):

    st.markdown(
        "### Cost Comparison",
        anchors=False
    )

    st.caption(
        "Compare the monthly premiums, applicable "
        "deductibles, and maximum out-of-pocket limits "
        "of the model-ranked plans. Missing limits are omitted from charts."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        chart = make_pie_chart(
            plans,
            "monthly_premium",
            "Monthly Premium"
        )
        st.altair_chart(chart, width="stretch")

    with col2:
        chart = make_pie_chart(
            plans,
            "deductible",
            "Deductible"
        )
        st.altair_chart(chart, width="stretch")

    with col3:
        chart = make_pie_chart(
            plans,
            "moop",
            "Maximum out-of-pocket"
        )
        st.altair_chart(chart, width="stretch")

    st.caption(
        "Pie slices represent each plan's share of the "
        "compared-plan total for that metric, not a breakdown "
        "of an individual plan's costs. Hover over each "
        "slice to view the corresponding dollar amount."
    )


# gets the model and makes the recommendation
def render_model_recommendations():

    """Show the ranked plans in the recommendation cards and charts."""
    from recommender.features import profile_from_answers
    from recommender.inference import recommend
    from recommender.presentation import plan_cards

    st.write("Up to five plans ranked by the saved LGBMRanker for your answers.")
    st.info(
        "Prototype: 2026 plans priced for the configured demonstration region, "
        "not verified for your ZIP. "
        "Premiums are before subsidies; rankings use synthetic preference labels."
    )
    
    if not any(st.session_state.get(key) for key in ["include_me", "include_partner", "include_dependents"]):
        st.info("Select at least one applicant in the questionnaire.")
        return
    try:
        signature = tuple((ROOT / name).stat().st_mtime_ns for name in [
            "models/insurance_ranker.txt", "models/feature_schema.json",
            "data/processed/plan_features.csv", "data/processed/rates.csv.gz"])
        assets = get_model_assets(signature)
        # Get the demo region from the settings file.
        # connect ZIP codes to the right region.
        config = json.loads((ROOT / "models/inference_config.json").read_text(encoding="utf-8"))
        area = config["rating_area_id"]
        if "monthly_budget" not in st.session_state:
            st.info("Complete the questionnaire before requesting plan comparisons.")
            return
        answers = dict(st.session_state)
        profile = profile_from_answers(
            answers, profile_id="current_session", rating_area_id=area, plan_year=config["plan_year"],
        )
        recommendations = plan_cards(recommend(profile, assets))
        if not recommendations:
            st.info("No matching plans fit this budget. Try increasing the budget or selecting another rating area.")
            return
        st.markdown("### Your Best Match", anchors=False)
        render_recommendation_card(recommendations[0], recommendations, highlight=True, answers=answers)
        if len(recommendations) > 1:
            st.markdown("### Other Recommended Plans", anchors=False)
            for plan in recommendations[1:]:
                render_recommendation_card(plan, recommendations, answers=answers)
        st.divider()
        render_price_comparison_charts(recommendations)
    except (ValueError, KeyError, FileNotFoundError) as error:
        st.warning(f"Unable to produce model comparisons: {error}")


# recommendations page
if st.session_state.page == RECOMMENDATIONS_PAGE:

    # light-green background for the best-ranked plan
    st.markdown(
        """
        <style>
        .st-key-best_plan_card {
            background-color: #EAF7EC !important;
            border: 1px solid #91D5A1 !important;
            border-radius: 14px !important;
            padding: 1rem !important;
        }

        .st-key-best_plan_card [data-testid="stMarkdownContainer"],
        .st-key-best_plan_card [data-testid="stMetric"] {
            color: #173A24 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.caption("HEALTH INSURANCE QUESTIONNAIRE")

    st.title(
        "Your Plan Recommendations",
        anchor=False
    )

    render_model_recommendations()

    st.divider()

    # navigation
    col1, spacer, col2 = st.columns([1, 4, 1.8])

    with col1:
        if st.button("← Return", key="recommendations_back"):
            st.session_state.page = BENEFITS_PAGE
            st.rerun()

    with col2:
        if st.button(
            "↻ Start Again",
            type="primary",
            width="stretch",
            key="recommendations_restart"
        ):
            for key in list(st.session_state.keys()):
                del st.session_state[key]

            st.session_state.page = 0
            st.rerun()