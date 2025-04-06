import os

def get_config():
    """環境変数から設定を読み込む"""
    return {
        # AIモデレーション設定
        "ai_moderation": {
            "enabled": os.getenv("ENABLE_AI_MODERATION", "false").lower() == "true",
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "custom_bad_words": os.getenv("CUSTOM_BAD_WORDS", "").split(","),
            "action": os.getenv("MODERATION_ACTION", "warn"),  # warn, delete, mute, kick, ban
            "excluded_roles": [int(role_id) for role_id in os.getenv("MODERATION_ROLES", "").split(",") if role_id],
        },
        
        # 自動応答設定
        "auto_response": {
            "enabled": os.getenv("ENABLE_AUTO_RESPONSE", "false").lower() == "true",
            "response_chance": float(os.getenv("AUTO_RESPONSE_CHANCE", "0.1")),
            "cooldown": int(os.getenv("AUTO_RESPONSE_COOLDOWN", "60")),
            "ignore_bots": os.getenv("AUTO_RESPONSE_IGNORE_BOTS", "true").lower() == "true",
            "ignore_prefixes": os.getenv("AUTO_RESPONSE_IGNORE_PREFIXES", "!,?,/,.,- ").split(","),
            "max_context_length": int(os.getenv("AUTO_RESPONSE_MAX_CONTEXT", "10")),
            "ai_powered": os.getenv("AUTO_RESPONSE_AI_POWERED", "false").lower() == "true",
            "ai_model": os.getenv("AUTO_RESPONSE_AI_MODEL", "gpt-3.5-turbo"),
            "ai_temperature": float(os.getenv("AUTO_RESPONSE_AI_TEMPERATURE", "0.7")),
            "ai_persona": os.getenv("AUTO_RESPONSE_AI_PERSONA", "こんにちは、私はフレンドリーな助けになるボットです。ぜひお手伝いさせてください！"),
            "custom_responses": {
                "こんにちは": ["こんにちは！", "やあ、元気ですか？", "こんにちは、何かお手伝いできることはありますか？"],
                "おやすみ": ["おやすみなさい！", "良い夢を！", "また明日会いましょう！"],
                "ありがとう": ["どういたしまして！", "いつでもどうぞ！", "お役に立てて嬉しいです！"]
            }
        },
    } 