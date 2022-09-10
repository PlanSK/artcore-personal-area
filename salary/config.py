HOURS_VARIANT = ('час', 'часа', 'часов')
DAYS_VARIANT = ('день', 'дня', 'дней')
MONTH_VARIANT = ('месяц','месяца','месяцев')
YEARS_VARIANT = ('год', 'года', 'лет')

REQUIRED_EXPERIENCE = 90
EXPERIENCE_BONUS = 200.0
PUBLICATION_BONUS = 100.0

ATTESTATION_BONUS = 200.0
DISCIPLINE_AWARD = 1000.0
HALL_CLEANING_BONUS = 400.0
HOOKAH_BONUS_RATIO = 0.2

ADMIN_BONUS_CRITERIA = {
    'bar' : [(0, 0.005), (3000, 0.01), (4000, 0.02), (6000, 0.025), (8000, 0.03)],
    'game_zone': [(0, 0.005), (20000, 0.01), (25000, 0.0125), (27500, 0.015), (30000, 0.0175)],
    'vr': [(0, 0.1), (1000, 0.12), (2000, 0.13), (3000, 0.14), (5000, 0.15)]
}

CASHIER_BONUS_CRITERIA = {
    'bar' : [(0, 0.03), (3000, 0.04), (4000, 0.05), (6000, 0.06), (8000, 0.07)],
    'game_zone': [(0, 0.005), (20000, 0.01), (25000, 0.0125), (27500, 0.015), (30000, 0.0175)],
    'vr': [(0, 0.05), (1000, 0.06), (2000, 0.065), (3000, 0.07), (5000, 0.075)]
}

DEFAULT_MISCONDUCT_ARTICLE_NUMBER = 1
DOCUMENTS_DIR_NAME = 'documents'