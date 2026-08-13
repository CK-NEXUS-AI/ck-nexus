# LLM Key Pool — auto-rotation, credit health, free-mode fallback

CK-NEXUS ใช้ key pool สำหรับ Live Mode / Development Council: ตรวจเครดิต key, สลับ key
อัตโนมัติเมื่อหมด/rate-limited, และ fallback เป็นโหมดฟรี (Ollama) เมื่อ key หมดทุกตัว

## วิธีใช้

```bash
# 1) เพิ่ม key ลง env (อย่างน้อย 1 ตัว)
export GROQ_API_KEY="gsk_..."
export GEMINI_API_KEY="AIza..."
# หรือกำหนดเองหลาย key พร้อม base_url/model
export CKNEXUS_LLM_KEYS='[
  {"id":"groq1","env_var":"GROQ_API_KEY","base_url":"https://api.groq.com/openai/v1","model":"llama-3.3-70b-versatile","free":true},
  {"id":"moonshot","env_var":"MOONSHOT_API_KEY","base_url":"https://api.moonshot.cn/v1","model":"kimi-k2-0711-preview","free":false}
]'

# 2) ตรวจเครดิต/สุขภาพของทุก key
python scripts/llm_keypool.py probe
python scripts/llm_keypool.py status --json
```

## พฤติกรรมอัตโนมัติ

- `GET {base}/models` เป็น health probe ราคาถูก: `200` = healthy, `401/402/403` = exhausted, อื่น = cooldown
- `429` = rate limit → cooldown 30s แล้วสลับ key ถัดไป
- 429 ที่เป็น quota ("insufficient balance"/"quota"/"suspended") → ถือว่า key หมดเครดิต → สลับทันที
- Round-robin + least-failed ordering; cooldown/exhaustion เก็บใน state JSON (`CKNEXUS_KEYPOOL_STATE`)
- key หมดทุกตัว → fallback เป็น local/free provider (Ollama) อัตโนมัติ
- Secret ไม่ถูกเก็บใน state file หรือแสดงใน status/CLI

## Free-tier providers ที่รองรับ (auto-discover จาก env)

| env | provider | model default |
|---|---|---|
| GROQ_API_KEY | Groq | llama-3.3-70b-versatile |
| MISTRAL_API_KEY | Mistral | mistral-small-latest |
| CEREBRAS_API_KEY | Cerebras | llama-3.3-70b |
| SAMBANOVA_API_KEY | SambaNova | Llama-3.3-70B-Instruct |
| OPENROUTER_API_KEY | OpenRouter | meta-llama/llama-3.3-70b-instruct:free |
| DEEPSEEK_API_KEY | DeepSeek | deepseek-chat |
| TOGETHER_API_KEY | Together | meta-llama/Llama-3.3-70B-Instruct-Turbo |
| ZHIPU_API_KEY | Zhipu GLM | glm-4-flash (ฟรี) |
| DASHSCOPE_API_KEY | Qwen | qwen-turbo |
| GEMINI_API_KEY | Google Gemini | gemini-2.5-flash |
| MOONSHOT_API_KEY | Moonshot Kimi | kimi-k2-0711-preview |
| OPENAI_API_KEY | OpenAI | gpt-4.1-mini |

หมายเหตุ: quota/rate limit ของ free tier เปลี่ยนตามเวลา — ตรวจที่หน้า pricing ของแต่ละ provider
