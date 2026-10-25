import pandas as pd

# Import dataset
df = pd.read_csv(
    r"C:\Users\FoodL\OneDrive\Desktop\plan-attributes-puf.csv", 
    low_memory=False
)

print(df.shape)
print(df.head())

# Find Florida records
fl_plans = df[df["StateCode"] == "FL"].copy()

print("Florida records:", fl_plans.shape)

print(fl_plans[
    [
        "IssuerId",
        "IssuerMarketPlaceMarketingName",
        "StandardComponentId",
        "PlanId",
        "MetalLevel"
    ]
].head(10))

# Identify data types, check for missing values and duplicates
print(fl_plans.dtypes.to_string())

missing = fl_plans.isnull().sum()
print(missing[missing > 0].sort_values(ascending=False))

duplicates = fl_plans.duplicated().sum()
print("Duplicate rows:", duplicates)

# Check identifier columns and determine unique value 
columns = [
    "IssuerId",
    "StandardComponentId",
    "PlanId"
]

for col in columns:
    print(f"{col}: {fl_plans[col].nunique()} unique values")

print(
    fl_plans[
        ["IssuerId", "StandardComponentId", "PlanId"]
    ].head(10).to_string(index=False)
)

# Check identifier and plan characteristic columns for missing values
important_columns = [
    "IssuerId",
    "StandardComponentId",
    "PlanId",
    "MetalLevel",
    "PlanType",
    "ServiceAreaId"
]

print(fl_plans[important_columns].isnull().sum())

# Identify deductible and out-of-pocket (MOOP) collumns
for col in fl_plans.columns:
    if "Deductible" in col or "MOOP" in col:
        print(col)

# Find all MOOP columns
moop_columns = [
    col for col in fl_plans.columns
    if "MOOP" in col
]

# Rebuild MOOP columns from the original data
# Preserve which original values were not applicable
for col in moop_columns:
    original = df.loc[fl_plans.index, col].astype("string")

    fl_plans[col + "_NotApplicable"] = (
        original.str.contains("not applicable", case=False, na=False)
    )

    fl_plans[col] = pd.to_numeric(
        original
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace("per person", "", regex=False)
            .str.replace("per group", "", regex=False)
            .str.strip(),
        errors="coerce"
    )

# Verify the results
print(fl_plans[moop_columns].dtypes)

# Checking missing values before and after cleaning
before = df.loc[fl_plans.index, moop_columns].isna().sum()
after = fl_plans[moop_columns].isna().sum()

comparison = pd.DataFrame({
    "Before": before,
    "After": after
})

comparison["New_Missing"] = (
    comparison["After"] - comparison["Before"]
)

print(comparison[comparison["New_Missing"] > 0])

before = df.loc[fl_plans.index, moop_columns].isna().sum()
after = fl_plans[moop_columns].isna().sum()

comparison = pd.DataFrame({
    "Before": before,
    "After": after
})

comparison["New_Missing"] = comparison["After"] - comparison["Before"]

print(comparison[comparison["New_Missing"] > 0])

# Identify original values that failed conversion
column = "TEHBOutOfNetIndividualMOOP"

# Find rows that originally had values but became NaN
failed = (
    df.loc[fl_plans.index, column].notna()
    & fl_plans[column].isna()
)

# Show the original values that failed
print(df.loc[fl_plans.index, column][failed].value_counts())

# Check failed conversions caused by "Non Applicable" and create new indicator in cleaning loop
for col in comparison[comparison["New_Missing"] > 0].index:
    failed = (
        df.loc[fl_plans.index, col].notna()
        & fl_plans[col].isna()
    )

    print(f"\n{col}")
    print(df.loc[fl_plans.index, col][failed].value_counts())

# Check other plan attribute columns data types
print(fl_plans.dtypes.value_counts())

string_columns = fl_plans.select_dtypes(
    include=["str", "object", "string"]
).columns

print(string_columns.tolist())

# Examine deductible values
ded_columns = [
    col for col in fl_plans.columns
    if "Ded" in col and "DeductiblesIntegrated" not in col
]

print("Number of deductible-related columns:", len(ded_columns))

for col in [
    "TEHBDedInnTier1Individual",
    "TEHBDedInnTier1FamilyPerPerson",
    "TEHBDedOutOfNetIndividual"
]:
    print(f"\n{col}")
    print(fl_plans[col].value_counts(dropna=False).head(10))

# Clean deductible columns
ded_columns = [
    col for col in fl_plans.columns
    if col.startswith(("MEHBDed", "DEHBDed", "TEHBDed"))
]

# Keep original values for comparison
ded_original = fl_plans[ded_columns].copy()

for col in ded_columns:
    original = ded_original[col].astype("string")

    # Preserve Not Applicable information
    fl_plans[col + "_NotApplicable"] = (
        original.str.contains("not applicable", case=False, na=False)
    )

    # Convert monetary amounts to numeric values
    fl_plans[col] = pd.to_numeric(
        original
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace("per person", "", regex=False)
            .str.replace("per group", "", regex=False)
            .str.strip(),
        errors="coerce"
    )

# Verify deductible conversion
before = ded_original.isna().sum()
after = fl_plans[ded_columns].isna().sum()

