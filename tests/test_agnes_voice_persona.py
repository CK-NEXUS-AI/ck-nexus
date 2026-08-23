from creator_app.agnes.voice import (
    ElevenLabsVoiceAdapter,
    EmotionMode,
    OpenAIVoiceAdapter,
    SemanticUtterance,
    SpeechContext,
    VoicePersonaPlanner,
)


def test_thai_warning_preserves_text_and_selects_urgent_delivery() -> None:
    planner = VoicePersonaPlanner()
    utterance = SemanticUtterance(
        text="ระบบพบความเสี่ยง กรุณาตรวจสอบก่อนดำเนินการต่อ",
        intent="warning",
        importance=0.95,
        key_phrases=("ตรวจสอบ",),
    )
    context = SpeechContext(audience_role="operator", urgency=0.9, locale="th-TH")

    plan = planner.plan(utterance, context)

    assert plan.text == utterance.text
    assert plan.emotion is EmotionMode.URGENT
    assert plan.lexical_form_preserved is True
    assert plan.thai_lexical_tone_preserved is True
    assert plan.rate > 1.0
    assert "Preserve Thai lexical tones" in plan.style_instruction


def test_relationship_changes_delivery_without_changing_persona() -> None:
    planner = VoicePersonaPlanner()
    utterance = SemanticUtterance(text="งานเสร็จเรียบร้อยแล้ว", intent="success")

    executive = planner.plan(
        utterance,
        SpeechContext(audience_role="executive", familiarity=0.2, locale="th-TH"),
    )
    familiar = planner.plan(
        utterance,
        SpeechContext(audience_role="peer", familiarity=0.9, locale="th-TH"),
    )

    assert executive.text == familiar.text == utterance.text
    assert "AGNES" in executive.style_instruction
    assert "AGNES" in familiar.style_instruction
    assert executive.rate != familiar.rate or executive.emotion != familiar.emotion


def test_sensitive_support_is_reassuring_and_slower() -> None:
    planner = VoicePersonaPlanner()
    plan = planner.plan(
        SemanticUtterance(text="ผมจะอธิบายทีละขั้นตอน", intent="support", importance=0.8),
        SpeechContext(sensitivity=0.9, locale="th-TH"),
    )

    assert plan.emotion is EmotionMode.REASSURING
    assert plan.rate < 1.0
    assert plan.energy < 0.6
    assert plan.pause_after_ms > plan.pause_before_ms


def test_semantic_ir_digest_is_deterministic() -> None:
    planner = VoicePersonaPlanner()
    utterance = SemanticUtterance(
        text="จุดนี้สำคัญ",
        intent="explain",
        importance=1.0,
        key_phrases=("สำคัญ",),
    )
    context = SpeechContext(locale="th-TH")

    first = planner.plan(utterance, context)
    second = planner.plan(utterance, context)

    assert first.to_semantic_ir() == second.to_semantic_ir()
    assert first.digest() == second.digest()
    assert len(first.digest()) == 64


def test_openai_adapter_maps_plan_without_mutating_text() -> None:
    plan = VoicePersonaPlanner().plan(
        SemanticUtterance(text="สวัสดีครับ", intent="greeting"),
        SpeechContext(locale="th-TH"),
    )

    request = OpenAIVoiceAdapter().build_request(plan)

    assert request["input"] == plan.text
    assert request["model"] == "gpt-4o-mini-tts"
    assert request["voice"] == "marin"
    assert request["speed"] == plan.rate
    assert "instructions" in request


def test_elevenlabs_adapter_uses_conservative_style_controls() -> None:
    plan = VoicePersonaPlanner().plan(
        SemanticUtterance(
            text="ยอดเยี่ยม งานผ่านแล้ว",
            intent="celebrate",
            emotion_hint=EmotionMode.CELEBRATORY,
        ),
        SpeechContext(locale="th-TH"),
    )

    request = ElevenLabsVoiceAdapter().build_request(plan)
    settings = request["voice_settings"]

    assert request["text"] == plan.text
    assert isinstance(settings, dict)
    assert 0.7 <= settings["speed"] <= 1.2
    assert settings["style"] <= 0.08
    assert settings["stability"] >= 0.35


def test_key_phrase_must_exist_in_text() -> None:
    try:
        SemanticUtterance(
            text="ข้อความจริง",
            intent="explain",
            key_phrases=("ไม่มีในข้อความ",),
        )
    except ValueError as exc:
        assert "key phrase" in str(exc)
    else:
        raise AssertionError("missing key phrase validation")
