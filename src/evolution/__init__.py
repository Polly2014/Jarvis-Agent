"""
Evolution 模块

Phase 4: 让 Jarvis 学会"长大"——自我进化系统

子模块:
- pattern_detector: 交互模式检测
- skill_generator: Skill 自动生成
- skill_registry: Skill 生命周期管理
- sandbox: 沙盒验证
- preference_learner: 偏好学习
- metacognition: 元认知
"""

from .pattern_detector import PatternDetector, InteractionFingerprint, DetectedPattern
from .skill_registry import SkillRegistry, SkillInfo
from .skill_generator import SkillGenerator
from .sandbox import SkillSandbox, ValidationReport
from .preference_learner import PreferenceLearner, UserPreference
from .metacognition import Metacognition, ReflectionReport

__all__ = [
    "PatternDetector",
    "InteractionFingerprint",
    "DetectedPattern",
    "SkillRegistry",
    "SkillInfo",
    "SkillGenerator",
    "SkillSandbox",
    "ValidationReport",
    "PreferenceLearner",
    "UserPreference",
    "Metacognition",
    "ReflectionReport",
]
