import streamlit as st
import pandas as pd
import altair as alt
import time
import re

zip_codes = pd.read_csv("florida_zip_codes.csv")
zip_codes = zip_codes["ZIP Code"].astype(str).to_numpy()

# Define the header
def quest_header(section_num, section_title):

    # Questionnaire Title
    st.title("Health Insurance Questionnaire", anchor=False)

    # Present the first page
    st.markdown(f"## Section {section_num} | _{section_title}_", anchors=False)

# Define the first state

if "page" not in st.session_state:
    st.session_state.page = 0

if "zip_touched" not in st.session_state:
    st.session_state.zip_touched = False

if "people_selected" not in st.session_state:
    st.session_state.people_selected = False

# Setup for dependents pages

DEPENDENTS_START = 9

n_dependents = (
    st.session_state.get("total_dependents", 0)
    if st.session_state.get("include_dependents", False)
    else 0
)

NEXT_SECTION = DEPENDENTS_START + n_dependents
BENEFITS_PAGE = NEXT_SECTION + 5
RECOMMENDATIONS_PAGE = BENEFITS_PAGE + 1

# Sidebar progress
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

    # Only reach 100% on the results page
    if current_page >= BENEFITS_PAGE:
        progress = 100

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

# Define functions to track user interaction

def mark_zip_touched():
    st.session_state.zip_touched = True

def mark_people_selected():
    st.session_state.people_selected = True

# Navigation buttons 
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

# Landing Page
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
            use_container_width=True,
            icon=":material/arrow_forward:"
        ):
            st.session_state.page = 1
            st.rerun()

    st.caption(
        "This tool provides informational plan comparisons. "
        "Final eligibility and enrollment are determined "
        "through the official Marketplace."
    )

    st.caption(
        "Inspired by the [official HealthCare.gov plan comparison tool](https://www.healthcare.gov/see-plans/#/). " \
        "This is an independent project and is not affiliated with or endorsed by HealthCare.gov."
    )
    
# Question 01: ZIP Code
if st.session_state.page == 1:

    quest_header("01", "Location & Household")

    # Get the user's zipcode
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

# Question 02: Claimed as a Dependent
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

# Question 03: Married
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

# Question 04: Claim Dependents
if st.session_state.page == 4:

    quest_header("01", "Location & Household")

    st.markdown("### Will you claim _any dependents_ on your 2027 federal tax return?", anchors=False)

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