comparison = pd.DataFrame({
    "Before": before,
    "After": after
})

comparison["New_Missing"] = comparison["After"] - comparison["Before"]

print(comparison[comparison["New_Missing"] > 0])

for col in comparison[comparison["New_Missing"] > 0].index:
    failed = ded_original[col].notna() & fl_plans[col].isna()

    unexpected = ded_original.loc[failed, col][
        ~ded_original.loc[failed, col]
            .astype("string")
            .str.contains("not applicable", case=False, na=False)
    ]

    if not unexpected.empty:
        print(f"\nUnexpected values in {col}:")
        print(unexpected.value_counts())

# Separate deductible amounts from coinsurance
ded_columns = [
    col for col in fl_plans.columns
    if col.startswith(("MEHBDed", "DEHBDed", "TEHBDed"))
    and not col.endswith("Coinsurance")
    and not col.endswith("_NotApplicable")
]

coinsurance_columns = [
    col for col in fl_plans.columns
    if col.startswith(("MEHBDed", "DEHBDed", "TEHBDed"))
    and col.endswith("Coinsurance")
]

# Restore and clean coinsurance columns, then check
for col in coinsurance_columns:
    original = df.loc[fl_plans.index, col].astype("string")

    fl_plans[col] = pd.to_numeric(
        original.str.replace("%", "", regex=False).str.strip(),
        errors="coerce"
    ) / 100

print(fl_plans[coinsurance_columns].head(10))

print(
    fl_plans[coinsurance_columns]
    .dtypes.value_counts()
)

print(
    fl_plans["TEHBDedInnTier1Coinsurance"]
    .value_counts(dropna=False).head(10)
)

# Check deductible and coinsurance conversions are valid
columns_to_check = ded_columns + coinsurance_columns

for col in columns_to_check:
    original = df.loc[fl_plans.index, col].astype("string")

    # Find values that became missing after cleaning
    failed = original.notna() & fl_plans[col].isna()

    # Exclude intentional Not Applicable conversions
    unexpected = original[
        failed & ~original.str.contains(
            "not applicable", case=False, na=False
        )
    ]

    if not unexpected.empty:
        print(f"\nUnexpected values in {col}:")
        print(unexpected.value_counts())

# Clean time stamp comumns
date_columns = [
    "ImportDate",
    "PlanEffectiveDate",
    "PlanExpirationDate"
]

for col in date_columns:
    print(f"\n{col}")
    print(fl_plans[col].head(5))
    print("Missing values:", fl_plans[col].isna().sum())

# Reformat date/time and check valid
date_columns = [
    "PlanEffectiveDate",
    "PlanExpirationDate"
]

for col in date_columns:
    fl_plans[col] = pd.to_datetime(
        fl_plans[col],
        format="%m/%d/%Y",
        errors="coerce"
    )

for col in date_columns:
    print(f"\n{col}")
    print("Data type:", fl_plans[col].dtype)
    print("Missing values:", fl_plans[col].isna().sum())
    print(fl_plans[col].head())

# Cleaning yes/no columns 
boolean_columns = [
    "IsHSAEligible",
    "DentalOnlyPlan",
    "IsNewPlan",
    "NationalNetwork",
    "IsReferralRequiredForSpecialist",
    "MedicalDrugDeductiblesIntegrated",
    "MedicalDrugMaximumOutofPocketIntegrated"
]

for col in boolean_columns:
    print(f"\n{col}")
    print(fl_plans[col].value_counts(dropna=False))

# Assign yes/no values to bool
boolean_columns = [
    "IsHSAEligible",
    "DentalOnlyPlan",
    "NationalNetwork",
    "IsReferralRequiredForSpecialist",
    "MedicalDrugDeductiblesIntegrated",
    "MedicalDrugMaximumOutofPocketIntegrated"
]

for col in boolean_columns:
    fl_plans[col] = fl_plans[col].map({
        "Yes": True,
        "No": False
    }).astype("boolean")

# Check identifiers
id_columns = [
    "IssuerId",
    "StandardComponentId",
    "PlanId",
    "ServiceAreaId",
    "NetworkId",
    "HIOSProductId"
]

for col in id_columns:
    print(f"\n{col}")
    print("Data type:", fl_plans[col].dtype)
    print("Missing values:", fl_plans[col].isna().sum())
    print("Unique values:", fl_plans[col].nunique())

# Update IssuerID to string
fl_plans["IssuerId"] = fl_plans["IssuerId"].astype("string")

# Final check 
print("Total rows:", len(fl_plans))
print("Unique PlanIds:", fl_plans["PlanId"].nunique())
print("Duplicate PlanIds:", fl_plans["PlanId"].duplicated().sum())

print("\nBoolean columns:")
print(fl_plans[boolean_columns].dtypes)

# Download clean CSV
fl_plans.to_csv(
    "fl_plan_attributes_cleaned_2026.csv",
    index=False
)

from pathlib import Path

output_file = Path("fl_plan_attributes_cleaned_2026.csv")

fl_plans.to_csv(output_file, index=False)

print("Saved to:", output_file.resolve())
print("File exists:", output_file.exists())