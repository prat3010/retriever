export interface ProviderDef {
  label: string;
  value: string;
  baseUrl: string;
  defaultModel: string;
}

export const PROVIDERS: ProviderDef[] = [
  {
    label: "OpenRouter",
    value: "openrouter",
    baseUrl: "https://openrouter.ai/api/v1",
    defaultModel: "openai/gpt-4o",
  },
  {
    label: "OpenAI",
    value: "openai",
    baseUrl: "https://api.openai.com/v1",
    defaultModel: "gpt-4o",
  },
  {
    label: "Google Gemini",
    value: "gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
    defaultModel: "gemini-2.5-flash",
  },
  {
    label: "Anthropic",
    value: "anthropic",
    baseUrl: "https://api.anthropic.com",
    defaultModel: "claude-3-5-sonnet-20240620",
  },
  {
    label: "DeepSeek",
    value: "deepseek",
    baseUrl: "https://api.deepseek.com",
    defaultModel: "deepseek-chat",
  },
  {
    label: "Groq",
    value: "groq",
    baseUrl: "https://api.groq.com/openai/v1",
    defaultModel: "llama-3.3-70b-versatile",
  },
  {
    label: "Together AI",
    value: "together",
    baseUrl: "https://api.together.xyz/v1",
    defaultModel: "mistralai/Mixtral-8x7B-Instruct-v0.1",
  },
  {
    label: "Fireworks",
    value: "fireworks",
    baseUrl: "https://api.fireworks.ai/inference/v1",
    defaultModel: "accounts/fireworks/models/llama-v3p1-70b-instruct",
  },
  {
    label: "Perplexity",
    value: "perplexity",
    baseUrl: "https://api.perplexity.ai",
    defaultModel: "llama-3.1-sonar-large-128k-online",
  },
  {
    label: "Mistral",
    value: "mistral",
    baseUrl: "https://api.mistral.ai/v1",
    defaultModel: "mistral-large-latest",
  },
  {
    label: "xAI (Grok)",
    value: "xai",
    baseUrl: "https://api.x.ai/v1",
    defaultModel: "grok-2-latest",
  },
  {
    label: "Custom",
    value: "__custom__",
    baseUrl: "",
    defaultModel: "",
  },
];

export function providerByBaseUrl(url: string): ProviderDef | undefined {
  return PROVIDERS.find((p) => p.baseUrl === url);
}

export function providerByValue(value: string): ProviderDef | undefined {
  return PROVIDERS.find((p) => p.value === value);
}
