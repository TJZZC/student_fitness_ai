from dataclasses import dataclass
from typing import Dict, List


@dataclass
class FitnessScoreResult:
    bmi_score: float
    lung_capacity_score: float
    sprint_50m_score: float
    sit_and_reach_score: float
    standing_long_jump_score: float
    endurance_score: float
    strength_score: float
    total_score: float
    level: str
    weak_items: List[str]


def get_score_level(total_score: float) -> str:
    if total_score >= 90:
        return "优秀"
    elif total_score >= 80:
        return "良好"
    elif total_score >= 60:
        return "及格"
    return "不及格"


def rank_weak_items(item_scores: Dict[str, float]) -> List[str]:
    return [name for name, _ in sorted(item_scores.items(), key=lambda x: x[1])]


def score_by_interval(value, rules, reverse=False):
    """
    reverse=False: 数值越大越好
    reverse=True: 数值越小越好
    """
    if value is None:
        return 0.0

    if reverse:
        for threshold, score in rules:
            if value <= threshold:
                return float(score)
        return 0.0
    else:
        current_score = 0.0
        for threshold, score in rules:
            if value < threshold:
                return float(current_score)
            current_score = score
        return float(current_score)


def bmi_score_rule(bmi, gender):
    if bmi is None:
        return 0.0

    if gender == "男":
        if 18.5 <= bmi <= 23.0:
            return 100.0
        elif 17.5 <= bmi < 18.5 or 23.0 < bmi <= 24.0:
            return 80.0
        elif 16.5 <= bmi < 17.5 or 24.0 < bmi <= 25.0:
            return 60.0
        else:
            return 40.0
    else:
        if 18.0 <= bmi <= 23.0:
            return 100.0
        elif 17.0 <= bmi < 18.0 or 23.0 < bmi <= 24.0:
            return 80.0
        elif 16.0 <= bmi < 17.0 or 24.0 < bmi <= 25.0:
            return 60.0
        else:
            return 40.0


def get_demo_rules(grade, gender):
    return {
        "lung_capacity": [(2000, 60), (2600, 80), (3200, 100)],
        "sprint_50m": [(9.5, 100), (10.5, 80), (11.5, 60)],
        "sit_and_reach": [(5, 60), (10, 80), (15, 100)],
        "standing_long_jump": [(150, 60), (180, 80), (210, 100)],
        "endurance_run": [(300, 100), (330, 80), (360, 60)],
        "strength": [(20, 60), (35, 80), (50, 100)],
    }


def calculate_fitness_score(
    grade,
    gender,
    bmi,
    lung_capacity,
    sprint_50m,
    sit_and_reach,
    standing_long_jump,
    endurance_run,
    strength
):
    rules = get_demo_rules(grade, gender)

    bmi_score = bmi_score_rule(bmi, gender)
    lung_capacity_score = score_by_interval(lung_capacity, rules["lung_capacity"], reverse=False)
    sprint_50m_score = score_by_interval(sprint_50m, rules["sprint_50m"], reverse=True)
    sit_and_reach_score = score_by_interval(sit_and_reach, rules["sit_and_reach"], reverse=False)
    standing_long_jump_score = score_by_interval(standing_long_jump, rules["standing_long_jump"], reverse=False)
    endurance_score = score_by_interval(endurance_run, rules["endurance_run"], reverse=True)
    strength_score = score_by_interval(strength, rules["strength"], reverse=False)

    total_score = round(
        bmi_score * 0.15 +
        lung_capacity_score * 0.15 +
        sprint_50m_score * 0.20 +
        sit_and_reach_score * 0.10 +
        standing_long_jump_score * 0.10 +
        endurance_score * 0.20 +
        strength_score * 0.10,
        2
    )

    item_scores = {
        "BMI": bmi_score,
        "肺活量": lung_capacity_score,
        "50米跑": sprint_50m_score,
        "坐位体前屈": sit_and_reach_score,
        "立定跳远": standing_long_jump_score,
        "耐力跑": endurance_score,
        "力量项目": strength_score
    }

    return FitnessScoreResult(
        bmi_score=bmi_score,
        lung_capacity_score=lung_capacity_score,
        sprint_50m_score=sprint_50m_score,
        sit_and_reach_score=sit_and_reach_score,
        standing_long_jump_score=standing_long_jump_score,
        endurance_score=endurance_score,
        strength_score=strength_score,
        total_score=total_score,
        level=get_score_level(total_score),
        weak_items=rank_weak_items(item_scores)[:3]
    )
