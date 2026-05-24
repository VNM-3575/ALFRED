import os


def get_llm(temperature=0.2):
    """Dynamically loads either a local inference engine or Gemini based on environment variables."""
    local_url = os.getenv("LOCAL_INFERENCE_URL")
    if local_url:
        from langchain_openai import ChatOpenAI
        primary_llm = ChatOpenAI(
            base_url=local_url,
            api_key=os.getenv("LOCAL_INFERENCE_KEY", "not-needed"),
            model=os.getenv("LOCAL_MODEL_NAME", "local-model"),
            temperature=temperature
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")
        primary_llm = ChatGoogleGenerativeAI(
            model=gemini_model, temperature=temperature)

    # Configure fallback models to prevent rate limits or token depletion mid-task
    fallbacks = []

    if os.getenv("GOOGLE_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        fallbacks.append(ChatGoogleGenerativeAI(
            model="gemini-1.5-pro", temperature=temperature))

    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        fallbacks.append(ChatOpenAI(
            model="gpt-4o-mini", temperature=temperature))

    if os.getenv("GROQ_API_KEY"):
        from langchain_groq import ChatGroq
        fallbacks.append(ChatGroq(
            model="llama3-70b-8192", temperature=temperature))

    if os.getenv("XAI_API_KEY"):
        from langchain_xai import ChatXAI
        fallbacks.append(ChatXAI(
            model="grok-beta", temperature=temperature))

    if fallbacks:
        return primary_llm.with_fallbacks(fallbacks)

    return primary_llm
