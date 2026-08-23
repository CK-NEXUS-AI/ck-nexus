"""AGNES voice persona control layer.

Text remains the semantic source of truth. This package only resolves persona
parameters for downstream speech providers and does not perform synthesis.
"""

from .persona import VoiceContext, VoiceMode, VoiceProfile, resolve_voice_profile

__all__ = ["VoiceContext", "VoiceMode", "VoiceProfile", "resolve_voice_profile"]
