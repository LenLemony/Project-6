import pandas as pd

# Import dataset
df = pd.read_csv(
    r"C:\Users\FoodL\OneDrive\Desktop\rate-puf.csv",
    low_memory=False
)

print("Dataset shape:", df.shape)
print(df.head())
print(df.columns.tolist())

# Locate Florida information
fl_rates = df[df["StateCode"] == "FL"].copy()

print("Florida dataset shape:", fl_rates.shape)
print("Unique plans:", fl_rates["PlanId"].nunique())
print("Data types:")
print(fl_rates.dtypes)

# Compare PlanID to fl_plan_attributes_cleaned_2026.csv
# Compare base plan identifiers
fl_plans = pd.read_csv(
    r"C:\Users\FoodL\OneDrive\Desktop\GWC P1\fl_plan_attributes_cleaned_2026.csv",
    low_memory=False
)
rate_ids = set(fl_rates["PlanId"].astype(str))
component_ids = set(fl_plans["StandardComponentId"].astype(str))

print("Unique Rate PUF PlanIds:", len(rate_ids))
print("Unique StandardComponentIds:", len(component_ids))

print(
    "Rate IDs missing from Plan Attributes:",
    len(rate_ids - component_ids)
)

print(
    "StandardComponentIds missing from Rate PUF:",
    len(component_ids - rate_ids)
)

# Check for missing values
print("Missing values:")
print(fl_rates.isna().sum().sort_values(ascending=False))

# Check completely duplicated rows
print("\nDuplicate rows:")
print(fl_rates.duplicated().sum())

# Check important identifiers
print("\nMissing identifiers:")
print(
    fl_rates[
        ["PlanId", "IssuerId", "RatingAreaId", "Age", "Tobacco"]
    ].isna().sum()
)

# Remove completely empty columns
fl_rates = fl_rates.dropna(axis=1, how="all")

# Check IndividualTobaccoRate
print(fl_rates["Tobacco"].value_counts(dropna=False))

print(
    fl_rates.groupby("Tobacco", dropna=False)[
        ["IndividualRate", "IndividualTobaccoRate"]
    ].agg(["count", "mean"])
)

# Check missing values
print(
    pd.crosstab(
        fl_rates["Tobacco"],
        fl_rates["IndividualTobaccoRate"].isna()
    )
)

# Check premium columns
premium_columns = [
    "IndividualRate",
    "IndividualTobaccoRate"
]

for col in premium_columns:
    print(f"\n{col}")

    print(fl_rates[col].describe())

    print("Negative values:", (fl_rates[col] < 0).sum())
    print("Zero values:", (fl_rates[col] == 0).sum())

# Investigate "$0 premium" value 
zero_rates = fl_rates[fl_rates["IndividualRate"] == 0]

print("Zero premiums by age:")
print(zero_rates["Age"].value_counts(dropna=False))

print("\nZero premiums by tobacco category:")
print(zero_rates["Tobacco"].value_counts(dropna=False))

print("\nSample records:")
print(
    zero_rates[
        ["PlanId", "Age", "RatingAreaId",
         "Tobacco", "IndividualRate"]
    ].head(10).to_string(index=False)
)

# Identify zero-premium plans
zero_plan_ids = set(zero_rates["PlanId"])

print("Unique plans with zero premiums:", len(zero_plan_ids))

zero_plan_attributes = fl_plans[
    fl_plans["StandardComponentId"].isin(zero_plan_ids)
]

print("\nDental-only status:")
print(zero_plan_attributes["DentalOnlyPlan"].value_counts(dropna=False))

print("\nMetal levels:")
print(zero_plan_attributes["MetalLevel"].value_counts(dropna=False))

print("\nPlan types:")
print(zero_plan_attributes["PlanType"].value_counts(dropna=False))

# Investigate "$9,999 premium" value
high_rates = fl_rates[fl_rates["IndividualRate"] == 9999]

print("Records with $9,999 premiums:", len(high_rates))
print("Unique plans:", high_rates["PlanId"].nunique())

print("\nAges:")
print(high_rates["Age"].value_counts().head(10))

print("\nTobacco categories:")
print(high_rates["Tobacco"].value_counts())

print("\nSample records:")
print(
    high_rates[
        ["PlanId", "Age", "RatingAreaId", "IndividualRate"]
    ].head(10).to_string(index=False)
)

high_plan_ids = set(high_rates["PlanId"])

high_plan_attributes = fl_plans[
    fl_plans["StandardComponentId"].isin(high_plan_ids)
]

print("Dental-only status:")
print(high_plan_attributes["DentalOnlyPlan"].value_counts(dropna=False))

print("\nMetal levels:")
print(high_plan_attributes["MetalLevel"].value_counts(dropna=False))

print("\nPlan types:")
print(high_plan_attributes["PlanType"].value_counts(dropna=False))

print("\nPlan names:")
print(high_plan_attributes["PlanMarketingName"].unique())

# Inspect date columns
date_columns = [
    "RateEffectiveDate",
    "RateExpirationDate"
]

for col in date_columns:
    print(f"\n{col}")
    print(fl_rates[col].head())
    print("Missing values:", fl_rates[col].isna().sum())

# Convert date columns to datetime format
date_columns = [
    "RateEffectiveDate",
    "RateExpirationDate"
]

for col in date_columns:
    fl_rates[col] = pd.to_datetime(
        fl_rates[col],
        format="%Y-%m-%d",
        errors="coerce"
    )

for col in date_columns:
    print(f"\n{col}")
    print("Data type:", fl_rates[col].dtype)
    print("Missing values:", fl_rates[col].isna().sum())
    print("Earliest date:", fl_rates[col].min())
    print("Latest date:", fl_rates[col].max())

print(
    "\nRecords where expiration precedes effective date:",
    (fl_rates["RateExpirationDate"] < fl_rates["RateEffectiveDate"]).sum()
)

# Final check for rate uniqueness (check for duplicates)
rate_keys = [
    "PlanId",
    "RatingAreaId",
    "Tobacco",
    "Age",
    "RateEffectiveDate",
    "RateExpirationDate"
]

print("Total records:", len(fl_rates))

print(
    "Duplicate rate combinations:",
    fl_rates.duplicated(subset=rate_keys).sum()
)

print(
    "Unique rate combinations:",
    len(fl_rates[rate_keys].drop_duplicates())
)

# Export cleaned file
fl_rates.to_csv(
    r"C:\Users\FoodL\OneDrive\Desktop\GWC P1\fl_rates_cleaned_2026.csv",
    index=False
)

print("Final shape:", fl_rates.shape)