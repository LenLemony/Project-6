import pandas as pd

# Import dataset
df = pd.read_csv(
    r"C:\Users\FoodL\OneDrive\Desktop\benefits-and-cost-sharing-puf.csv",
    low_memory=False
)

print("Dataset shape:", df.shape)
print(df.head())
print(df.columns.tolist())

# Filter for FL specific data
fl_benefits = df[df["StateCode"] == "FL"].copy()

print("Florida dataset shape:", fl_benefits.shape)
print("Unique plans:", fl_benefits["PlanId"].nunique())
print("Unique benefits:", fl_benefits["BenefitName"].nunique())

# Check missing values in each column
print("Missing values:")
print(fl_benefits.isna().sum().sort_values(ascending=False))

# Check completely duplicated rows
print("\nDuplicate rows:")
print(fl_benefits.duplicated().sum())

# Check missing values in important identifiers
print("\nImportant fields:")
print(
    fl_benefits[
        ["PlanId", "BenefitName", "StandardComponentId"]
    ].isna().sum()
)

# Inspect copay formatting 
cost_columns = [
    "CopayInnTier1",
    "CopayInnTier2",
    "CopayOutofNet",
    "CoinsInnTier1",
    "CoinsInnTier2",
    "CoinsOutofNet"
]

for col in cost_columns:
    print(f"\n{col}")
    print("Data type:", fl_benefits[col].dtype)
    print(fl_benefits[col].value_counts(dropna=False).head(10))

for col in cost_columns:
    values = fl_benefits[col].dropna().astype("string")

    # Find values that are not simple dollar amounts or percentages
    special = values[
        ~values.str.fullmatch(r"\$[\d,]+(\.\d+)?|\d+(\.\d+)?%")
    ]

    print(f"\n{col}")
    print("Unique special values:", special.nunique())
    print(special.value_counts().head(15))

# Check/clean cost-sharing and co-pay columns
def clean_cost_sharing(df, columns):
    for col in columns:
        values = df[col].astype("string").str.strip()

        # Preserve special conditions
        df[col + "_NotApplicable"] = values.eq("Not Applicable").fillna(False)
        df[col + "_AfterDeductible"] = (
            values.str.contains("after deductible", case=False, na=False)
        )

        # Preserve the payment basis for copays
        if col.startswith("Copay"):
            df[col + "_PerDay"] = (
                values.str.contains("per Day", case=False, na=False)
            )
            df[col + "_PerStay"] = (
                values.str.contains("per Stay", case=False, na=False)
            )

        # Extract dollar amount or percentage
        amount = values.str.extract(r"(\d[\d,]*(?:\.\d+)?)", expand=False)
        amount = pd.to_numeric(
            amount.str.replace(",", "", regex=False),
            errors="coerce"
        )

        # "No Charge" means zero
        amount = amount.mask(values.str.startswith("No Charge", na=False), 0)

        # Store percentages as proportions
        if col.startswith("Coins"):
            amount = amount / 100

        df[col + "_Amount"] = amount

    return df

fl_benefits = clean_cost_sharing(fl_benefits, cost_columns)

# Validate clean
for col in cost_columns:
    original = fl_benefits[col].astype("string")

    unexpected = (
        original.notna()
        & ~original.eq("Not Applicable").fillna(False)
        & fl_benefits[col + "_Amount"].isna()
    )

    print(f"{col}: {unexpected.sum()} unexpected missing amounts")

    if unexpected.any():
        print(original[unexpected].value_counts().head(10))

# Check Yes/No columns
boolean_columns = [
    "IsEHB",
    "IsCovered",
    "QuantLimitOnSvc",
    "IsExclFromInnMOOP",
    "IsExclFromOonMOOP"
]

for col in boolean_columns:
    print(f"\n{col}")
    print(fl_benefits[col].value_counts(dropna=False))

# Convert yes/no columns to bool values accounting for NaN
yes_no_columns = [
    "IsEHB",
    "QuantLimitOnSvc",
    "IsExclFromInnMOOP",
    "IsExclFromOonMOOP"
]

for col in yes_no_columns:
    fl_benefits[col] = (
        fl_benefits[col]
        .map({"Yes": True, "No": False})
        .astype("boolean")
    )

# Convert coverage status
fl_benefits["IsCovered"] = (
    fl_benefits["IsCovered"]
    .map({"Covered": True, "Not Covered": False})
    .astype("boolean")
)

for col in boolean_columns:
    print(f"\n{col}")
    print("Data type:", fl_benefits[col].dtype)
    print(fl_benefits[col].value_counts(dropna=False))

# Check quantity limits columns
print("LimitQty data type:", fl_benefits["LimitQty"].dtype)

print("\nLimitQty values:")
print(fl_benefits["LimitQty"].value_counts(dropna=False).head(20))

print("\nLimitUnit values:")
print(fl_benefits["LimitUnit"].value_counts(dropna=False).head(20))

# Check quantity limit formatting
print("Benefits with quantity limits:")
print((fl_benefits["QuantLimitOnSvc"] == True).sum())

print("\nQuantity limits missing a quantity:")
print(
    (
        (fl_benefits["QuantLimitOnSvc"] == True)
        & fl_benefits["LimitQty"].isna()
    ).sum()
)

print("\nQuantity limits missing a unit:")
print(
    (
        (fl_benefits["QuantLimitOnSvc"] == True)
        & fl_benefits["LimitUnit"].isna()
    ).sum()
)

print("\nQuantities recorded without a Yes limit flag:")
print(
    (
        (fl_benefits["QuantLimitOnSvc"] != True).fillna(True)
        & fl_benefits["LimitQty"].notna()
    ).sum()
)

# Verify continuity with plan attributes
# Load previously cleaned Plan Attributes
fl_plans = pd.read_csv(
    r"C:\Users\FoodL\OneDrive\Desktop\GWC P1\fl_plan_attributes_cleaned_2026.csv",
    low_memory=False
)

# Compare identifiers with fl_plan_attributes_cleaned.csv
benefit_ids = set(fl_benefits["PlanId"].astype(str))
plan_ids = set(fl_plans["PlanId"].astype(str))

print("Plans in Benefits:", len(benefit_ids))
print("Plans in Plan Attributes:", len(plan_ids))

print(
    "Benefits plans missing from Plan Attributes:",
    len(benefit_ids - plan_ids)
)

print(
    "Plan Attributes plans missing from Benefits:",
    len(plan_ids - benefit_ids)
)

# Verify with plan attributes
identifiers = ["PlanId", "IssuerId", "StandardComponentId"]

benefits_keys = fl_benefits[identifiers].drop_duplicates()
plans_keys = fl_plans[identifiers].drop_duplicates()

print("Unique benefit identifier combinations:", len(benefits_keys))
print("Unique plan identifier combinations:", len(plans_keys))

print(
    "Benefit combinations missing from Plan Attributes:",
    len(
        benefits_keys.merge(
            plans_keys,
            on=identifiers,
            how="left",
            indicator=True
        ).query('_merge == "left_only"')
    )
)

# Export cleaned file
fl_benefits.to_csv(
    r"C:\Users\FoodL\OneDrive\Desktop\GWC P1\fl_benefits_cleaned_2026.csv",
    index=False
)