# Question 05: Estimated Annual Household Income
if st.session_state.page == 5:

    quest_header("01", "Location & Household")

    st.markdown("### What is your estimated _annual household income_ for 2027?", anchors=False)

    income = st.number_input(
        r"Enter your household's expected income for 2027.",
        help = (
            r"Enter the total income your household expects to receive "
            r"throughout 2027, not just your personal income. "
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

# Question 06: Who needs insurance
if st.session_state.page == 6:

    quest_header("02", "About the Applicants")

    # Get the amount of people wanting to get health insurance
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

# Question 07: Questions about User
if st.session_state.page == 7:

    quest_header("02", "About the Applicants")

    # Get the amount of people wanting to get health insurance
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
        "",
        ["Yes", "No"],
        label_visibility="collapsed",
        index = None,
        persist_state = "session",
        key = "you_smoke"
        )

    st.markdown("### Are you currently _pregnant_?", anchors=False)

    you_pregnant = st.radio(
        "", 
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

# Question 08: Questions about Spouse
if st.session_state.page == 8:

    quest_header("02", "About the Applicants")

    # Get the amount of people wanting to get health insurance
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

# Question 09: Questions about Dependents
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
        f"### Does this dependent _smoke_?",
        anchors=False
    )
    pregnant = st.radio(
        "Is this dependent currently pregnant?",
        ["Yes", "No", "Prefer not to say"],
        index=None,
        key=f"dependent_{i}_pregnant",
        persist_state="session"
    )

    validity = smoke is not None and pregnant is not None

    # Determine previous page
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

# Question 10: Expected Healthcare Usage
if st.session_state.page == NEXT_SECTION:

    quest_header("03", "Healthcare Needs & Preferences")

    st.markdown(
        "### How much healthcare do you and your family "
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

# Question 11: Personal Priorities
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

# Question 12: Monthly Budget
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

# Question 13: Specialist Referrals
if st.session_state.page == NEXT_SECTION + 3:

    quest_header("03", "Healthcare Needs & Preferences")

    st.markdown(
        "### How important is it to see specialists "
        "_without a referral_?",
            anchors=False
    )

    referral_preference = st.radio(
        "",
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

# Question 14: Out-of-Network Coverage
if st.session_state.page == NEXT_SECTION + 4:

    quest_header("03", "Healthcare Needs & Preferences")

    st.markdown(
        "### Do you need coverage for non-emergency "
        "care _outside your provider network_?",
        anchors = False
    )

    out_network = st.radio(
        "",
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
            use_container_width=True
        ):
            st.session_state.page = BENEFITS_PAGE
            st.rerun()

# Results Page: Potential Benefits

OFFICIAL_SOURCES = {
    "marketplace": "https://www.healthcare.gov/lower-costs/",
    "tax_credit": "https://www.irs.gov/credits-deductions/premium-tax-credit-ptc-overview",
    "cost_sharing": "https://www.healthcare.gov/lower-costs/save-on-out-of-pocket-costs/",
    "kidcare": "https://www.floridakidcare.org/requirements/",
    "medicaid": "https://www.myflfamilies.com/medicaid/",
    "medicare": "https://www.healthcare.gov/medicare/medicare-and-the-marketplace/"
}

# 2026 Federal Poverty Level (used for 2027 Marketplace coverage)
def get_fpl(household_size):
    return 15960 + 5680 * (household_size - 1)

# Estimate the tax household size when the answers allow it
def get_household_size():
    state = st.session_state

    if state.get("is_dependent") != "No":
        return None

    if state.get("has_dependents") not in ("Yes", "No"):
        return None

    married = state.get("married")

    if married not in ("Yes", "No"):
        return None

    if married == "Yes" and state.get("jointly") != "Yes":
        return None

    household = 1

    if married == "Yes":
        household += 1

    if state.get("has_dependents") == "Yes":
        household += int(state.get("total_dependents_tax", 0) or 0)

    return household

# Collect applicants using existing questionnaire responses
def get_applicants():
    state = st.session_state
    applicants = []

    if state.get("include_me", False):
        applicants.append({
            "name": "You",
            "age": state.get("you_age"),
            "pregnant": state.get("you_pregnant") == "Yes",
            "role": "self"
        })

    if state.get("include_partner", False):
        relationship = (
            "Your spouse"
            if state.get("married") == "Yes"
            else "Your partner"
        )

        applicants.append({
            "name": relationship,
            "age": state.get("spouse_age"),
            "pregnant": state.get("spouse_pregnant") == "Yes",
            "role": "partner"
        })

    if state.get("include_dependents", False):
        n = int(state.get("total_dependents", 0) or 0)

        for i in range(n):
            applicants.append({
                "name": f"Dependent {i + 1}",
                "age": state.get(f"dependent_{i}_age"),
                "pregnant": (
                    state.get(f"dependent_{i}_pregnant") == "Yes"
                ),
                "role": "dependent"
            })

    return applicants

# Identify potential benefits for each applicant
def get_potential_benefits(person, household_size, income, applicants):

    benefits = []
    name = person["name"]
    age = person.get("age")
    role = person.get("role")
    state = st.session_state

    def add_benefit(title, message, source):
        benefits.append({
            "title": title,
            "message": message,
            "source": OFFICIAL_SOURCES[source]
        })

    if age is None:
        add_benefit(
            "Marketplace Coverage Review",
            f"Coverage options for {name.lower()} can be explored through the "
            "official Marketplace application. More information is needed.",
            "marketplace"
        )
        return benefits

    # Florida KidCare
    if age < 19:
        add_benefit(
            "Florida KidCare",
            f"{name} may qualify for coverage through Florida KidCare. "
            "Free, subsidized, or full-pay options may apply depending on "
            "income and other eligibility requirements.",
            "kidcare"
        )

    # Pregnancy-related Medicaid
    if person.get("pregnant") is True:
        add_benefit(
            "Florida Pregnancy Medicaid",
            f"{name} may qualify for pregnancy-related Medicaid coverage. "
            "Income, household composition, and other requirements apply.",
            "medicaid"
        )

    # Children's coverage is reviewed separately
    if age < 19:
        return benefits

    # Medicare
    if age >= 65:
        add_benefit(
            "Medicare Eligibility Review",
            f"{name} may qualify for Medicare based on age. "
            "Eligibility and any Part A premium depend on additional rules. "
            "If Medicare is not available, ask about Marketplace options.",
            "medicare"
        )
        return benefits

    # An unmarried partner may belong to a different tax household
    unmarried_partner_applying = (
        state.get("include_partner", False)
        and state.get("married") != "Yes"
    )

    unknown_tax_household = (
        household_size is None
        or income is None
        or unmarried_partner_applying
        or (
            role == "partner"
            and state.get("married") != "Yes"
        )
    )

    if unknown_tax_household:
        add_benefit(
            "Marketplace Savings Review",
            f"{name} may have Marketplace coverage or savings options. "
            "More information about the applicable tax household and "
            "income is needed before estimating income-based assistance.",
            "marketplace"
        )
        return benefits

    # Estimated household income as a percentage of FPL
    income_percentage = 100 * income / get_fpl(household_size)

    # Premium Tax Credit: income-based screening for 2027
    if 100 <= income_percentage <= 400:
        add_benefit(
            "Premium Tax Credit (APTC)",
            f"Based on estimated household income, {name.lower()} may meet "
            "the income range for a Premium Tax Credit that can lower "
            "Marketplace premiums. Other eligibility rules apply, "
            "including tax filing, other coverage, and immigration status.",
            "tax_credit"
        )

        # Income-based Cost-Sharing Reductions
        if income_percentage <= 250:
            add_benefit(
                "Cost-Sharing Reductions (CSR)",
                f"Based on estimated household income, {name.lower()} may "
                "meet the income range for Cost-Sharing Reductions. "
                "To receive income-based CSR savings on deductibles and "
                "copayments, an eligible person generally must choose a "
                "Silver Marketplace plan. Other requirements apply.",
                "cost_sharing"
            )

    # Florida Medicaid preliminary income screening
    # Official DCF monthly limits effective April 2026–March 2027.
    # These figures must be reviewed when updated limits are published.
    # Annual income / 12 is only an approximation; actual Medicaid
    # countable income and household rules may be different.
    florida_family_medicaid_monthly_limits = {
        1: 356,
        2: 478,
        3: 600,
        4: 723,
        5: 846,
        6: 968,
        7: 1091,
        8: 1214
    }

    published_limit = florida_family_medicaid_monthly_limits.get(
        household_size
    )

    low_income_for_medicaid_review = (
        published_limit is not None
        and income >= 0
        and income / 12 <= published_limit
    )

    # Medicaid category for certain 19- and 20-year-olds
    if age in (19, 20) and low_income_for_medicaid_review:
        add_benefit(
            "Florida Medicaid — Ages 19–20 Review",
            f"{name} may be worth screening for Florida Medicaid's "
            "19–20 age category. The reported annual income is low "
            "enough for a preliminary review against the published "
            "monthly income table, but eligibility is not confirmed.",
            "medicaid"
        )

    # Possible parent or caretaker Medicaid category
    minor_applicant_present = any(
        p.get("role") == "dependent"
        and p.get("age") is not None
        and p["age"] < 18
        for p in applicants
    )

    if (
        age >= 21
        and role in ("self", "partner")
        and minor_applicant_present
        and low_income_for_medicaid_review
    ):
        add_benefit(
            "Florida Medicaid — Parent or Caretaker Review",
            f"{name} may be worth screening for Florida Medicaid if "
            "they are an eligible parent or caretaker living with a "
            "minor child. The actual Medicaid household, countable "
            "income, and other requirements must be verified.",
            "medicaid"
        )

    # General fallback when no specific benefit is suggested
    if not benefits:
        add_benefit(
            "Marketplace Coverage Options",
            f"{name} may be able to explore Marketplace health plans. "
            "The available answers did not identify a specific savings "
            "program for this person; coverage and savings eligibility "
            "must be checked through an official application.",
            "marketplace"
        )

    return benefits

# Display Results Page
if st.session_state.page == BENEFITS_PAGE:

    st.caption("HEALTH INSURANCE QUESTIONNAIRE")

    st.title("Your Potential Benefits", anchor=False)

    st.write(
        "Based on your answers, here are some programs "
        "and savings opportunities you and your family "
        "may qualify for."
    )

    st.caption(
        "These are preliminary suggestions, not official "
        "eligibility determinations."
    )

    applicants = get_applicants()
    household_size = get_household_size()
    income = st.session_state.get("income")

    # Household summary
    if household_size is not None and income is not None:

        income_percentage = (
            100 * income / get_fpl(household_size)
        )

        with st.container(border=True):
            st.markdown("#### Your Household Summary")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Household Size",
                household_size
            )

            col2.metric(
                "Annual Income",
                f"USD {income:,.0f}"
            )

            col3.metric(
                "Income as % of FPL",
                f"{income_percentage:.0f}%"
            )

            st.caption(
                "Based on estimated 2027 household income "
                "and 2026 federal poverty guidelines."
            )

    else:
        st.info(
            "Your tax household size could not be reliably "
            "estimated from your answers. The suggestions "
            "below are informational."
        )

    st.divider()

    # Show benefits for each person
    for person in applicants:

        st.subheader(person["name"], anchor=False)

        benefits = get_potential_benefits(
            person,
            household_size,
            income,
            applicants
        )

        for benefit in benefits:

            with st.container(border=True):

                st.markdown(
                    f"##### {benefit['title']}",
                    anchors=False
                )

                st.write(benefit["message"])

                st.markdown(
                    "[Learn more about eligibility]"
                    f"({benefit['source']})"
                )

    st.divider()

    st.warning(
        "These results do not guarantee eligibility. "
        "Actual benefits depend on additional factors, "
        "including citizenship or immigration status, "
        "tax filing information, current health coverage, "
        "and employer-sponsored insurance. Additional "
        "Marketplace savings restrictions apply in 2027."
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
        if st.button(
            "See Recommendations →",
            type="primary",
            use_container_width=True
        ):
            st.session_state.page = RECOMMENDATIONS_PAGE
            st.rerun()

# Placeholder Plans and Ranking
def get_placeholder_recommendations():
    """
    Rank three fictional plans using questionnaire preferences.

    This is a demonstration only.
    No real Marketplace prices or plan availability are verified.
    """

    priorities = set(st.session_state.get("priorities", []))
    usage = st.session_state.get("healthcare_usage", "Not sure")
    budget = st.session_state.get("monthly_budget", 500)

    referral_preference = st.session_state.get(
        "referral_preference", "Not important"
    )

    out_network_preference = st.session_state.get(
        "out_network", "Not sure"
    )

    plans = [
        {
            "name": "Plan 1",
            "issuer": "Sample Insurance Company",
            "plan_type": "HMO",
            "metal_level": "Bronze",
            "monthly_premium": 295.00,
            "deductible": 7500.00,
            "moop": 9200.00,
            "referrals_required": True,
            "out_of_network_covered": False,
            "description": (
                "A lower-premium option designed for people who "
                "prefer smaller monthly payments and expect "
                "relatively limited healthcare usage."
            ),
        },
        {
            "name": "Plan 2",
            "issuer": "Sample Insurance Company",
            "plan_type": "EPO",
            "metal_level": "Silver",
            "monthly_premium": 430.00,
            "deductible": 4200.00,
            "moop": 7800.00,
            "referrals_required": False,
            "out_of_network_covered": False,
            "description": (
                "A balanced option between monthly premiums "
                "and costs when receiving medical care."
            ),
        },
        {
            "name": "Plan 3",
            "issuer": "Sample Insurance Company",
            "plan_type": "PPO",
            "metal_level": "Gold",
            "monthly_premium": 590.00,
            "deductible": 1500.00,
            "moop": 5500.00,
            "referrals_required": False,
            "out_of_network_covered": True,
            "description": (
                "A higher-premium option with a lower deductible "
                "and more flexibility for accessing healthcare."
            ),
        },
    ]

    def lower_cost_score(value, field):
        values = [plan[field] for plan in plans]
        minimum = min(values)
        maximum = max(values)

        if maximum == minimum:
            return 1.0

        return (maximum - value) / (maximum - minimum)

    for plan in plans:

        score = 0.0
        reasons = []

        premium = plan["monthly_premium"]
        deductible = plan["deductible"]
        moop = plan["moop"]

        # Budget preference
        if premium <= budget:
            score += 20
            reasons.append("Within your stated monthly budget.")
        else:
            score -= min(20, (premium - budget) / 20)

        # Personal priorities
        if "Lower monthly premiums" in priorities:
            score += 30 * lower_cost_score(
                premium, "monthly_premium"
            )

        if "Lower costs when receiving care" in priorities:
            score += 30 * lower_cost_score(
                deductible, "deductible"
            )

        if "Protection against large medical bills" in priorities:
            score += 30 * lower_cost_score(
                moop, "moop"
            )

        if "More freedom to choose doctors" in priorities:
            if plan["out_of_network_covered"]:
                score += 25
                reasons.append(
                    "Includes out-of-network benefits."
                )
            elif not plan["referrals_required"]:
                score += 10

        # Expected healthcare usage
        if usage.startswith("High"):
            score += 15 * lower_cost_score(
                deductible, "deductible"
            )
            score += 15 * lower_cost_score(
                moop, "moop"
            )

        elif usage.startswith("Moderate"):
            score += 15 * lower_cost_score(
                deductible, "deductible"
            )

        elif usage.startswith("Low"):
            score += 15 * lower_cost_score(
                premium, "monthly_premium"
            )

        # Specialist referral preference
        if referral_preference == "Very important":
            if not plan["referrals_required"]:
                score += 20
                reasons.append(
                    "Specialist referrals are not required."
                )

        elif referral_preference == "Somewhat important":
            if not plan["referrals_required"]:
                score += 10

        # Out-of-network preference
        if out_network_preference == "Yes":
            if plan["out_of_network_covered"]:
                score += 25
                reasons.append(
                    "Includes out-of-network coverage."
                )

        plan["score"] = round(score, 2)
        plan["annual_premium"] = premium * 12

        if not reasons:
            reasons.append(
                "Compare this plan's sample costs and coverage "
                "rules with your healthcare preferences."
            )

        plan["reasons"] = list(dict.fromkeys(reasons))[:3]

    ranked = sorted(
        plans,
        key=lambda plan: (
            -plan["score"],
            plan["monthly_premium"]
        )
    )

    for rank, plan in enumerate(ranked, start=1):
        plan["rank"] = rank

    return ranked

# Personalized Plan Explanations
def generate_plan_fit_explanations(plan, all_plans, answers):
    """
    Explain how a plan compares with the user's monthly
    budget and each selected priority.

    Explanations are based on plan attributes and comparisons,
    not on the recommendation model's internal reasoning.
    """

    explanations = {
        "budget": "",
        "priorities": []
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

        lowest_plan = min(
            all_plans,
            key=lambda p: p[field]
        )

        current_value = plan[field]
        lowest_value = lowest_plan[field]

        difference = current_value - lowest_value

        if abs(difference) < 0.005:
            return (
                f"This plan has the lowest {label} among "
                f"the compared options, at "
                f"USD {current_value:,.2f}."
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
                "monthly premium"
            )

        elif priority == "Lower costs when receiving care":

            message = (
                compare_cost(
                    "deductible",
                    "individual deductible"
                )
                + " Deductibles are only one component of "
                "healthcare costs. Copayments and coinsurance "
                "are not compared in this prototype."
            )

        elif priority == "Protection against large medical bills":

            message = (
                compare_cost(
                    "moop",
                    "individual out-of-pocket maximum"
                )
                + " This limit generally applies to covered "
                "in-network cost-sharing, not monthly premiums "
                "or non-covered services."
            )


        elif priority == "More freedom to choose doctors":

            referral_text = (
                "Specialist referrals are required."
                if plan["referrals_required"]
                else "Specialist referrals are not required."
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
            "message": message
        })

    return explanations

# Recommendation Cards
def render_recommendation_card(
    plan,
    all_plans,
    highlight=False
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
            f"USD {plan['monthly_premium']:,.2f}"
        )

        col2.metric(
            "Deductible",
            f"USD {plan['deductible']:,.0f}"
        )

        col3.metric(
            "Max Out-of-Pocket",
            f"USD {plan['moop']:,.0f}"
        )

        st.caption(
            f"Annual premium: "
            f"USD {plan['annual_premium']:,.2f}"
        )

        # Coverage characteristics
        referral_text = (
            "Required"
            if plan["referrals_required"]
            else "Not required"
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
            st.session_state
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

# Altair Pie Charts
def make_pie_chart(plans, field, title):

    chart_data = pd.DataFrame([
        {
            "Plan": plan["name"],
            "Value": plan[field]
        }
        for plan in plans
    ])

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
                    domain=["Plan 1", "Plan 2", "Plan 3"],
                    range=["#6595D0", "#75BDA7", "#E7B56D"]
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
        "Compare the monthly premiums, individual "
        "deductibles, and maximum out-of-pocket limits "
        "of the three sample plans."
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
            "Max Out-of-Pocket"
        )
        st.altair_chart(chart, width="stretch")

    st.caption(
        "Pie slices represent each plan's share of the "
        "three-plan total for that metric, not a breakdown "
        "of an individual plan's costs. Hover over each "
        "slice to view the corresponding dollar amount."
    )

# Health Insurance Recommendations Page
if st.session_state.page == RECOMMENDATIONS_PAGE:

    # Light-green background for the best-ranked plan
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

    st.write(
        "Based on your answers, here are three sample "
        "health insurance plans ranked by how well they "
        "match your preferences."
    )

    st.info(
        "Dylan, please alter this to account for your model"
    )

    if (
        st.session_state.get("include_partner", False)
        or st.session_state.get("include_dependents", False)
    ):
        st.caption(
            "The current pricing pipeline supports one "
            "applicant only. Household pricing is not yet "
            "implemented."
        )

    # Generate and rank placeholder recommendations
    recommendations = get_placeholder_recommendations()

    best_plan = recommendations[0]
    other_plans = recommendations[1:]

    # First-ranked plan
    st.markdown("### Your Best Match", anchors=False)

    render_recommendation_card(
        best_plan,
        recommendations,
        highlight=True
    )

    # Remaining ranked plans
    st.markdown(
        "### Other Recommended Plans",
        anchors=False
    )

    for plan in other_plans:
        render_recommendation_card(
            plan,
            recommendations,
            highlight=False
        )

    # Cost comparison charts
    st.divider()

    render_price_comparison_charts(recommendations)

    st.divider()

    # Navigation
    col1, spacer, col2 = st.columns([1, 4, 1.8])

    with col1:
        if st.button("← Return", key="recommendations_back"):
            st.session_state.page = BENEFITS_PAGE
            st.rerun()

    with col2:
        if st.button(
            "↻ Start Again",
            type="primary",
            use_container_width=True,
            key="recommendations_restart"
        ):
            for key in list(st.session_state.keys()):
                del st.session_state[key]

            st.session_state.page = 0
            st.rerun()