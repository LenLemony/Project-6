import streamlit as st
import pandas as pd
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
LOADING_PAGE = NEXT_SECTION + 5
RESULTS_PAGE = NEXT_SECTION + 6

# Sidebar progress

if 0 < st.session_state.page < LOADING_PAGE:

    current_page = st.session_state.page

    # Results page
    RESULTS_PAGE = NEXT_SECTION + 5

    # Three sections
    sections = [
        ("Location & Household", 1, 6),
        ("About the Applicants", 6, NEXT_SECTION),
        ("Healthcare Needs & Personal Preferences", NEXT_SECTION, RESULTS_PAGE)
    ]

    # Calculate progress
    total_steps = RESULTS_PAGE - 1

    progress = min(
        100,
        max(0, int((current_page - 1) / total_steps * 100))
    )

    # Only reach 100% on the results page
    if current_page >= RESULTS_PAGE:
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
    
# Question 01: ZIP Code
if st.session_state.page == 1:

    quest_header("01", "Location & Household")

    # Get the user's zipcode
    st.markdown("### What is your _ZIP Code?_ (Florida)", anchors=False)

    zip_code = st.text_input(
        "Enter the first 5 digits of your ZIP Code", 
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

    # Get the user's zipcode
    st.markdown("### Will someone else claim you as tax dependent?", anchors=False)

    is_dependent = st.radio(
        "Select the option that better reflects your situation", 
        ["Yes", "No", "Not Sure"],
        index = None,
        persist_state = "session",
        key = "is_dependent",
        )

    validity = is_dependent is not None

    if is_dependent == "Yes":
        st.markdown("### How many people are in the household of the person claiming you as a tax dependent?", anchors=False)

        total_household = st.number_input(
            "Include the person claiming you, their spouse (if married), you, and any other dependents they claim on their federal tax return.", 
            label_visibility = "visible",
            value=2, 
            placeholder="e.g., 3",
            step = 1,
            required = True,
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

    # Get the user's zipcode
    st.markdown("### Are you legally married?", anchors=False)

    is_married = st.radio(
        "Select the option that better reflects your situation", 
        ["Yes", "No"],
        index = None,
        persist_state = "session",
        key = "married"
        )
    
    validity = is_married is not None

    if is_married == "Yes":
        st.markdown("### Will you file a joint federal income tax return with your spouse?", anchors=False)

        fill_jointly = st.radio(
            "Select the option that better reflects your situation", 
            ["Yes", "No", "Not Sure"],
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

    # Get the user's zipcode
    st.markdown("### Will you claim _any dependents_ on your 2027 federal tax return?", anchors=False)

    has_dependents = st.radio(
        "Select the option that better reflects your situation", 
        ["Yes", "No", "Not Sure"],
        index = None,
        persist_state = "session",
        key = "has_dependents"
        )

    validity = has_dependents is not None

    if has_dependents == "Yes":
        st.markdown("### How many dependents will you claim?", anchors=False)

        total_dependents_tax = st.number_input(
            "Enter the number of dependents that you will claim", 
            label_visibility = "visible",
            value=1, 
            placeholder="e.g., 3",
            step = 1,
            required = True,
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

    # Get the user's zipcode
    st.markdown("### What is your estimated _annual household income_ for 2027?", anchors=False)

    income = st.number_input(
        "Enter your estimated annual household income", 
        label_visibility = "visible",
        value=60000, 
        placeholder="e.g., 60700",
        step = 10000,
        required = True,
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

    st.text("Please select at least one option")
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

    st.text("Please inform your age")
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
            st.error("Please select a valid age")

    st.markdown("### Do you _smoke_?", anchors=False)

    you_smoke = st.radio(
        "Select the option that better reflects your situation", 
        ["Yes", "No"],
        index = None,
        persist_state = "session",
        key = "you_smoke"
        )

    st.markdown("### Are you currently _pregnant_?", anchors=False)

    you_pregnant = st.radio(
        "Select the option that better reflects your situation", 
        ["Yes", "No", "Prefer not to say"],
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

    st.text("Please inform your spouse's age")
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
        "Select the option that better reflects your situation",
        ["Yes", "No"],
        label_visibility= "collapsed",
        index = None,
        persist_state = "session",
        key = "spouse_smoke"
        )

    st.markdown("### Is your spouse currently _pregnant_?", anchors=False)

    spouse_pregnant = st.radio(
        "Select the option that better reflects your situation", 
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
        "Please enter a valid age",
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
        "Select the option that best describes your household",
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
        "Select up to two priorities",
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
        "Select one option",
        [
            "Very important",
            "Somewhat important",
            "Not important"
        ],
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
        "Select one option",
        ["Yes", "No", "Not sure"],
        index=None,
        key="out_network",
        persist_state="session"
    )

    validity = out_network is not None

    navigation_buttons(validity)