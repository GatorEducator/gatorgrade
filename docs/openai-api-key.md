# How to use an OpenAI-compatible API

GatorGrade can use OpenAI and other providers that offer OpenAI-compatible
APIs, such as DeepSeek, Gemini, Grok, and others.

To use an OpenAI-compatible provider, you need:

- an API key from the provider;
- the provider's OpenAI-compatible API URL;
- the name of the model you want to use.

## Get an API key

An API key is a secret code that allows GatorGrade to connect to an AI
provider on your behalf. You can think of it like a password that gives
GatorGrade permission to send requests to the AI model you choose.

First, create an account with the provider you want to use. This could be any
provider that offers an OpenAI-compatible API. Then go to that provider's
developer or API settings and create a new API key.

When the key is created, copy it and save it somewhere private. Some providers
only show the full key once, so make sure you save it before closing the page.

Treat your API key like a password:

- **Do not** put it directly in your assignment files.
- **Do not** commit it to Git.
- **Do not** upload it to GitHub.
- **Do not** share it publicly.

If someone else gets your API key, they may be able to use your account and
generate charges.

You will save the key on your computer in an environment variable so GatorGrade
can use it without putting the secret directly in your code or command.

## Configure GatorGrade

First, follow the [GatorGrade setup instructions][setup] to store your
provider's API key in `AUTO_HINT_KEY_ENV`.

Then run GatorGrade with auto-hinting enabled and provide the
OpenAI-compatible API URL and model name for your provider:

```bash
uvx --from 'gatorgrade[auto-hint]' gatorgrade \
  --auto-hint \
  --auto-hint-url <provider_api_url> \
  --auto-hint-model <model_name>
```

Replace `<provider_api_url>` with the provider's OpenAI-compatible API URL and
`<model_name>` with a model supported by that provider.

For example, using OpenAI:

```bash
uvx --from 'gatorgrade[auto-hint]' gatorgrade \
  --auto-hint \
  --auto-hint-url https://api.openai.com/v1 \
  --auto-hint-model gpt-4.1-mini
```

The same options can be used with other OpenAI-compatible providers by changing
the API URL, API key, and model name.

[setup]: ../README.md#persistent-remote-api-key
