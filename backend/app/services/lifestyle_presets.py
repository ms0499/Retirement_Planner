from app.constants import DEFAULT_EXPENSE_CATEGORY_SPLIT, LIFESTYLE_PRESET_ANNUAL_SPEND
from app.models.assumptions import LifestylePreset


def default_expense_categories_for_preset(preset: LifestylePreset) -> list[dict]:
    """Prefill expense categories for onboarding from a lifestyle preset.
    Pre-retirement spending defaults to the same split at 80% of the
    post-retirement total (rough starting point, editable immediately)."""
    total = LIFESTYLE_PRESET_ANNUAL_SPEND.get(
        preset.value, LIFESTYLE_PRESET_ANNUAL_SPEND["comfortable"]
    )
    categories = []
    for category, fraction in DEFAULT_EXPENSE_CATEGORY_SPLIT.items():
        post = round(total * fraction, 2)
        categories.append(
            {
                "category": category,
                "pre_retirement_annual": round(post * 0.8, 2),
                "post_retirement_annual": post,
            }
        )
    return categories
